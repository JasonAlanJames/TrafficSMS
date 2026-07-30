import re
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.entities import User, CommunityReport, ReportVote
from app.services.traffic import build_traffic_reply

POLICE_RE = re.compile(r"^POLICE(?:\s+(HIDDEN|OTHER SIDE|VISIBLE|MOBILE CAMERA))?(?:\s+(.+))?$", re.I)
VOTE_RE = re.compile(r"^P(\d+)\s+(YES|NO|UNSURE)$", re.I)


async def process_sms(db: Session, from_number: str, body: str) -> str:
    text = " ".join(body.strip().split())
    user = db.scalar(select(User).where(User.phone_e164 == from_number))

    if text.upper() == "HELP":
        return "Commands: TRAFFIC [ZIP/city], POLICE [VISIBLE/HIDDEN/OTHER SIDE] [road/area], P{id} YES/NO/UNSURE, STOP. Report only while parked or as a passenger."
    if text.upper() == "STOP":
        return "You are unsubscribed. Twilio will suppress further messages until START."
    if not user or user.subscription_status != "active":
        return "TrafficSMS requires an active subscription. Visit the customer portal to subscribe or update billing."

    vote_match = VOTE_RE.match(text)
    if vote_match:
        report_id, vote_text = int(vote_match.group(1)), vote_match.group(2).upper()
        report = db.get(CommunityReport, report_id)
        if not report or report.expires_at <= datetime.utcnow():
            return "That report is no longer active."
        voter_key = f"phone:{from_number}"
        existing = db.scalar(select(ReportVote).where(ReportVote.report_id == report_id, ReportVote.voter_key == voter_key))
        if existing:
            return "Your response was already recorded."
        mapped = {"YES": "still", "NO": "cleared", "UNSURE": "unsure"}[vote_text]
        db.add(ReportVote(report_id=report_id, voter_key=voter_key, vote=mapped))
        if mapped == "still": report.still_there_votes += 1
        elif mapped == "cleared": report.cleared_votes += 1
        else: report.unsure_votes += 1
        if report.cleared_votes >= 3 and report.cleared_votes > report.still_there_votes:
            report.status = "likely_cleared"
        elif report.still_there_votes >= 2:
            report.status = "likely_present"
            report.expires_at = max(report.expires_at, datetime.utcnow() + timedelta(minutes=20))
        db.commit()
        return f"Thanks. Police report #{report_id} updated to {report.status.replace('_', ' ')}."

    police_match = POLICE_RE.match(text)
    if police_match:
        subtype = (police_match.group(1) or "VISIBLE").upper().replace(" ", "_")
        location = police_match.group(2) or user.home_area
        if not location:
            return "Reply with a generalized road and area, for example: POLICE VISIBLE I-15 N NEAR MAGNOLIA. Do not report while driving."
        type_map = {"VISIBLE": "police_visible", "HIDDEN": "police_hidden", "OTHER_SIDE": "police_other_side", "MOBILE_CAMERA": "mobile_camera"}
        report = CommunityReport(
            reporter_user_id=user.id,
            report_type=type_map[subtype],
            road_name=location[:160],
            area_label=location[:160],
            status="recently_reported",
            reported_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=35),
        )
        db.add(report)
        db.commit(); db.refresh(report)
        return f"Police peer report #{report.id} recorded for the generalized area: {location}. It expires automatically. Report only while parked or as a passenger."

    if text.upper().startswith("TRAFFIC"):
        area = text[7:].strip() or user.home_area or "your saved area"
        user.monthly_sms_count += 1
        db.commit()
        return await build_traffic_reply(db, area)

    return "Unknown command. Text HELP for supported commands."
