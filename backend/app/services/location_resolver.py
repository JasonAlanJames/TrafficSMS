from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.entities import User
from app.services.google_maps import google_maps


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

        #
        # Future:
        # HOME
        #
        if user and text.upper() == "HOME" and user.home_location:

            print("=" * 80)
            print(f"Original query : {query!r}")
            print(f"Candidate sent : {candidate!r}")
            print("=" * 80)

            geo = await google_maps.geocode(
                candidate,
            )

            return ResolvedLocation(
                query=query,
                formatted_address=geo["formatted_address"],
                latitude=geo["latitude"],
                longitude=geo["longitude"],
                place_id=geo["place_id"],
                source="home",
            )

        #
        # Future:
        # WORK
        #
        if user and text.upper() == "WORK" and user.work_location:

            geo = await google_maps.geocode(
                user.work_location,
            )

            return ResolvedLocation(
                query=query,
                formatted_address=geo["formatted_address"],
                latitude=geo["latitude"],
                longitude=geo["longitude"],
                place_id=geo["place_id"],
                source="work",
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