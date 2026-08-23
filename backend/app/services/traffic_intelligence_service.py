"""Deterministic enrichment of existing traffic-engine responses."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta

from app.models.traffic_report import (
    AlternateRoute,
    IncidentCategory,
    Severity,
    TrafficIncidentSummary,
    TrafficReport,
)
from app.models.traffic_request import TrafficRequest
from app.models.traffic_source import TrafficSource
from app.models.traffic_incident import TrafficIncident
from app.services.traffic_aggregation_service import (
    TrafficAggregation,
    TrafficAggregationService,
)


_MINUTES_RE = r"(?P<minutes>\d+)\s*(?:min(?:ute)?s?)"
_METRIC_PATTERNS = {
    "travel_time": re.compile(rf"Travel\s+Time:\s*{_MINUTES_RE}", re.IGNORECASE),
    "normal_travel_time": re.compile(
        rf"Normal\s+Time:\s*{_MINUTES_RE}", re.IGNORECASE
    ),
    "delay_minutes": re.compile(
        rf"(?:Traffic\s+)?Delay:\s*{_MINUTES_RE}", re.IGNORECASE
    ),
}
_ALTERNATE_LINE_RE = re.compile(
    r"^(?:Alternate|Alt)(?:\s+Route)?\s*:\s*(?P<detail>.+)$",
    re.IGNORECASE,
)
_ALTERNATE_TIME_RE = re.compile(r"\s*[-,]\s*(?P<minutes>\d+)\s*min(?:ute)?s?", re.IGNORECASE)
_ALTERNATE_SAVINGS_RE = re.compile(
    r"\(?\s*(?:saves?|saving)\s*(?P<savings>\d+)\s*min(?:ute)?s?\)?",
    re.IGNORECASE,
)


class TrafficIntelligenceService:
    """Create a normalized report without accessing SMS, providers, or AI."""

    def build_report(
        self,
        request: TrafficRequest,
        engine_reply: str | TrafficAggregation,
        *,
        alternate_routes: Iterable[AlternateRoute | Mapping[str, object]] = (),
        generated_at: datetime | None = None,
    ) -> TrafficReport:
        """Normalize an existing engine reply and optional route alternatives."""

        aggregation = engine_reply if isinstance(engine_reply, TrafficAggregation) else None
        raw_reply = aggregation.engine_reply if aggregation else engine_reply
        source_records = aggregation.sources if aggregation else ()
        aggregated_routes = aggregation.alternate_routes if aggregation else ()
        report_generated_at = generated_at or (
            aggregation.generated_at if aggregation else datetime.now(UTC)
        )
        generation_duration = (
            aggregation.generation_duration if aggregation else timedelta()
        )

        travel_time = self._metric(raw_reply, "travel_time")
        normal_travel_time = self._metric(raw_reply, "normal_travel_time")
        delay_minutes = self._metric(raw_reply, "delay_minutes")
        if delay_minutes is None and travel_time is not None and normal_travel_time is not None:
            delay_minutes = max(travel_time - normal_travel_time, 0)

        congestion_level = self.congestion_level(
            delay_minutes=delay_minutes,
            travel_time=travel_time,
            normal_travel_time=normal_travel_time,
        )
        severity = self.classify_severity(
            delay_minutes=delay_minutes,
            congestion_level=congestion_level,
        )
        incidents = self._extract_incidents(
            raw_reply,
            source=source_records[0].source_name if source_records else "Traffic Engine",
        )
        alternatives = TrafficAggregationService.rank_alternate_routes(
            self._normalize_alternates(
                (*aggregated_routes, *tuple(alternate_routes)),
                engine_reply=raw_reply,
                current_travel_time=travel_time,
            )
        )
        construction = tuple(
            incident for incident in incidents if incident.category == "Construction"
        )
        lane_closures = tuple(
            incident for incident in incidents if incident.category == "Lane Closure"
        )
        weather_impacts = tuple(
            incident.description
            for incident in incidents
            if incident.category == "Weather"
        )
        confidence = self.confidence_score(
            location=self._location(request, raw_reply),
            travel_time=travel_time,
            normal_travel_time=normal_travel_time,
            delay_minutes=delay_minutes,
        )
        overall_confidence = self.overall_confidence(confidence, source_records)
        report_age = min((source.data_age for source in source_records), default=None)

        return TrafficReport(
            location=self._location(request, raw_reply),
            travel_time=travel_time,
            normal_travel_time=normal_travel_time,
            delay_minutes=delay_minutes,
            congestion_level=congestion_level,
            severity=severity,
            incidents=incidents,
            construction=construction,
            lane_closures=lane_closures,
            weather_impacts=weather_impacts,
            alternate_routes=alternatives,
            confidence=confidence,
            generated_at=report_generated_at,
            # Preserve established replies where the legacy engine has no
            # structured traffic data to enrich yet.
            source_summary=raw_reply.strip(),
            sources=source_records,
            report_age=report_age,
            overall_confidence=overall_confidence,
            data_quality=self.data_quality(overall_confidence, source_records, report_age),
            generation_duration=generation_duration,
        )

    @staticmethod
    def overall_confidence(
        report_confidence: float,
        sources: tuple[TrafficSource, ...],
    ) -> float:
        """Combine report completeness with available source confidence."""

        available = [source.confidence for source in sources if source.status == "AVAILABLE"]
        if not available:
            return report_confidence
        return round((report_confidence + sum(available) / len(available)) / 2, 2)

    @staticmethod
    def data_quality(
        overall_confidence: float,
        sources: tuple[TrafficSource, ...],
        report_age: timedelta | None,
    ) -> str:
        """Classify the usable quality of the report's provenance."""

        if not sources or report_age is None:
            return "UNKNOWN"
        if overall_confidence >= 0.85 and report_age <= timedelta(minutes=5):
            return "HIGH"
        if overall_confidence >= 0.60 and report_age <= timedelta(minutes=15):
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def classify_severity(
        *,
        delay_minutes: int | None,
        congestion_level: str,
    ) -> Severity:
        """Return the highest deterministic severity from delay and congestion."""

        delay_severity: Severity = "LOW"
        if delay_minutes is not None:
            if delay_minutes > 30:
                delay_severity = "SEVERE"
            elif delay_minutes > 15:
                delay_severity = "HIGH"
            elif delay_minutes > 5:
                delay_severity = "MODERATE"

        congestion_severity: Severity = (
            congestion_level if congestion_level != "UNKNOWN" else "LOW"
        )
        levels: tuple[Severity, ...] = ("LOW", "MODERATE", "HIGH", "SEVERE")
        return max((delay_severity, congestion_severity), key=levels.index)

    @staticmethod
    def congestion_level(
        *,
        delay_minutes: int | None,
        travel_time: int | None,
        normal_travel_time: int | None,
    ) -> str:
        """Classify congestion from a delay's duration and relative impact."""

        if delay_minutes is None:
            return "UNKNOWN"

        delay_ratio = 0.0
        if normal_travel_time and normal_travel_time > 0:
            delay_ratio = delay_minutes / normal_travel_time

        if delay_minutes > 30 or delay_ratio > 0.65:
            return "SEVERE"
        if delay_minutes > 15 or delay_ratio > 0.35:
            return "HIGH"
        if delay_minutes > 5 or delay_ratio > 0.15:
            return "MODERATE"
        return "LOW"

    @staticmethod
    def confidence_score(
        *,
        location: str,
        travel_time: int | None,
        normal_travel_time: int | None,
        delay_minutes: int | None,
    ) -> float:
        """Score complete, internally consistent traffic data from zero to one."""

        score = 0.20 if location else 0.0
        score += 0.25 if travel_time is not None else 0.0
        score += 0.20 if normal_travel_time is not None else 0.0
        score += 0.20 if delay_minutes is not None else 0.0
        if (
            travel_time is not None
            and normal_travel_time is not None
            and delay_minutes is not None
            and delay_minutes == max(travel_time - normal_travel_time, 0)
        ):
            score += 0.15
        return round(min(score, 1.0), 2)

    @staticmethod
    def _metric(engine_reply: str, metric: str) -> int | None:
        match = _METRIC_PATTERNS[metric].search(engine_reply)
        return int(match.group("minutes")) if match else None

    @staticmethod
    def _location(request: TrafficRequest, engine_reply: str) -> str:
        for line in engine_reply.splitlines():
            candidate = line.strip()
            if "→" in candidate or "->" in candidate:
                return candidate

        if request.mode in {"route", "commute"}:
            return " to ".join(
                value for value in (request.origin, request.destination) if value
            )
        if request.mode == "corridor":
            return " ".join(
                value for value in (request.corridor, request.direction) if value
            )
        return request.area or "Traffic update"

    def _normalize_alternates(
        self,
        alternates: Iterable[AlternateRoute | Mapping[str, object]],
        *,
        engine_reply: str,
        current_travel_time: int | None,
    ) -> tuple[AlternateRoute, ...]:
        normalized: list[AlternateRoute] = []
        for alternate in alternates:
            if isinstance(alternate, AlternateRoute):
                candidate = alternate
            else:
                name = str(alternate.get("name") or alternate.get("route_name") or "").strip()
                if not name:
                    continue
                travel_time = self._positive_int(alternate.get("travel_time"))
                savings = self._positive_int(alternate.get("savings_minutes"))
                candidate = AlternateRoute(
                    name,
                    travel_time,
                    savings,
                    confidence=self._normalized_float(alternate.get("confidence"), 0.5),
                    stability=self._normalized_float(alternate.get("stability"), 0.5),
                    distance_miles=self._positive_float(alternate.get("distance_miles")),
                )
            normalized.append(self._with_calculated_savings(candidate, current_travel_time))

        for line in engine_reply.splitlines():
            match = _ALTERNATE_LINE_RE.match(line.strip())
            if match is None:
                continue
            detail = match.group("detail")
            time_match = _ALTERNATE_TIME_RE.search(detail)
            savings_match = _ALTERNATE_SAVINGS_RE.search(detail)
            name_end = time_match.start() if time_match else len(detail)
            name = detail[:name_end].strip()
            if not name:
                continue
            travel_time = self._positive_int(
                time_match.group("minutes") if time_match else None
            )
            savings = self._positive_int(
                savings_match.group("savings") if savings_match else None
            )
            normalized.append(
                self._with_calculated_savings(
                    AlternateRoute(name, travel_time, savings), current_travel_time
                )
            )

        unique: dict[str, AlternateRoute] = {}
        for alternate in normalized:
            unique.setdefault(alternate.name.upper(), alternate)
        return tuple(unique.values())

    @staticmethod
    def _with_calculated_savings(
        alternate: AlternateRoute,
        current_travel_time: int | None,
    ) -> AlternateRoute:
        if alternate.savings_minutes is not None or alternate.travel_time is None:
            return alternate
        if current_travel_time is None:
            return alternate
        return AlternateRoute(
            name=alternate.name,
            travel_time=alternate.travel_time,
            savings_minutes=max(current_travel_time - alternate.travel_time, 0),
            confidence=alternate.confidence,
            stability=alternate.stability,
            distance_miles=alternate.distance_miles,
        )

    def _extract_incidents(
        self,
        engine_reply: str,
        *,
        source: str,
    ) -> tuple[TrafficIncident | TrafficIncidentSummary, ...]:
        lines = [line.strip().lstrip("•").strip() for line in engine_reply.splitlines()]
        incidents: list[TrafficIncident] = []
        for index, line in enumerate(lines):
            category = self._incident_category(line)
            if category is None:
                continue
            road_name = self._following_road(lines, index)
            incidents.append(
                TrafficIncident(
                    incident_type=category,
                    severity=self._incident_severity(category),
                    location=road_name or "",
                    description=line,
                    source=source,
                    confidence=0.8,
                )
            )
        return tuple(incidents)

    @staticmethod
    def _following_road(lines: list[str], index: int) -> str | None:
        if index + 1 >= len(lines):
            return None
        candidate = lines[index + 1]
        if not candidate or candidate.endswith(":") or "min ago" in candidate.lower():
            return None
        if TrafficIntelligenceService._incident_category(candidate) is not None:
            return None
        return candidate

    @staticmethod
    def _incident_category(text: str) -> IncidentCategory | None:
        value = text.lower()
        if any(term in value for term in ("accident", "collision", "crash")):
            return "Accident"
        if any(term in value for term in ("disabled vehicle", "stalled", "breakdown")):
            return "Disabled Vehicle"
        if any(term in value for term in ("road hazard", "debris", "hazard")):
            return "Road Hazard"
        if any(term in value for term in ("lane closure", "lane closed")):
            return "Lane Closure"
        if any(term in value for term in ("construction", "roadwork", "work zone")):
            return "Construction"
        if any(term in value for term in ("police", "chp", "enforcement")):
            return "Police Activity"
        if any(term in value for term in ("weather", "rain", "fog", "snow", "wind")):
            return "Weather"
        if "fire" in value:
            return "Fire"
        return None

    @staticmethod
    def _incident_severity(category: IncidentCategory) -> Severity:
        levels: dict[IncidentCategory, Severity] = {
            "Accident": "HIGH",
            "Disabled Vehicle": "MODERATE",
            "Road Hazard": "MODERATE",
            "Lane Closure": "HIGH",
            "Construction": "MODERATE",
            "Police Activity": "MODERATE",
            "Weather": "MODERATE",
            "Fire": "SEVERE",
        }
        return levels[category]

    @staticmethod
    def _positive_int(value: object) -> int | None:
        try:
            parsed = int(str(value))
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None

    @staticmethod
    def _positive_float(value: object) -> float | None:
        try:
            parsed = float(str(value))
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None

    @staticmethod
    def _normalized_float(value: object, default: float) -> float:
        parsed = TrafficIntelligenceService._positive_float(value)
        return min(parsed, 1.0) if parsed is not None else default
