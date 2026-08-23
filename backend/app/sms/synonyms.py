"""Deterministic synonym expansion for inbound SMS text."""

from __future__ import annotations

from dataclasses import dataclass

from app.sms.entity_catalog import EntityCatalog, entity_catalog


@dataclass(frozen=True)
class SynonymResolution:
    """Canonical text and entities produced by deterministic synonym expansion."""

    normalized_text: str
    entities: dict[str, str]


class SMSSynonymDictionary:
    """Expand known traffic aliases without invoking an AI provider."""

    def __init__(self, catalog: EntityCatalog = entity_catalog):
        """Use the nationwide catalog as the sole alias data source."""

        self._catalog = catalog

    def resolve(self, normalized_text: str) -> SynonymResolution:
        """Return a synonym-expanded command representation and entities."""

        return SynonymResolution(
            normalized_text=self._catalog.expand_aliases(normalized_text),
            entities={},
        )
