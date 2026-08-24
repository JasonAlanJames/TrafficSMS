import asyncio

from app.cache.cache_manager import CacheManager
from app.models.traffic_provider_result import TrafficProviderResult
from app.models.traffic_request import TrafficRequest
from app.services.traffic_service import TrafficService

class Cache(CacheManager):
    def __init__(self, result=None): super().__init__(); self.result=result; self.writes=0
    def get_provider_result(self, key): return self.result
    def set_provider_result(self, key, result, ttl): self.writes += 1; return True
class Manager:
    def __init__(self): self.calls=0
    async def request(self, *args, **kwargs): self.calls += 1; return TrafficProviderResult("Mock", "test")
def test_request_cache_hit_bypasses_provider_manager():
    cached=TrafficProviderResult("Cached", "test"); manager=Manager(); service=TrafficService(provider_manager=manager, cache_manager=Cache(cached))
    assert asyncio.run(service.lookup_provider_result(TrafficRequest(mode="area", area="Corona"))) is cached
    assert manager.calls == 0
def test_request_cache_miss_calls_provider_and_writes():
    manager=Manager(); cache=Cache(); service=TrafficService(provider_manager=manager, cache_manager=cache)
    assert asyncio.run(service.lookup_provider_result(TrafficRequest(mode="area", area="Corona"))).provider == "Mock"
    assert manager.calls == cache.writes == 1
