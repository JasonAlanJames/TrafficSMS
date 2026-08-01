from sqlalchemy.orm import Session

from app.models.entities import User
from app.models.traffic_request import TrafficRequest


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

    #
    # Placeholder until live corridor providers
    # (CHP, Caltrans, Google Traffic, etc.)
    # are integrated.
    #

    lines = [
        "TrafficSMS",
        "",
        f"{request.corridor} {request.direction}",
        "",
        "Live corridor intelligence",
        "coming soon.",
        "",
        "Planned information:",
        "",
        "• Average speed",
        "• Travel delays",
        "• CHP incidents",
        "• Lane closures",
        "• Construction",
        "• Community police reports",
        "• Enforcement cameras",
        "• Weather impacts",
        "",
        "Drive safely.",
    ]

    return "\n".join(lines)