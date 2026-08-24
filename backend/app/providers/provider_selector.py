"""Deterministic capability, state, priority, and health provider selection."""

from app.providers.provider_registry import RegisteredProvider, TrafficProviderRegistry


class ProviderSelector:
    def select(self, registry: TrafficProviderRegistry, *, capability: str, state: str = "") -> tuple[RegisteredProvider, ...]:
        state = state.upper()
        capability_name = {"route": "routes", "corridor": "corridors", "area": "routes", "incidents": "incidents"}.get(capability, capability)
        selected = []
        for entry in registry.entries():
            health = registry.health(entry.metadata.provider_name)
            if not entry.metadata.enabled or not health.healthy:
                continue
            if state and entry.supported_states and state not in entry.supported_states:
                continue
            if not getattr(entry.metadata, f"supports_{capability_name}", False):
                continue
            selected.append(entry)
        return tuple(sorted(selected, key=lambda entry: entry.metadata.priority))
