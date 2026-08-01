from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import User
from app.models.traffic_request import TrafficRequest


@dataclass
class TrafficIntelligence:

    #
    # Request Information
    #

    mode: str

    request: TrafficRequest

    #
    # Route Information
    #

    route: dict | None = None

    #
    # Community
    #

    community_reports: list[dict] = field(default_factory=list)

    #
    # Enforcement
    #

    enforcement_cameras: list[dict] = field(default_factory=list)

    #
    # Official Incidents
    #

    incidents: list[dict] = field(default_factory=list)

    construction: list[dict] = field(default_factory=list)

    lane_closures: list[dict] = field(default_factory=list)

    #
    # Weather
    #

    weather: dict | None = None

    #
    # AI
    #

    ai_summary: str | None = None

    #
    # Diagnostics
    #

    metadata: dict[str, Any] = field(default_factory=dict)


class TrafficIntelligenceService:
    """
    Coordinates every traffic provider.

    This service does NOT generate SMS.

    It simply gathers intelligence from all providers and
    returns one normalized TrafficIntelligence object.
    """

    async def gather(
        self,
        db: Session,
        request: TrafficRequest,
        user: User | None = None,
    ) -> TrafficIntelligence:

        intelligence = TrafficIntelligence(
            mode=request.mode,
            request=request,
        )

        #
        # Google Route
        #
        # Filled by route/commute engines.
        #

        #
        # Community Reports
        #
        # TODO
        #

        #
        # Enforcement Cameras
        #
        # TODO
        #

        #
        # CHP Incidents
        #
        # TODO
        #

        #
        # Caltrans Incidents
        #
        # TODO
        #

        #
        # Construction
        #
        # TODO
        #

        #
        # Weather
        #
        # TODO
        #

        #
        # AI Summary
        #
        # TODO
        #

        return intelligence


traffic_intelligence = TrafficIntelligenceService()