"""Abstract provider contract; implementations return normalized results only."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.provider_health import ProviderHealth
from app.models.traffic_provider_result import TrafficProviderResult


class TrafficProvider(ABC):
    """Base class for asynchronous, provider-neutral traffic retrieval."""

    @abstractmethod
    async def get_route(self, origin: str, destination: str) -> TrafficProviderResult: ...

    @abstractmethod
    async def get_corridor(self, corridor: str, direction: str) -> TrafficProviderResult: ...

    @abstractmethod
    async def get_area(self, area: str) -> TrafficProviderResult: ...

    @abstractmethod
    async def get_incidents(self, area: str) -> TrafficProviderResult: ...

    @abstractmethod
    async def health(self) -> ProviderHealth: ...
