"""Static capabilities metadata for a traffic provider."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderMetadata:
    provider_name: str
    provider_version: str
    provider_type: str
    supports_routes: bool = False
    supports_corridors: bool = False
    supports_airports: bool = False
    supports_incidents: bool = False
    supports_weather: bool = False
    supports_construction: bool = False
    supports_closures: bool = False
    supports_saved_locations: bool = False
    supports_natural_language: bool = False
    priority: int = 100
    enabled: bool = True
