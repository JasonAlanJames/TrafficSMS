from sqlalchemy.orm import Session

from app.models.entities import User
from app.models.traffic_request import TrafficRequest
from app.services.incident_coverage_service import incident_coverage_service


async def build_corridor_reply(
    db: Session,
    request: TrafficRequest,
    user: User | None = None,
) -> str:
    """
    Build a highway corridor traffic summary.

    Examples:

        TRAFFIC 91 WEST
        TRAFFIC I-15 NORTH
        TRAFFIC 405 SOUTH
    """

    if not request.corridor:
        return (
            "Please specify a highway.\n\n"
            "Example:\n"
            "TRAFFIC 91 WEST"
        )

    if not request.direction:
        return (
            "Please specify a direction.\n\n"
            "Example:\n"
            "TRAFFIC 91 WEST"
        )

    lines = [
        "TrafficSMS",
        "",
        f"{request.corridor} {request.direction}",
        "",
    ]

    coverage = await incident_coverage_service.collect(db, request)
    if not coverage:
        lines.append("No active community incidents or closures found for this corridor yet.")
    else:
        for item in coverage[:4]:
            location = item.road_name or item.location_text
            lines.append(f"• {item.title}: {location}" if location else f"• {item.title}")
    lines.extend(("", "Drive safely."))

    return "\n".join(lines)
