from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class TrafficIncident:
    external_id: str
    category: str
    road_name: str
    area_label: str
    description: str
    severity: int
    updated_at: datetime
    delay_minutes: int | None = None


class TrafficProvider(Protocol):
    async def incidents_for(self, area: str) -> list[TrafficIncident]: ...


class DemoTrafficProvider:
    async def incidents_for(self, area: str) -> list[TrafficIncident]:
        now = datetime.utcnow()
        return [
            TrafficIncident(
                external_id="demo-1",
                category="collision",
                road_name="I-15 N",
                area_label=area,
                description="Collision reported; right lane affected",
                severity=4,
                updated_at=now,
                delay_minutes=14,
            ),
            TrafficIncident(
                external_id="demo-2",
                category="congestion",
                road_name="SR-91 W",
                area_label=area,
                description="Heavy congestion approaching the county line",
                severity=3,
                updated_at=now,
                delay_minutes=11,
            ),
        ]
