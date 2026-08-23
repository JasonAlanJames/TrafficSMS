from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.entities import User
from app.services.google_maps import google_maps


_SAVED_LOCATION_ATTRIBUTES = {
    "HOME": ("home_location", "home"),
    "WORK": ("work_location", "work"),
    "GYM": ("gym_location", "gym"),
    "SCHOOL": ("school_location", "school"),
}


@dataclass
class ResolvedLocation:
    """
    Canonical representation of a resolved location.
    """

    query: str

    formatted_address: str

    latitude: float

    longitude: float

    place_id: str

    source: str
    # gps
    # home
    # work
    # gym
    # school
    # default_state
    # geocoder
    # area_code


class LocationResolver:
    """
    Resolves user-supplied locations into a canonical location.

    This class intentionally knows nothing about traffic.
    Its only responsibility is converting user input into
    a normalized location.
    """

    async def resolve_location(
        self,
        db: Session,
        user: User | None,
        query: str,
    ) -> ResolvedLocation:

        text = query.strip()

        saved_location = _SAVED_LOCATION_ATTRIBUTES.get(text.upper())
        if user and saved_location:
            attribute, source = saved_location
            candidate = getattr(user, attribute)
            if candidate:
                geo = await google_maps.geocode(candidate)
                return ResolvedLocation(
                    query=query,
                    formatted_address=geo["formatted_address"],
                    latitude=geo["latitude"],
                    longitude=geo["longitude"],
                    place_id=geo["place_id"],
                    source=source,
                )

        #
        # Default city/state assistance.
        #
        candidate = text

        if (
            user
            and user.default_state
            and "," not in text
        ):
            candidate = f"{text}, {user.default_state}"

        #
        # Google geocoder
        #
        geo = await google_maps.geocode(
            candidate,
        )

        return ResolvedLocation(
            query=query,
            formatted_address=geo["formatted_address"],
            latitude=geo["latitude"],
            longitude=geo["longitude"],
            place_id=geo["place_id"],
            source="geocoder",
        )


location_resolver = LocationResolver()
