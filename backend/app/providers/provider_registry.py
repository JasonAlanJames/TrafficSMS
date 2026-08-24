"""Dynamic registration and discovery for traffic providers."""

from dataclasses import dataclass, replace

from app.models.provider_health import ProviderHealth
from app.models.provider_metadata import ProviderMetadata
from app.providers.provider import TrafficProvider


@dataclass(frozen=True, slots=True)
class RegisteredProvider:
    provider: TrafficProvider
    metadata: ProviderMetadata
    supported_states: tuple[str, ...] = ()


class TrafficProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, RegisteredProvider] = {}
        self._health: dict[str, ProviderHealth] = {}

    def register(self, provider: TrafficProvider, metadata: ProviderMetadata, *, supported_states: tuple[str, ...] = ()) -> None:
        key = metadata.provider_name.upper()
        self._providers[key] = RegisteredProvider(provider, metadata, tuple(state.upper() for state in supported_states))
        self._health.setdefault(key, ProviderHealth(metadata.provider_name, True))

    def get(self, provider_name: str) -> RegisteredProvider | None:
        return self._providers.get(provider_name.upper())

    def set_enabled(self, provider_name: str, enabled: bool) -> None:
        entry = self._providers[provider_name.upper()]
        self._providers[provider_name.upper()] = RegisteredProvider(
            entry.provider,
            replace(entry.metadata, enabled=enabled),
            entry.supported_states,
        )

    def health(self, provider_name: str) -> ProviderHealth:
        return self._health[provider_name.upper()]

    def update_health(self, health: ProviderHealth) -> None:
        self._health[health.provider.upper()] = health

    def entries(self) -> tuple[RegisteredProvider, ...]:
        return tuple(self._providers.values())
