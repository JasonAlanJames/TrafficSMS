from dataclasses import dataclass
from typing import Literal


TrafficMode = Literal[
    "area",
    "route",
    "corridor",
    "commute",
]


@dataclass(slots=True)
class TrafficRequest:
    mode: TrafficMode

    #
    # Area traffic
    #
    area: str | None = None

    #
    # Route traffic
    #
    origin: str | None = None

    destination: str | None = None

    #
    # Corridor traffic
    #
    corridor: str | None = None

    direction: str | None = None

    #
    # Saved commute
    #
    subscriber_id: int | None = None