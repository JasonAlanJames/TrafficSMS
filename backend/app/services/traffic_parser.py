import re

from app.models.traffic_request import TrafficRequest


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

    #
    # TRAFFIC 91 WEST
    #
    match = CORRIDOR_RE.match(text)

    if match:
        corridor = match.group(1).upper()

        if corridor.isdigit():
            corridor = f"SR-{corridor}"

        direction = match.group(2).upper()

        direction = {
            "NB": "NORTH",
            "SB": "SOUTH",
            "EB": "EAST",
            "WB": "WEST",
        }.get(direction, direction)

        return TrafficRequest(
            mode="corridor",
            corridor=corridor,
            direction=direction,
            subscriber_id=subscriber_id,
        )

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
