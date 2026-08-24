from app.cache.cache_manager import CacheManager
from app.cache import cache_keys

class Redis:
    def __init__(self): self.values = {}
    def get(self, key): return self.values.get(key)
    def set(self, key, value, ex): self.values[key] = value
    def delete(self, key): self.values.pop(key, None)
    def exists(self, key): return int(key in self.values)

def test_cache_json_metrics_and_keys():
    cache = CacheManager(Redis()); key = cache_keys.traffic("CA", "Corona")
    assert cache.get(key) is None
    assert cache.set(key, {"delay": 12}, 60)
    assert cache.get(key) == {"delay": 12}
    assert cache.exists(key)
    assert cache.delete(key)
    assert cache.metrics.hits == cache.metrics.misses == cache.metrics.writes == cache.metrics.deletes == 1

def test_cache_bypasses_unavailable_redis():
    cache = CacheManager()
    assert cache.get("missing") is None
    assert cache.set("missing", {"x": 1}, 1) is False
