import asyncio

import pytest

from app.models.provider_health import ProviderHealth
from app.models.provider_metadata import ProviderMetadata
from app.models.traffic_provider_result import TrafficProviderResult
from app.providers.provider import TrafficProvider
from app.providers.provider_manager import ProviderUnavailableError, TrafficProviderManager


class MockProvider(TrafficProvider):
    def __init__(self, name: str, fail: bool = False) -> None:
        self.name, self.fail, self.calls = name, fail, 0
    async def get_route(self, origin: str, destination: str) -> TrafficProviderResult:
        self.calls += 1
        if self.fail: raise RuntimeError("unavailable")
        return TrafficProviderResult(self.name, "mock", coverage=f"{origin}-{destination}")
    async def get_corridor(self, corridor: str, direction: str) -> TrafficProviderResult: return TrafficProviderResult(self.name, "mock")
    async def get_area(self, area: str) -> TrafficProviderResult: return TrafficProviderResult(self.name, "mock")
    async def get_incidents(self, area: str) -> TrafficProviderResult: return TrafficProviderResult(self.name, "mock")
    async def health(self) -> ProviderHealth: return ProviderHealth(self.name, True)


def test_manager_selects_priority_and_fails_over() -> None:
    manager = TrafficProviderManager()
    first, second = MockProvider("DOT", True), MockProvider("Fallback")
    manager.registry.register(first, ProviderMetadata("DOT", "1", "dot", supports_routes=True, priority=1), supported_states=("CA",))
    manager.registry.register(second, ProviderMetadata("Fallback", "1", "mock", supports_routes=True, priority=2))
    result = asyncio.run(manager.request("route", "A", "B", state="CA"))
    assert result.provider == "Fallback"
    assert first.calls == second.calls == 1
    assert manager.metrics("DOT").failed_requests == 1


def test_manager_rejects_no_eligible_provider() -> None:
    with pytest.raises(ProviderUnavailableError):
        asyncio.run(TrafficProviderManager().request("route", "A", "B"))
