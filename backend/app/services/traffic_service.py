"""Traffic command orchestration built on the existing traffic engines."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

from app.models.traffic_report import TrafficReport
from app.models.traffic_request import TrafficRequest
from app.models.traffic_provider_result import TrafficProviderResult
from app.cache.cache_keys import traffic as traffic_cache_key
from app.cache.cache_manager import CacheManager
from app.cache.cache_ttl import traffic as traffic_cache_ttl
from app.providers.provider_manager import TrafficProviderManager
from app.llm.traffic_summary_service import TrafficSummaryService
from app.services.traffic import build_traffic_reply
from app.services.traffic_aggregation_service import TrafficAggregationService
from app.services.traffic_intelligence_service import TrafficIntelligenceService
from app.services.incident_coverage_service import IncidentCoverageService
from app.services.traffic_quality_service import TrafficQualityService
from app.models.traffic_quality import TrafficQualityAssessment
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
    quality: TrafficQualityAssessment | None = None


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
        provider_manager: TrafficProviderManager | None = None,
        cache_manager: CacheManager | None = None,
        incident_coverage_service: IncidentCoverageService | None = None,
        quality_service: TrafficQualityService | None = None,
    ) -> None:
        self._intelligence_service = intelligence_service or TrafficIntelligenceService()
        self._aggregation_service = aggregation_service or TrafficAggregationService()
        self._summary_service = summary_service or TrafficSummaryService()
        self._provider_manager = provider_manager or TrafficProviderManager()
        self._cache_manager = cache_manager or CacheManager()
        self._incident_coverage_service = incident_coverage_service or IncidentCoverageService()
        self._quality_service = quality_service or TrafficQualityService()

    async def lookup_provider_result(
        self,
        request: TrafficRequest,
        *,
        state: str = "",
    ) -> TrafficProviderResult:
        """Use request cache above the existing provider-manager cache."""

        target = request.destination or request.area or request.corridor or "commute"
        key = traffic_cache_key(state or "default", target)
        cached = self._cache_manager.get_provider_result(key)
        if cached is not None:
            return cached

        if request.mode in {"route", "commute"}:
            result = await self._provider_manager.request(
                "route", request.origin or "", request.destination or "", state=state
            )
        elif request.mode == "corridor":
            result = await self._provider_manager.request(
                "corridor", request.corridor or "", request.direction or "", state=state
            )
        else:
            result = await self._provider_manager.request("area", request.area or "", state=state)
        self._cache_manager.set_provider_result(key, result, traffic_cache_ttl())
        return result

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

        return self.validate_request(request)

    def validate_request(self, request: TrafficRequest) -> TrafficPreparation:
        """Apply deterministic nationwide quality checks before traffic work begins."""

        quality = self._quality_service.assess(request)
        if not quality.is_supported:
            return TrafficPreparation(request=None, error_message=quality.user_message, quality=quality)
        if request.mode == "corridor":
            request.corridor = quality.corridor or request.corridor
            request.direction = quality.direction or request.direction
        return TrafficPreparation(request=request, quality=quality)

    async def build_reply(
        self,
        context: SMSContext,
        request: TrafficRequest,
    ) -> TrafficServiceResult:
        """Delegate a prepared request to the existing traffic engine."""

        quality = self._quality_service.assess(request)
        if not quality.is_supported:
            return TrafficServiceResult(
                message=quality.user_message,
                request=request,
                metadata={
                    "traffic_mode": request.mode,
                    "quality_level": quality.quality_level,
                    "coverage_status": quality.coverage_status,
                    "fallback_reason": quality.fallback_reason,
                },
            )

        if request.mode == "corridor":
            request.corridor = quality.corridor or request.corridor
            request.direction = quality.direction or request.direction

        started_at = datetime.now(UTC)
        reply = await build_traffic_reply(
            db=context.db,
            request=request,
            user=context.user,
        )
        coverage = await self._incident_coverage_service.collect(context.db, request)
        aggregation = self._aggregation_service.aggregate(
            request,
            reply,
            coverage=coverage,
            generation_duration=datetime.now(UTC) - started_at,
        )
        report = self._intelligence_service.build_report(request, aggregation)
        report = replace(
            report,
            quality_level=quality.quality_level,
            coverage_status=quality.coverage_status,
            fallback_reason=quality.fallback_reason,
            location_confidence=quality.confidence,
            normalized_query=quality.normalized_query,
        )
        deterministic_reply = format_traffic_report(report)
        summary = await self._summary_service.summarize(report, deterministic_reply)
        report = replace(report, summary_metadata=self._summary_service.metadata)
        return TrafficServiceResult(
            message=summary,
            request=request,
            report=report,
            metadata={
                "traffic_mode": request.mode,
                "quality_level": quality.quality_level,
                "coverage_status": quality.coverage_status,
                "normalized_query": quality.normalized_query,
            },
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
