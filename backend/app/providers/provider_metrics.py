"""Reusable operational metrics for provider-manager requests."""

from dataclasses import dataclass


@dataclass(slots=True)
class ProviderMetrics:
    usage_count: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_response_time_ms: int = 0
    estimated_api_cost: float = 0.0

    def record(self, *, success: bool, latency_ms: int, cache_hit: bool) -> None:
        self.usage_count += 1
        self.total_response_time_ms += max(latency_ms, 0)
        self.successful_requests += int(success)
        self.failed_requests += int(not success)
        self.cache_hits += int(cache_hit)
        self.cache_misses += int(not cache_hit)
