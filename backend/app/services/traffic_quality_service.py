"""Nationwide, deterministic traffic-request quality classification."""

from __future__ import annotations

import re

from app.models.traffic_quality import TrafficQualityAssessment
from app.models.traffic_request import TrafficRequest


_STATE_PAIRS = (
    ("ALABAMA", "AL"), ("ALASKA", "AK"), ("ARIZONA", "AZ"), ("ARKANSAS", "AR"),
    ("CALIFORNIA", "CA"), ("COLORADO", "CO"), ("CONNECTICUT", "CT"), ("DELAWARE", "DE"),
    ("FLORIDA", "FL"), ("GEORGIA", "GA"), ("HAWAII", "HI"), ("IDAHO", "ID"),
    ("ILLINOIS", "IL"), ("INDIANA", "IN"), ("IOWA", "IA"), ("KANSAS", "KS"),
    ("KENTUCKY", "KY"), ("LOUISIANA", "LA"), ("MAINE", "ME"), ("MARYLAND", "MD"),
    ("MASSACHUSETTS", "MA"), ("MICHIGAN", "MI"), ("MINNESOTA", "MN"), ("MISSISSIPPI", "MS"),
    ("MISSOURI", "MO"), ("MONTANA", "MT"), ("NEBRASKA", "NE"), ("NEVADA", "NV"),
    ("NEW HAMPSHIRE", "NH"), ("NEW JERSEY", "NJ"), ("NEW MEXICO", "NM"), ("NEW YORK", "NY"),
    ("NORTH CAROLINA", "NC"), ("NORTH DAKOTA", "ND"), ("OHIO", "OH"), ("OKLAHOMA", "OK"),
    ("OREGON", "OR"), ("PENNSYLVANIA", "PA"), ("RHODE ISLAND", "RI"), ("SOUTH CAROLINA", "SC"),
    ("SOUTH DAKOTA", "SD"), ("TENNESSEE", "TN"), ("TEXAS", "TX"), ("UTAH", "UT"),
    ("VERMONT", "VT"), ("VIRGINIA", "VA"), ("WASHINGTON", "WA"), ("WEST VIRGINIA", "WV"),
    ("WISCONSIN", "WI"), ("WYOMING", "WY"),
)
_STATE_BY_NAME = dict(_STATE_PAIRS)
_STATE_NAMES_BY_CODE = {code: name for name, code in _STATE_PAIRS}
_DIRECTIONS = {"N": "N", "NORTH": "N", "NB": "N", "NORTHBOUND": "N", "S": "S", "SOUTH": "S", "SB": "S", "SOUTHBOUND": "S", "E": "E", "EAST": "E", "EB": "E", "EASTBOUND": "E", "W": "W", "WEST": "W", "WB": "W", "WESTBOUND": "W"}
_AMBIGUOUS_AREAS = {"SPRINGFIELD", "WASHINGTON", "DOWNTOWN"}
_UNSUPPORTED_TOKENS = {"MARS", "ATLANTIS", "LONDON", "MEXICO", "UK", "CANADA", "EUROPE"}
_INTERSTATE_NUMBERS = {"5", "10", "15", "35", "40", "70", "80", "90", "95", "405"}
_ZIP_RE = re.compile(r"^\d{5}$")


class TrafficQualityService:
    """Classify requests without geocoding, providers, AI, or network calls."""

    def assess(self, request: TrafficRequest) -> TrafficQualityAssessment:
        if request.mode in {"route", "commute"}:
            return self._route(request)
        if request.mode == "corridor":
            return self._corridor(request)
        return self._area(request)

    def _area(self, request: TrafficRequest) -> TrafficQualityAssessment:
        query = " ".join((request.area or "").upper().split())
        if not query:
            return self._missing("area")
        if _ZIP_RE.fullmatch(query):
            return TrafficQualityAssessment(query, query, "zip", 0.9, "high", "no_active_internal_data", True, zip_code=query, location_text=query)
        if any(token in _UNSUPPORTED_TOKENS for token in query.split()):
            return self._unsupported(query, "unsupported_region")
        if query.isdigit():
            return self._ambiguous(query, "corridor")
        if normalize_corridor(query) is not None:
            return self._missing("corridor")
        city, state_code = self._city_state(query)
        if city and state_code:
            return TrafficQualityAssessment(query, f"{city}, {state_code}", "area", 0.9, "high", "no_active_internal_data", True, location_text=f"{city}, {state_code}", city=city, state=_STATE_NAMES_BY_CODE[state_code], state_abbreviation=state_code)
        if query in _AMBIGUOUS_AREAS:
            return self._ambiguous(query, "area")
        if len(query) < 3 or not re.fullmatch(r"[A-Z][A-Z .'-]+", query):
            return self._unsupported(query, "unknown_location")
        return TrafficQualityAssessment(query, query, "area", 0.55, "medium", "no_active_internal_data", True, location_text=query, city=query)

    def _corridor(self, request: TrafficRequest) -> TrafficQualityAssessment:
        corridor = " ".join((request.corridor or "").upper().split())
        direction = _DIRECTIONS.get((request.direction or "").upper())
        if not corridor or not direction:
            return self._missing("corridor")
        canonical = normalize_corridor(corridor)
        if canonical is None:
            return self._ambiguous(corridor, "corridor")
        highway_system, number = canonical.split("-", 1)
        return TrafficQualityAssessment(
            f"{corridor} {direction}", f"{canonical} {direction}", "corridor", 0.9,
            "high", "no_active_internal_data", True, corridor=canonical,
            highway_system=highway_system, highway_number=number, direction=direction,
        )

    def _route(self, request: TrafficRequest) -> TrafficQualityAssessment:
        origin = " ".join((request.origin or "").split())
        destination = " ".join((request.destination or "").split())
        if not origin or not destination:
            return self._missing("route")
        origin_quality = self._endpoint_quality(origin)
        destination_quality = self._endpoint_quality(destination)
        if origin_quality.is_ambiguous or destination_quality.is_ambiguous:
            return self._ambiguous(f"{origin} TO {destination}", "route")
        if not origin_quality.is_supported or not destination_quality.is_supported:
            return self._unsupported(f"{origin} TO {destination}", "unsupported_region")
        return TrafficQualityAssessment(
            f"{origin} TO {destination}", f"{origin} TO {destination}", "route", min(origin_quality.confidence, destination_quality.confidence),
            "high" if min(origin_quality.confidence, destination_quality.confidence) >= 0.8 else "medium",
            "no_active_internal_data", True, origin_text=origin, destination_text=destination,
        )

    def _endpoint_quality(self, text: str) -> TrafficQualityAssessment:
        return self._area(TrafficRequest(mode="area", area=text))

    @staticmethod
    def _city_state(query: str) -> tuple[str | None, str | None]:
        for state_name, code in sorted(_STATE_PAIRS, key=lambda item: len(item[0]), reverse=True):
            if query.endswith(f" {state_name}"):
                return query[: -len(state_name)].strip(" ,"), code
            if query.endswith(f" {code}"):
                return query[: -len(code)].strip(" ,"), code
        return None, None

    @staticmethod
    def _missing(request_type: str) -> TrafficQualityAssessment:
        return TrafficQualityAssessment("", "", request_type, 0.0, "unknown", "missing_location", False, requires_more_detail=True, fallback_reason="missing_location", user_message="TrafficSMS needs a U.S. city/state, ZIP code, or highway direction.")

    @staticmethod
    def _ambiguous(query: str, request_type: str) -> TrafficQualityAssessment:
        return TrafficQualityAssessment(query, query, request_type, 0.2, "low", "ambiguous_location", False, is_ambiguous=True, requires_more_detail=True, fallback_reason="ambiguous_location", user_message="I need a little more detail. Try: TRAFFIC I-15 N, TRAFFIC Springfield MO, or TRAFFIC 92882.")

    @staticmethod
    def _unsupported(query: str, reason: str) -> TrafficQualityAssessment:
        return TrafficQualityAssessment(query, query, "unknown", 0.0, "unsupported", "unsupported_region", False, fallback_reason=reason, user_message="I could not match that to a supported U.S. traffic area yet. Try a U.S. city/state, ZIP code, or highway like TRAFFIC I-15 N.")


def normalize_corridor(value: str, *, state_hint: str | None = None) -> str | None:
    """Return a nationwide canonical highway name without state-specific guessing."""

    text = " ".join(value.upper().replace("INTERSTATE", "I").replace("ROUTE", "US").replace("HIGHWAY", "US").replace("HWY", "US").replace("FREEWAY", "").split())
    text = re.sub(r"\b(I|US|SR|CA)\s*-?\s*(\d{1,3})\b", r"\1-\2", text)
    match = re.fullmatch(r"(I|US|SR|CA)-(\d{1,3})", text)
    if match:
        system, number = match.groups()
        return f"SR-{number}" if system == "CA" else f"{system}-{number}"
    if text.isdigit():
        if text in _INTERSTATE_NUMBERS:
            return f"I-{text}"
        if text == "101":
            return "US-101"
        if state_hint:
            return f"SR-{text}"
    return None
