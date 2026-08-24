"""Failure-safe centralized JSON Redis cache access."""

import json
from dataclasses import asdict
from datetime import timedelta
from typing import Protocol

from app.cache.cache_metrics import CacheMetrics
from app.models.traffic_provider_result import ProviderResultMetadata, TrafficProviderResult

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

    def get_provider_result(self, key: str) -> TrafficProviderResult | None:
        value = self.get(key)
        if not isinstance(value, dict): return None
        try:
            metadata = value.get("metadata", {})
            return TrafficProviderResult(
                provider=str(value["provider"]), provider_type=str(value["provider_type"]),
                confidence=float(value.get("confidence", 0.0)), latency_ms=int(value.get("latency_ms", 0)),
                coverage=str(value.get("coverage", "")),
                metadata=ProviderResultMetadata(
                    request_id=str(metadata.get("request_id", "")),
                    cache_hit=bool(metadata.get("cache_hit", False)),
                    cache_age=timedelta(seconds=float(metadata.get("cache_age", 0))),
                    warnings=tuple(metadata.get("warnings", ())), errors=tuple(metadata.get("errors", ())),
                ),
            )
        except (KeyError, TypeError, ValueError): return None

    def set_provider_result(self, key: str, result: TrafficProviderResult, ttl: int) -> bool:
        payload = asdict(result)
        payload["freshness"] = result.freshness.total_seconds()
        payload["generated_at"] = result.generated_at.isoformat()
        payload["metadata"]["cache_age"] = result.metadata.cache_age.total_seconds()
        return self.set(key, payload, ttl)
