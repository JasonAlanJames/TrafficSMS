from sqlalchemy.orm import Session

from app.models.traffic_request import TrafficRequest

from app.services.traffic_area import build_area_reply
from app.services.traffic_route import build_route_reply
from app.services.traffic_corridor import build_corridor_reply
from app.services.traffic_commute import build_commute_reply
from app.models.entities import User

async def build_traffic_reply(
    db: Session,
    request: TrafficRequest,
    user: User | None = None,
) -> str:

    """
    Main TrafficSMS dispatcher.

    Routes each request to the proper traffic engine.
    """

    if request.mode == "area":
        return await build_area_reply(
            db=db,
            request=request,
            user=user,
        )

    if request.mode == "route":
        return await build_route_reply(
            db=db,
            request=request,
            user=user,
        )

    if request.mode == "corridor":
        return await build_corridor_reply(
            db=db,
            request=request,
            user=user,
        )

    if request.mode == "commute":
        return await build_commute_reply(
            db=db,
            request=request,
            user=user,
        )

    raise ValueError(
        f"Unsupported traffic mode: {request.mode}"
    )