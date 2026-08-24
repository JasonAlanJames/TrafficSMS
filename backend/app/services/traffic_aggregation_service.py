"""Aggregate the existing traffic engine result with source provenance."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.models.traffic_report import AlternateRoute
from app.models.traffic_request import TrafficRequest
from app.models.traffic_source import TrafficSource
from app.models.incident_coverage import IncidentCoverageItem


@dataclass(frozen=True, slots=True)
class TrafficAggregation:
    """Normalized input for deterministic report enrichment."""

    request: TrafficRequest
    engine_reply: str
    sources: tuple[TrafficSource, ...]
    alternate_routes: tuple[AlternateRoute, ...] = ()
    coverage: tuple[IncidentCoverageItem, ...] = ()
    generated_at: datetime = field(
        default_factory=lambda: datetime.min.replace(tzinfo=UTC)
    )
    generation_duration: timedelta = field(default_factory=timedelta)


class TrafficAggregationService:
    """Build a provenance-aware aggregation without calling external providers."""

    def aggregate(
        self,
        request: TrafficRequest,
        engine_reply: str,
        *,
        sources: Iterable[TrafficSource] = (),
        alternate_routes: Iterable[AlternateRoute] = (),
        coverage: Iterable[IncidentCoverageItem] = (),
        generated_at: datetime | None = None,
        generation_duration: timedelta | None = None,
    ) -> TrafficAggregation:
        """Wrap the existing engine output in a future multi-source contract."""

        completed_at = generated_at or datetime.now(UTC)
        duration = generation_duration or timedelta()
        primary_source = TrafficSource(
            source_name="Traffic Engine",
            retrieved_at=completed_at,
            confidence=1.0 if engine_reply.strip() else 0.0,
            data_age=timedelta(),
            coverage=request.mode,
            latency=duration,
            status="AVAILABLE" if engine_reply.strip() else "UNAVAILABLE",
        )
        return TrafficAggregation(
            request=request,
            engine_reply=engine_reply,
            sources=(primary_source, *tuple(sources)),
            alternate_routes=self.rank_alternate_routes(alternate_routes),
            coverage=tuple(coverage),
            generated_at=completed_at,
            generation_duration=duration,
        )

    @staticmethod
    def rank_alternate_routes(
        routes: Iterable[AlternateRoute],
    ) -> tuple[AlternateRoute, ...]:
        """Rank alternatives by time, savings, confidence, stability, and distance."""

        return tuple(
            sorted(
                routes,
                key=lambda route: (
                    route.travel_time is None,
                    route.travel_time if route.travel_time is not None else float("inf"),
                    -(route.savings_minutes or 0),
                    -route.confidence,
                    -route.stability,
                    route.distance_miles is None,
                    route.distance_miles if route.distance_miles is not None else float("inf"),
                    route.name.upper(),
                ),
            )
        )
