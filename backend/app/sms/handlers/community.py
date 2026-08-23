"""Community police-report command handlers."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from sqlalchemy import select

from app.billing.exceptions import SubscriptionRequiredError
from app.billing.repository import BillingRepository
from app.billing.service import BillingService
from app.models.entities import CommunityReport, ReportVote, User
from app.sms.intents import SMSIntent
from app.sms.models import SMSMessageContext, SMSParseResult, SMSResponse
from app.sms.handlers.subscription import REGISTRATION_URL


_POLICE_RE = re.compile(
    r"^POLICE(?:\s+(HIDDEN|OTHER SIDE|VISIBLE|MOBILE CAMERA))?(?:\s+(.+))?$"
)
_VOTE_RE = re.compile(r"^P(\d+)\s+(YES|NO|UNSURE)$")


def _registered_user(context: SMSMessageContext) -> User | None:
    return context.db.scalar(
        select(User).where(User.phone_e164 == context.from_number)
    )


def _subscription_required_response(intent: SMSIntent) -> SMSResponse:
    return SMSResponse(
        success=False,
        intent=intent,
        message=(
            "TrafficSMS requires an active subscription.\n\n"
            "Visit:\n\n"
            f"{REGISTRATION_URL}"
        ),
    )


def _ensure_active_subscriber(
    context: SMSMessageContext,
    intent: SMSIntent,
) -> tuple[User | None, SMSResponse | None]:
    user = _registered_user(context)
    if user is None:
        return None, SMSResponse(
            success=False,
            intent=intent,
            message=(
                "Welcome to TrafficSMS!\n\n"
                "Reply SUBSCRIBE to get started.\n\n"
                "Or visit:\n\n"
                f"{REGISTRATION_URL}"
            ),
        )

    billing_service = BillingService(BillingRepository(context.db))
    try:
        billing_service.ensure_active_subscription(user)
    except SubscriptionRequiredError:
        return user, _subscription_required_response(intent)

    return user, None


async def handle_police_report(
    parsed: SMSParseResult,
    context: SMSMessageContext,
) -> SMSResponse:
    """Create a time-limited community police report."""

    user, failure = _ensure_active_subscriber(context, SMSIntent.POLICE_REPORT)
    if failure is not None:
        return failure
    if user is None:
        return _subscription_required_response(SMSIntent.POLICE_REPORT)

    match = _POLICE_RE.fullmatch(parsed.normalized_text)
    if match is None:
        return SMSResponse(
            success=False,
            intent=SMSIntent.POLICE_REPORT,
            message="Reply HELP for available commands.",
        )

    subtype = (match.group(1) or "VISIBLE").replace(" ", "_")
    location = match.group(2) or user.home_location
    if not location:
        return SMSResponse(
            success=False,
            intent=SMSIntent.POLICE_REPORT,
            message=(
                "Reply with a generalized road and area, for example: "
                "POLICE VISIBLE I-15 N NEAR MAGNOLIA. Do not report while driving."
            ),
        )

    type_map = {
        "VISIBLE": "police_visible",
        "HIDDEN": "police_hidden",
        "OTHER_SIDE": "police_other_side",
        "MOBILE_CAMERA": "mobile_camera",
    }
    report = CommunityReport(
        reporter_user_id=user.id,
        report_type=type_map[subtype],
        road_name=location[:160],
        area_label=location[:160],
        status="recently_reported",
        reported_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=35),
    )
    context.db.add(report)
    context.db.commit()
    context.db.refresh(report)

    return SMSResponse(
        success=True,
        intent=SMSIntent.POLICE_REPORT,
        message=(
            f"Police peer report #{report.id} recorded for the generalized area: "
            f"{location}. It expires automatically. "
            "Report only while parked or as a passenger."
        ),
        metadata={"report_id": report.id},
    )


async def handle_police_vote(
    parsed: SMSParseResult,
    context: SMSMessageContext,
) -> SMSResponse:
    """Record a subscriber's community-report confirmation vote."""

    user, failure = _ensure_active_subscriber(context, SMSIntent.POLICE_VOTE)
    if failure is not None:
        return failure
    if user is None:
        return _subscription_required_response(SMSIntent.POLICE_VOTE)

    match = _VOTE_RE.fullmatch(parsed.normalized_text)
    if match is None:
        return SMSResponse(
            success=False,
            intent=SMSIntent.POLICE_VOTE,
            message="Reply HELP for available commands.",
        )

    report_id = int(match.group(1))
    vote_text = match.group(2)
    report = context.db.get(CommunityReport, report_id)
    if report is None or report.expires_at <= datetime.utcnow():
        return SMSResponse(
            success=False,
            intent=SMSIntent.POLICE_VOTE,
            message="That report is no longer active.",
        )

    voter_key = f"phone:{context.from_number}"
    existing = context.db.scalar(
        select(ReportVote).where(
            ReportVote.report_id == report_id,
            ReportVote.voter_key == voter_key,
        )
    )
    if existing is not None:
        return SMSResponse(
            success=False,
            intent=SMSIntent.POLICE_VOTE,
            message="Your response was already recorded.",
        )

    vote_map = {"YES": "still", "NO": "cleared", "UNSURE": "unsure"}
    mapped_vote = vote_map[vote_text]
    context.db.add(
        ReportVote(
            report_id=report_id,
            voter_key=voter_key,
            vote=mapped_vote,
        )
    )
    if mapped_vote == "still":
        report.still_there_votes += 1
    elif mapped_vote == "cleared":
        report.cleared_votes += 1
    else:
        report.unsure_votes += 1

    if report.cleared_votes >= 3 and report.cleared_votes > report.still_there_votes:
        report.status = "likely_cleared"
    elif report.still_there_votes >= 2:
        report.status = "likely_present"
        report.expires_at = max(
            report.expires_at,
            datetime.utcnow() + timedelta(minutes=20),
        )

    context.db.commit()
    return SMSResponse(
        success=True,
        intent=SMSIntent.POLICE_VOTE,
        message=f"Thanks. Police report #{report_id} updated to {report.status.replace('_', ' ')}.",
        metadata={"report_id": report_id, "status": report.status},
    )
