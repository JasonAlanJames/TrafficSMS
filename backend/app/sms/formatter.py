"""SMS presentation helpers with no command or business logic."""

from __future__ import annotations

import re

from app.models.traffic_report import TrafficReport
from app.sms.models import SMSResponse


MAX_SMS_MESSAGE_LENGTH = 1600
_EXCESS_BLANK_LINES_RE = re.compile(r"\n{3,}")


def format_sms_response(
    response: SMSResponse,
    maximum_length: int = MAX_SMS_MESSAGE_LENGTH,
) -> str:
    """Return a readable, bounded SMS string for a handler response."""

    return _format_message(response.message, maximum_length)


def format_traffic_report(
    report: TrafficReport,
    maximum_length: int = MAX_SMS_MESSAGE_LENGTH,
) -> str:
    """Render an enriched traffic report as a concise, bounded SMS reply."""

    has_structured_traffic = any(
        (
            report.travel_time is not None,
            report.incidents,
            report.construction,
            report.lane_closures,
            report.weather_impacts,
            report.alternate_routes,
        )
    )
    if not has_structured_traffic and report.source_summary:
        return _format_message(report.source_summary, maximum_length)

    lines = ["TrafficSMS", report.location]
    if report.travel_time is not None:
        travel_line = f"Travel: {report.travel_time} min"
        if report.delay_minutes is not None:
            travel_line += f" (+{report.delay_minutes} min delay)"
        lines.append(travel_line)
    if report.congestion_level != "UNKNOWN":
        lines.append(f"Traffic: {report.severity.title()} congestion")

    major_incident = report.incidents[0] if report.incidents else None
    if major_incident:
        detail = major_incident.category
        if major_incident.road_name:
            detail += f" on {major_incident.road_name}"
        lines.append(f"Incident: {detail}")

    best_alternate = _best_alternate(report)
    if best_alternate:
        alternate_line = f"Alt: {best_alternate.name}"
        if best_alternate.travel_time is not None:
            alternate_line += f", {best_alternate.travel_time} min"
        if best_alternate.savings_minutes:
            alternate_line += f" (saves {best_alternate.savings_minutes} min)"
        lines.append(alternate_line)

    attribution = _attribution_line(report)
    if attribution:
        lines.append(attribution)
    freshness = _freshness_line(report)
    if freshness:
        lines.append(freshness)

    return _format_message("\n".join(lines), maximum_length)


def _best_alternate(report: TrafficReport):
    if not report.alternate_routes:
        return None
    return max(
        report.alternate_routes,
        key=lambda alternate: alternate.savings_minutes or 0,
    )


def _freshness_line(report: TrafficReport) -> str | None:
    if not report.sources:
        return None
    age_seconds = int(report.freshness.newest_source_age.total_seconds())
    if age_seconds < 5:
        return "Updated moments ago."
    if age_seconds < 60:
        return f"Updated {age_seconds} seconds ago."
    minutes = max(age_seconds // 60, 1)
    return f"Updated {minutes} min ago."


def _attribution_line(report: TrafficReport) -> str | None:
    providers = tuple(
        dict.fromkeys(
            (source.provider_name or source.source_name).strip()
            for source in report.sources
            if source.status == "AVAILABLE" and (source.provider_name or source.source_name).strip()
        )
    )
    if not providers:
        return None
    if len(providers) == 1:
        return f"Based on {providers[0]}."
    if len(providers) == 2:
        return f"Based on {providers[0]} and {providers[1]}."
    return f"Based on {', '.join(providers[:-1])} and {providers[-1]}."


def _format_message(message: str, maximum_length: int) -> str:
    """Normalize whitespace and apply the shared outbound SMS limit."""

    message = message.replace("\r\n", "\n").replace("\r", "\n")
    message = _EXCESS_BLANK_LINES_RE.sub("\n\n", message).strip()

    if maximum_length <= 0 or len(message) <= maximum_length:
        return message

    if maximum_length <= 3:
        return message[:maximum_length]

    return f"{message[: maximum_length - 3].rstrip()}..."
