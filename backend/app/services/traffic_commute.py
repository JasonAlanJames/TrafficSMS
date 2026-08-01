from sqlalchemy.orm import Session

from app.models.entities import User
from app.models.traffic_request import TrafficRequest

from app.services.traffic_route import build_route_reply


async def build_commute_reply(
    db: Session,
    request: TrafficRequest,
    user: User | None = None,
) -> str:
    """
    Build traffic for a subscriber's saved commute.

    This engine validates that the subscriber has
    saved locations, then reuses the Route engine.
    """

    if not request.origin:
        return (
            "You haven't saved your Home location yet.\n\n"
            "Reply:\n"
            "SET HOME <address>\n\n"
            "Example:\n"
            "SET HOME 123 Main St Corona CA"
        )

    if not request.destination:
        return (
            "You haven't saved your Work location yet.\n\n"
            "Reply:\n"
            "SET WORK <address>\n\n"
            "Example:\n"
            "SET WORK Disneyland Anaheim CA"
        )

    #
    # Reuse the Route Engine.
    #
    return await build_route_reply(
        db=db,
        request=request,
        user=user,
    )