import asyncio

from app.cache.cache_manager import CacheManager
from app.models.provider_health import ProviderHealth
from app.models.provider_metadata import ProviderMetadata
from app.models.traffic_provider_result import TrafficProviderResult
from app.providers.provider import TrafficProvider
from app.providers.provider_manager import TrafficProviderManager

class Redis:
    def __init__(self): self.data = {}
    def get(self, key): return self.data.get(key)
    def set(self, key, value, ex): self.data[key] = value
    def delete(self, key): self.data.pop(key, None)
    def exists(self, key): return int(key in self.data)
class Provider(TrafficProvider):
    def __init__(self): self.calls = 0
    async def get_route(self, a, b): self.calls += 1; return TrafficProviderResult("Mock", "test")
    async def get_corridor(self, a, b): return TrafficProviderResult("Mock", "test")
    async def get_area(self, a): return TrafficProviderResult("Mock", "test")
    async def get_incidents(self, a): return TrafficProviderResult("Mock", "test")
    async def health(self): return ProviderHealth("Mock", True)
def test_provider_manager_caches_result():
    provider, cache = Provider(), CacheManager(Redis()); manager = TrafficProviderManager(cache_manager=cache)
    manager.registry.register(provider, ProviderMetadata("Mock", "1", "test", supports_routes=True))
    asyncio.run(manager.request("route", "A", "B")); asyncio.run(manager.request("route", "A", "B"))
    assert provider.calls == 1 and cache.metrics.hits == 1
