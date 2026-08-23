"""Contract tests for future normalized traffic providers."""

import asyncio
from datetime import UTC, datetime

import pytest

from app.models.provider_health import ProviderHealth
from app.models.provider_metadata import ProviderMetadata
from app.models.traffic_provider_result import TrafficProviderResult
from app.providers.provider import TrafficProvider


def test_typed_provider_models_construct() -> None:
    result = TrafficProviderResult(provider="Mock", provider_type="test")
    metadata = ProviderMetadata("Mock", "1", "test", supports_routes=True)
    health = ProviderHealth("Mock", True, last_success=datetime(2026, 1, 1, tzinfo=UTC))
    assert result.provider == "Mock"
    assert metadata.supports_routes is True
    assert health.healthy is True


def test_provider_is_abstract_and_returns_normalized_results() -> None:
    with pytest.raises(TypeError):
        TrafficProvider()

    class Provider(TrafficProvider):
        async def get_route(self, origin: str, destination: str) -> TrafficProviderResult:
            return TrafficProviderResult("Mock", "test", coverage=f"{origin}:{destination}")
        async def get_corridor(self, corridor: str, direction: str) -> TrafficProviderResult:
            return TrafficProviderResult("Mock", "test")
        async def get_area(self, area: str) -> TrafficProviderResult:
            return TrafficProviderResult("Mock", "test")
        async def get_incidents(self, area: str) -> TrafficProviderResult:
            return TrafficProviderResult("Mock", "test")
        async def health(self) -> ProviderHealth:
            return ProviderHealth("Mock", True)

    result = asyncio.run(Provider().get_route("A", "B"))
    assert isinstance(result, TrafficProviderResult)
