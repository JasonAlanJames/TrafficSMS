"""Failure-safe centralized JSON Redis cache access."""

import json
from typing import Protocol

from app.cache.cache_metrics import CacheMetrics

class RedisCacheClient(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, ex: int) -> object: ...
    def delete(self, key: str) -> object: ...
    def exists(self, key: str) -> int: ...

class CacheManager:
    def __init__(self, client: RedisCacheClient | None = None) -> None:
        self._client = client
        self.metrics = CacheMetrics()
    def get(self, key: str) -> object | None:
        try:
            if self._client is None: self.metrics.misses += 1; return None
            value = self._client.get(key)
            if value is None: self.metrics.misses += 1; return None
            self.metrics.hits += 1
            return json.loads(value)
        except Exception:
            self.metrics.misses += 1
            return None
    def set(self, key: str, value: object, ttl: int) -> bool:
        try:
            if self._client is None: return False
            self._client.set(key, json.dumps(value), ex=ttl); self.metrics.writes += 1; return True
        except Exception: return False
    def delete(self, key: str) -> bool:
        try:
            if self._client is None: return False
            self._client.delete(key); self.metrics.deletes += 1; return True
        except Exception: return False
    def exists(self, key: str) -> bool:
        try: return bool(self._client and self._client.exists(key))
        except Exception: return False
