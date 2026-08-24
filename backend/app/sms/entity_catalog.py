"""Data-driven nationwide entities and deterministic target resolution."""

from __future__ import annotations

from dataclasses import dataclass
import re


_DIRECTIONS = {"NORTH", "SOUTH", "EAST", "WEST"}
_SAVED_LOCATIONS = {"HOME", "WORK", "GYM", "SCHOOL"}


@dataclass(frozen=True)
class EntityDefinition:
    """A canonical nationwide entity and the aliases it accepts."""

    canonical_name: str
    entity_type: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class EntityResolution:
    """Canonical text, extracted entities, and unknown target diagnostics."""

    normalized_text: str
    entities: dict[str, str]
    unresolved_targets: tuple[str, ...] = ()


_STATE_DATA = (
    ("ALABAMA", "AL"), ("ALASKA", "AK"), ("ARIZONA", "AZ"),
    ("ARKANSAS", "AR"), ("CALIFORNIA", "CA"), ("COLORADO", "CO"),
    ("CONNECTICUT", "CT"), ("DELAWARE", "DE"), ("FLORIDA", "FL"),
    ("GEORGIA", "GA"), ("HAWAII", "HI"), ("IDAHO", "ID"),
    ("ILLINOIS", "IL"), ("INDIANA", "IN"), ("IOWA", "IA"),
    ("KANSAS", "KS"), ("KENTUCKY", "KY"), ("LOUISIANA", "LA"),
    ("MAINE", "ME"), ("MARYLAND", "MD"), ("MASSACHUSETTS", "MA"),
    ("MICHIGAN", "MI"), ("MINNESOTA", "MN"), ("MISSISSIPPI", "MS"),
    ("MISSOURI", "MO"), ("MONTANA", "MT"), ("NEBRASKA", "NE"),
    ("NEVADA", "NV"), ("NEW HAMPSHIRE", "NH"), ("NEW JERSEY", "NJ"),
    ("NEW MEXICO", "NM"), ("NEW YORK", "NY"), ("NORTH CAROLINA", "NC"),
    ("NORTH DAKOTA", "ND"), ("OHIO", "OH"), ("OKLAHOMA", "OK"),
    ("OREGON", "OR"), ("PENNSYLVANIA", "PA"), ("RHODE ISLAND", "RI"),
    ("SOUTH CAROLINA", "SC"), ("SOUTH DAKOTA", "SD"), ("TENNESSEE", "TN"),
    ("TEXAS", "TX"), ("UTAH", "UT"), ("VERMONT", "VT"),
    ("VIRGINIA", "VA"), ("WASHINGTON", "WA"), ("WEST VIRGINIA", "WV"),
    ("WISCONSIN", "WI"), ("WYOMING", "WY"),
)

_CITY_NAMES = (
    "CORONA", "RIVERSIDE", "ANAHEIM", "IRVINE", "FULLERTON", "MIAMI",
    "CHICAGO", "BOSTON", "ATLANTA", "DALLAS", "DENVER", "SEATTLE",
    "NASHVILLE", "PHOENIX", "LAS VEGAS", "ORLANDO", "HOUSTON", "ASPEN",
    "NEW YORK", "LOS ANGELES", "SAN FRANCISCO", "WASHINGTON DC",
    "PHILADELPHIA", "DETROIT", "MINNEAPOLIS", "PORTLAND", "SAN DIEGO",
    "AUSTIN", "CHARLOTTE", "TAMPA",
)


def _state_entities() -> tuple[EntityDefinition, ...]:
    return tuple(
        EntityDefinition(name, "state", aliases=(abbreviation,))
        for name, abbreviation in _STATE_DATA
    )


def _city_entities() -> tuple[EntityDefinition, ...]:
    aliases = {"NEW YORK": ("NYC",), "WASHINGTON DC": ("WASHINGTON, DC",)}
    return tuple(
        EntityDefinition(name, "city", aliases=aliases.get(name, ()))
        for name in _CITY_NAMES
    )


DEFAULT_ENTITY_DEFINITIONS = (
    *_state_entities(),
    *_city_entities(),
    EntityDefinition(
        "LOS ANGELES INTERNATIONAL AIRPORT",
        "airport",
        aliases=("LAX",),
    ),
    EntityDefinition("JOHN F KENNEDY INTERNATIONAL AIRPORT", "airport", aliases=("JFK",)),
    EntityDefinition("CHICAGO O HARE INTERNATIONAL AIRPORT", "airport", aliases=("ORD",)),
    EntityDefinition("DALLAS FORT WORTH INTERNATIONAL AIRPORT", "airport", aliases=("DFW",)),
    EntityDefinition("HARTSFIELD JACKSON ATLANTA INTERNATIONAL AIRPORT", "airport", aliases=("ATL",)),
    EntityDefinition("PHOENIX SKY HARBOR INTERNATIONAL AIRPORT", "airport", aliases=("PHX",)),
    EntityDefinition("DENVER INTERNATIONAL AIRPORT", "airport", aliases=("DEN",)),
    EntityDefinition("HARRY REID INTERNATIONAL AIRPORT", "airport", aliases=("LAS",)),
    EntityDefinition("SEATTLE TACOMA INTERNATIONAL AIRPORT", "airport", aliases=("SEA",)),
    EntityDefinition("BOSTON LOGAN INTERNATIONAL AIRPORT", "airport", aliases=("BOS",)),
    EntityDefinition("ORLANDO INTERNATIONAL AIRPORT", "airport", aliases=("MCO",)),
    EntityDefinition("I-95", "interstate", aliases=("THE 95", "95 FREEWAY")),
    EntityDefinition("I-90", "interstate"),
    EntityDefinition("I-80", "interstate"),
    EntityDefinition("I-70", "interstate"),
    EntityDefinition("I-40", "interstate"),
    EntityDefinition("I-35", "interstate"),
    EntityDefinition("I-10", "interstate"),
    EntityDefinition("I-5", "interstate", aliases=("5 FREEWAY",)),
    EntityDefinition("I-15", "interstate"),
    EntityDefinition("I-405", "interstate", aliases=("405", "405 FREEWAY")),
    EntityDefinition("US-1", "us_route"),
    EntityDefinition("US-101", "us_route", aliases=("101 FREEWAY",)),
        EntityDefinition(
            "SR-91",
            "state_route",
            aliases=("91", "THE 91", "91 FREEWAY", "RIVERSIDE FREEWAY"),
        ),
    EntityDefinition("SR-55", "state_route"),
    EntityDefinition("SR-57", "state_route"),
    EntityDefinition("SR-60", "state_route"),
    EntityDefinition("SR-73", "state_route"),
    EntityDefinition("SR-78", "state_route"),
    EntityDefinition("SR-241", "state_route"),
    EntityDefinition("FLORIDA S TURNPIKE", "toll_road", aliases=("FLORIDA TURNPIKE",)),
    EntityDefinition("NEW JERSEY TURNPIKE", "toll_road"),
    EntityDefinition("MASSACHUSETTS TURNPIKE", "toll_road", aliases=("MASS PIKE",)),
    EntityDefinition("DISNEYLAND", "landmark", aliases=("DISNEY",)),
    EntityDefinition("TIMES SQUARE", "landmark"),
    EntityDefinition("GOLDEN GATE BRIDGE", "landmark"),
    EntityDefinition("YELLOWSTONE NATIONAL PARK", "national_park", aliases=("YELLOWSTONE",)),
    EntityDefinition("YOSEMITE NATIONAL PARK", "national_park", aliases=("YOSEMITE",)),
    EntityDefinition("GRAND CANYON NATIONAL PARK", "national_park", aliases=("GRAND CANYON",)),
)


class EntityCatalog:
    """Single source of truth for deterministic nationwide traffic entities."""

    def __init__(
        self,
        definitions: tuple[EntityDefinition, ...] = DEFAULT_ENTITY_DEFINITIONS,
    ):
        """Index canonical names and aliases for deterministic replacement."""

        self._definitions = {
            definition.canonical_name: definition for definition in definitions
        }
        aliases: list[tuple[str, str]] = []
        for definition in definitions:
            for alias in definition.aliases:
                aliases.append((alias, definition.canonical_name))
        self._aliases = tuple(sorted(aliases, key=lambda item: len(item[0]), reverse=True))

    def expand_aliases(self, normalized_text: str) -> str:
        """Replace only catalog-defined aliases with canonical names."""

        resolved_text = normalized_text
        for alias, canonical_name in self._aliases:
            pattern = self._alias_pattern(alias)
            resolved_text = pattern.sub(canonical_name, resolved_text)
        return resolved_text

    @staticmethod
    def _alias_pattern(alias: str) -> re.Pattern[str]:
        """Avoid expanding airport code LAS inside the Las Vegas city name."""

        if alias == "LAS":
            return re.compile(r"(?<![\w-])LAS(?![\w-]|\s+VEGAS)")
        return re.compile(rf"(?<![\w-]){re.escape(alias)}(?![\w-])")

    def resolve(self, normalized_text: str) -> EntityResolution:
        """Validate traffic operands and preserve their canonical entity types."""

        if not normalized_text.startswith("TRAFFIC"):
            return EntityResolution(normalized_text, {})

        arguments = tuple(normalized_text.split()[1:])
        if not arguments or arguments[0] == "FROM":
            return EntityResolution(normalized_text, {})

        route_separator_count = arguments.count("TO")
        if route_separator_count == 1:
            route_index = arguments.index("TO")
            if route_index == 0 or route_index == len(arguments) - 1:
                return EntityResolution(normalized_text, {})
            origin = " ".join(arguments[:route_index])
            destination = " ".join(arguments[route_index + 1:])
            return self._resolve_route(normalized_text, origin, destination)
        if route_separator_count > 1:
            return EntityResolution(normalized_text, {}, ("TO",))

        target = " ".join(arguments)
        return self._resolve_target_command(normalized_text, target)

    def _resolve_route(
        self,
        normalized_text: str,
        origin: str,
        destination: str,
    ) -> EntityResolution:
        origin_definition = self._find_target(origin)
        destination_definition = self._find_target(destination)
        unresolved = tuple(
            target
            for target, definition in (
                (origin, origin_definition),
                (destination, destination_definition),
            )
            if definition is None
        )
        if unresolved:
            return EntityResolution(normalized_text, {}, unresolved)

        return EntityResolution(
            normalized_text,
            {
                "origin": origin,
                "origin_type": origin_definition.entity_type,
                "destination": destination,
                "destination_type": destination_definition.entity_type,
                "route": f"{origin} TO {destination}",
            },
        )

    def _resolve_target_command(
        self,
        normalized_text: str,
        target: str,
    ) -> EntityResolution:
        target_parts = target.split()
        direction = None
        if len(target_parts) > 1 and target_parts[-1] in _DIRECTIONS:
            direction = target_parts.pop()
        entity_target = " ".join(target_parts)
        definition = self._find_target(entity_target)
        if definition is None:
            return EntityResolution(normalized_text, {}, (entity_target,))

        entities = self._target_entities(entity_target, definition)
        if direction:
            entities["direction"] = direction
        return EntityResolution(normalized_text, entities)

    def _find_target(self, target: str) -> EntityDefinition | None:
        if target in _SAVED_LOCATIONS:
            return EntityDefinition(target, "saved_location")
        return self._definitions.get(target)

    @staticmethod
    def _target_entities(
        target: str,
        definition: EntityDefinition,
    ) -> dict[str, str]:
        if definition.entity_type in {"interstate", "us_route", "state_route"}:
            return {"highway": target, "corridor": target}
        if definition.entity_type == "saved_location":
            return {"saved_location": target}
        return {definition.entity_type: target}


entity_catalog = EntityCatalog()
