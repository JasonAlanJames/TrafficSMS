import re

from app.models.traffic_request import TrafficRequest
from app.services.traffic_quality_service import normalize_corridor


#
# TRAFFIC
#
# TRAFFIC
# TRAFFIC CORONA
# TRAFFIC CORONA TO ANAHEIM
# TRAFFIC 91 WEST
# TRAFFIC I-15 NORTH
#

ROUTE_RE = re.compile(
    r"^TRAFFIC\s+(.+?)\s+TO\s+(.+)$",
    re.IGNORECASE,
)

CORRIDOR_RE = re.compile(
    r"^TRAFFIC\s+((?:(?:I|SR)-)?\d+)\s+"
    r"(NORTH|SOUTH|EAST|WEST|NB|SB|EB|WB)$",
    re.IGNORECASE,
)
_DIRECTION_ALIASES = {
    "N": "N", "NORTH": "N", "NB": "N", "NORTHBOUND": "N",
    "S": "S", "SOUTH": "S", "SB": "S", "SOUTHBOUND": "S",
    "E": "E", "EAST": "E", "EB": "E", "EASTBOUND": "E",
    "W": "W", "WEST": "W", "WB": "W", "WESTBOUND": "W",
}
_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
}

AREA_RE = re.compile(
    r"^TRAFFIC\s+(.+)$",
    re.IGNORECASE,
)


def parse_traffic_command(
    message: str,
    subscriber_id: int | None = None,
) -> TrafficRequest:
    """
    Converts an incoming SMS command into a TrafficRequest.

    Examples:

        TRAFFIC
        -> commute

        TRAFFIC CORONA
        -> area

        TRAFFIC CORONA TO ANAHEIM
        -> route

        TRAFFIC 91 WEST
        -> corridor
    """

    text = " ".join(message.strip().split())

    #
    # TRAFFIC
    #
    if text.upper() == "TRAFFIC":
        return TrafficRequest(
            mode="commute",
            subscriber_id=subscriber_id,
        )

    #
    # TRAFFIC CORONA TO ANAHEIM
    #
    match = ROUTE_RE.match(text)

    if match:
        return TrafficRequest(
            mode="route",
            origin=match.group(1).strip(),
            destination=match.group(2).strip(),
            subscriber_id=subscriber_id,
        )

    corridor_request = _parse_corridor(text, subscriber_id)
    if corridor_request is not None:
        return corridor_request

    #
    # TRAFFIC CORONA
    #
    match = AREA_RE.match(text)

    if match:
        return TrafficRequest(
            mode="area",
            area=match.group(1).strip(),
            subscriber_id=subscriber_id,
        )

    raise ValueError("Invalid TRAFFIC command.")


def _parse_corridor(text: str, subscriber_id: int | None) -> TrafficRequest | None:
    """Recognize nationwide highway formats only when a direction is supplied."""

    if not text.upper().startswith("TRAFFIC "):
        return None
    tokens = text.upper().split()[1:]
    state_hint = None
    if tokens and tokens[-1] in _STATE_CODES:
        state_hint = tokens.pop()
    if not tokens:
        return None
    direction = _DIRECTION_ALIASES.get(tokens[-1])
    if direction is None:
        return None
    corridor = normalize_corridor(" ".join(tokens[:-1]), state_hint=state_hint)
    if corridor is None:
        return None
    return TrafficRequest(
        mode="corridor",
        corridor=corridor,
        direction=direction,
        subscriber_id=subscriber_id,
    )
