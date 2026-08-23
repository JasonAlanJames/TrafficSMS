"""Traffic command orchestration built on the existing traffic engines."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.models.traffic_report import TrafficReport
from app.models.traffic_request import TrafficRequest
from app.llm.traffic_summary_service import TrafficSummaryService
from app.services.traffic import build_traffic_reply
from app.services.traffic_aggregation_service import TrafficAggregationService
from app.services.traffic_intelligence_service import TrafficIntelligenceService
from app.services.traffic_parser import parse_traffic_command
from app.sms.context import SMSContext
from app.sms.formatter import format_traffic_report


_SAVED_LOCATION_ATTRIBUTES = {
    "HOME": "home_location",
    "WORK": "work_location",
    "GYM": "gym_location",
    "SCHOOL": "school_location",
}


@dataclass(frozen=True)
class TrafficPreparation:
    """A validated traffic request or a user-safe preparation error."""

    request: TrafficRequest | None
    error_message: str | None = None


@dataclass(frozen=True)
class TrafficServiceResult:
    """Structured output from the existing traffic engine bridge."""

    message: str
    request: TrafficRequest
    report: TrafficReport | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class TrafficService:
    """Prepare deterministic traffic commands and invoke the traffic engine."""

    def __init__(
        self,
        intelligence_service: TrafficIntelligenceService | None = None,
        aggregation_service: TrafficAggregationService | None = None,
        summary_service: TrafficSummaryService | None = None,
    ) -> None:
        self._intelligence_service = intelligence_service or TrafficIntelligenceService()
        self._aggregation_service = aggregation_service or TrafficAggregationService()
        self._summary_service = summary_service or TrafficSummaryService()

    def prepare_request(self, context: SMSContext) -> TrafficPreparation:
        """Build a request while validating any saved-location references."""

        if context.user is None:
            return TrafficPreparation(
                request=None,
                error_message="A registered account is required for traffic requests.",
            )

        try:
            request = parse_traffic_command(
                context.resolved_text or context.normalized_text,
                subscriber_id=context.user.id,
            )
        except ValueError:
            return TrafficPreparation(
                request=None,
                error_message="Sorry, I couldn't understand that traffic request.",
            )

        missing_locations = self._missing_saved_locations(context, request)
        if missing_locations:
            return TrafficPreparation(
                request=None,
                error_message=self._missing_location_message(
                    missing_locations,
                    is_commute=request.mode == "commute",
                ),
            )

        if request.mode == "commute":
            request.origin = context.user.home_location
            request.destination = context.user.work_location

        return TrafficPreparation(request=request)

    async def build_reply(
        self,
        context: SMSContext,
        request: TrafficRequest,
    ) -> TrafficServiceResult:
        """Delegate a prepared request to the existing traffic engine."""

        started_at = datetime.now(UTC)
        reply = await build_traffic_reply(
            db=context.db,
            request=request,
            user=context.user,
        )
        aggregation = self._aggregation_service.aggregate(
            request,
            reply,
            generation_duration=datetime.now(UTC) - started_at,
        )
        report = self._intelligence_service.build_report(request, aggregation)
        deterministic_reply = format_traffic_report(report)
        return TrafficServiceResult(
            message=await self._summary_service.summarize(report, deterministic_reply),
            request=request,
            report=report,
            metadata={"traffic_mode": request.mode},
        )

    @staticmethod
    def _missing_saved_locations(
        context: SMSContext,
        request: TrafficRequest,
    ) -> tuple[str, ...]:
        if context.user is None:
            return ()

        if request.mode == "commute":
            queries = ("HOME", "WORK")
        elif request.mode == "route":
            queries = (request.origin or "", request.destination or "")
        elif request.mode == "area":
            queries = (request.area or "",)
        else:
            queries = ()

        missing: list[str] = []
        for query in queries:
            location_key = query.upper()
            attribute = _SAVED_LOCATION_ATTRIBUTES.get(location_key)
            if (
                attribute
                and not getattr(context.user, attribute)
                and location_key.title() not in missing
            ):
                missing.append(location_key.title())
        return tuple(missing)

    @staticmethod
    def _missing_location_message(
        missing_locations: tuple[str, ...],
        *,
        is_commute: bool,
    ) -> str:
        if is_commute and missing_locations == ("Home", "Work"):
            return (
                "Please configure your Home and Work locations before using "
                "the TRAFFIC commute command."
            )

        if len(missing_locations) == 1:
            location = missing_locations[0]
            return (
                f"Please configure your {location} location before using "
                f"TRAFFIC {location.upper()}."
            )

        locations = " and ".join(missing_locations)
        return f"Please configure your {locations} locations before requesting this route."
