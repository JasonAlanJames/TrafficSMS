"""Provider health state transitions for successful and failed requests."""

from datetime import UTC, datetime

from app.models.provider_health import ProviderHealth


class ProviderFailover:
    def success(self, health: ProviderHealth, latency_ms: int) -> ProviderHealth:
        average = (health.average_latency_ms + max(latency_ms, 0)) // 2 if health.average_latency_ms else max(latency_ms, 0)
        return ProviderHealth(health.provider, True, datetime.now(UTC), health.last_failure, 0, average, min((health.success_rate + 1.0) / 2, 1.0))

    def failure(self, health: ProviderHealth) -> ProviderHealth:
        failures = health.consecutive_failures + 1
        return ProviderHealth(health.provider, failures < 3, health.last_success, datetime.now(UTC), failures, health.average_latency_ms, health.success_rate / 2)
