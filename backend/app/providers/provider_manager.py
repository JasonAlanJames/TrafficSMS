"""Provider-agnostic execution, metrics, health, and automatic failover."""

from time import perf_counter

from app.models.traffic_provider_result import TrafficProviderResult
from app.providers.provider_failover import ProviderFailover
from app.providers.provider_metrics import ProviderMetrics
from app.providers.provider_registry import TrafficProviderRegistry
from app.providers.provider_selector import ProviderSelector


class ProviderUnavailableError(RuntimeError): pass


class TrafficProviderManager:
    def __init__(self, registry: TrafficProviderRegistry | None = None) -> None:
        self.registry = registry or TrafficProviderRegistry()
        self._selector = ProviderSelector()
        self._failover = ProviderFailover()
        self._metrics: dict[str, ProviderMetrics] = {}

    def metrics(self, provider_name: str) -> ProviderMetrics:
        return self._metrics.setdefault(provider_name.upper(), ProviderMetrics())

    async def request(self, capability: str, *args: str, state: str = "") -> TrafficProviderResult:
        providers = self._selector.select(self.registry, capability=capability, state=state)
        for entry in providers:
            started = perf_counter()
            metric = self.metrics(entry.metadata.provider_name)
            try:
                result = await getattr(entry.provider, f"get_{capability}")(*args)
                latency = int((perf_counter() - started) * 1000)
                metric.record(success=True, latency_ms=latency, cache_hit=result.metadata.cache_hit)
                self.registry.update_health(self._failover.success(self.registry.health(entry.metadata.provider_name), latency))
                return result
            except Exception:
                metric.record(success=False, latency_ms=int((perf_counter() - started) * 1000), cache_hit=False)
                self.registry.update_health(self._failover.failure(self.registry.health(entry.metadata.provider_name)))
        raise ProviderUnavailableError("No eligible traffic provider succeeded.")
