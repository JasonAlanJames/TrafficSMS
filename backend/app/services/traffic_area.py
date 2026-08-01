from datetime import datetime

from sqlalchemy.orm import Session

from app.models.entities import User
from app.models.traffic_request import TrafficRequest

from app.services.location_resolver import location_resolver
from app.services.providers.community_provider import community_provider


async def build_area_reply(
    db: Session,
    request: TrafficRequest,
    user: User | None = None,
) -> str:
    """
    Build an area traffic summary.

    Example:

        TRAFFIC CORONA
    """

    if not request.area:
        return (
            "Please specify an area.\n\n"
            "Example:\n"
            "TRAFFIC CORONA"
        )

    #
    # Resolve the requested location.
    #

    location = await location_resolver.resolve_location(
        db=db,
        user=user,
        query=request.area,
    )

    resolved_area = location.formatted_address

    now = datetime.utcnow()

    #
    # Retrieve community intelligence.
    #

    police_reports = await community_provider.get_reports(
        db=db,
        area=resolved_area,
    )

    cameras = await community_provider.get_cameras(
        db=db,
        area=resolved_area,
    )

    dui_notices = await community_provider.get_dui_notices(
        db=db,
        area=resolved_area,
    )

    lines = [
        "TrafficSMS",
        "",
        resolved_area,
        "",
    ]

    #
    # Community Reports
    #

    if police_reports:

        lines.append("Community Reports")

        for report in police_reports:

            age = int(
                (
                    now - report.reported_at
                ).total_seconds()
                / 60
            )

            report_name = (
                report.report_type
                .replace("_", " ")
                .title()
            )

            lines.append(
                f"• {report_name}"
            )

            lines.append(
                f"  {report.road_name}"
            )

            lines.append(
                f"  {age} min ago"
            )

    else:

        lines.append(
            "No active community reports."
        )

    #
    # Enforcement Cameras
    #

    if cameras:

        lines.append("")
        lines.append("Enforcement Cameras")

        for camera in cameras:

            verified = (
                "Verified"
                if camera.verified
                else "Community"
            )

            lines.append(
                f"• {camera.road_name}"
            )

            lines.append(
                f"  ({verified})"
            )

    #
    # Official DUI Notices
    #

    if dui_notices:

        lines.append("")
        lines.append("Official DUI Notices")

        for notice in dui_notices:

            lines.append(
                f"• {notice.agency}"
            )

            lines.append(
                f"  {notice.area_label}"
            )

    lines.append("")
    lines.append("Drive safely.")

    #
    # Twilio SMS limit
    #

    return "\n".join(lines)[:1500]