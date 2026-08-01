from sqlalchemy.orm import Session

from app.models.entities import User
from app.models.traffic_request import TrafficRequest

from app.services.google_maps import google_maps
from app.services.location_resolver import location_resolver

async def build_route_reply(
    db: Session,
    request: TrafficRequest,
    user: User | None = None,
) -> str:
    """
    Build a live route traffic summary using the
    Google Routes API.
    """

    if not request.origin:
        return (
            "Please provide a starting location.\n\n"
            "Example:\n"
            "TRAFFIC CORONA TO ANAHEIM"
        )

    if not request.destination:
        return (
            "Please provide a destination.\n\n"
            "Example:\n"
            "TRAFFIC CORONA TO ANAHEIM"
        )

    origin = await location_resolver.resolve_location(
        db=db,
        user=user,
        query=request.origin,
    )

    destination = await location_resolver.resolve_location(
        db=db,
        user=user,
        query=request.destination,
    )
    

    route = await google_maps.compute_route(
        origin=origin.formatted_address,
        destination=destination.formatted_address,
    )

    lines = [
        "TrafficSMS",
        "",
        f"{origin.formatted_address} → {destination.formatted_address}",
        "",
        f"Distance: {route['distance_miles']} miles",
        f"Travel Time: {route['travel_minutes']} min",
        f"Normal Time: {route['normal_minutes']} min",
        f"Traffic Delay: {route['delay_minutes']} min",
        f"Average Speed: {route['average_speed_mph']} MPH",
        "",
        "Drive safely.",
    ]

    return "\n".join(lines)