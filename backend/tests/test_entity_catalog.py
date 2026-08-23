"""Revision 3.1 tests for nationwide catalog-backed entity resolution."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import cast

import pytest
from sqlalchemy.orm import Session

from app.models.entities import User
from app.services.traffic_service import TrafficService
from app.sms.context import SMSContext
from app.sms.entity_catalog import entity_catalog
from app.sms.intent_resolver import SMSIntentResolver
from app.sms.intents import SMSIntent
from app.sms.parser import SMSParser


def _context(message: str, user: User | None = None) -> SMSContext:
    parsed = SMSParser().parse(message)
    return SMSContext(
        db=cast(Session, object()),
        phone_number="+17145550123",
        user=user or User(
            id=1,
            email="driver@example.com",
            phone_e164="+17145550123",
            home_location="Corona, CA",
            work_location="Anaheim, CA",
        ),
        subscription=None,
        normalized_text=parsed.normalized_text,
        raw_text=parsed.raw_text,
        tokens=parsed.tokens,
        parsed_arguments=parsed.arguments,
        timestamp=datetime.now(UTC),
    )


@pytest.mark.parametrize(
    ("message", "canonical", "entity_key", "entity_value"),
    [
        ("TRAFFIC MIAMI", "TRAFFIC MIAMI", "city", "MIAMI"),
        ("TRAFFIC CHICAGO", "TRAFFIC CHICAGO", "city", "CHICAGO"),
        ("TRAFFIC BOSTON", "TRAFFIC BOSTON", "city", "BOSTON"),
        ("TRAFFIC ATLANTA", "TRAFFIC ATLANTA", "city", "ATLANTA"),
        ("TRAFFIC DALLAS", "TRAFFIC DALLAS", "city", "DALLAS"),
        ("TRAFFIC DENVER", "TRAFFIC DENVER", "city", "DENVER"),
        ("TRAFFIC SEATTLE", "TRAFFIC SEATTLE", "city", "SEATTLE"),
        ("TRAFFIC NASHVILLE", "TRAFFIC NASHVILLE", "city", "NASHVILLE"),
        ("TRAFFIC PHOENIX", "TRAFFIC PHOENIX", "city", "PHOENIX"),
        ("TRAFFIC LAS VEGAS", "TRAFFIC LAS VEGAS", "city", "LAS VEGAS"),
        ("TRAFFIC THE 95 NORTH", "TRAFFIC I-95 NORTH", "highway", "I-95"),
        ("TRAFFIC US-101", "TRAFFIC US-101", "highway", "US-101"),
        (
            "TRAFFIC YELLOWSTONE",
            "TRAFFIC YELLOWSTONE NATIONAL PARK",
            "national_park",
            "YELLOWSTONE NATIONAL PARK",
        ),
    ],
)
def test_catalog_resolves_nationwide_entities(
    message: str,
    canonical: str,
    entity_key: str,
    entity_value: str,
) -> None:
    """Cities, highways, routes, and landmarks use one catalog path."""

    expanded = entity_catalog.expand_aliases(message)
    resolution = entity_catalog.resolve(expanded)

    assert resolution.normalized_text == canonical
    assert resolution.unresolved_targets == ()
    assert resolution.entities[entity_key] == entity_value


@pytest.mark.parametrize(
    ("message", "canonical", "origin", "destination"),
    [
        ("TRAFFIC MIAMI TO ORLANDO", "TRAFFIC MIAMI TO ORLANDO", "MIAMI", "ORLANDO"),
        ("TRAFFIC DALLAS TO HOUSTON", "TRAFFIC DALLAS TO HOUSTON", "DALLAS", "HOUSTON"),
        ("TRAFFIC DENVER TO ASPEN", "TRAFFIC DENVER TO ASPEN", "DENVER", "ASPEN"),
        (
            "TRAFFIC BOSTON TO JFK",
            "TRAFFIC BOSTON TO JOHN F KENNEDY INTERNATIONAL AIRPORT",
            "BOSTON",
            "JOHN F KENNEDY INTERNATIONAL AIRPORT",
        ),
    ],
)
def test_catalog_resolves_nationwide_routes(
    message: str,
    canonical: str,
    origin: str,
    destination: str,
) -> None:
    """Nationwide route endpoints remain structured for existing routing."""

    expanded = entity_catalog.expand_aliases(message)
    resolution = entity_catalog.resolve(expanded)

    assert resolution.normalized_text == canonical
    assert resolution.unresolved_targets == ()
    assert resolution.entities["origin"] == origin
    assert resolution.entities["destination"] == destination


@pytest.mark.parametrize(
    ("airport_code", "airport_name"),
    [
        ("LAX", "LOS ANGELES INTERNATIONAL AIRPORT"),
        ("JFK", "JOHN F KENNEDY INTERNATIONAL AIRPORT"),
        ("ORD", "CHICAGO O HARE INTERNATIONAL AIRPORT"),
        ("DFW", "DALLAS FORT WORTH INTERNATIONAL AIRPORT"),
        ("ATL", "HARTSFIELD JACKSON ATLANTA INTERNATIONAL AIRPORT"),
        ("PHX", "PHOENIX SKY HARBOR INTERNATIONAL AIRPORT"),
        ("DEN", "DENVER INTERNATIONAL AIRPORT"),
        ("LAS", "HARRY REID INTERNATIONAL AIRPORT"),
        ("SEA", "SEATTLE TACOMA INTERNATIONAL AIRPORT"),
        ("BOS", "BOSTON LOGAN INTERNATIONAL AIRPORT"),
        ("MCO", "ORLANDO INTERNATIONAL AIRPORT"),
    ],
)
def test_catalog_resolves_airport_codes(
    airport_code: str,
    airport_name: str,
) -> None:
    """Every supported airport code expands through the shared catalog."""

    expanded = entity_catalog.expand_aliases(f"TRAFFIC {airport_code}")
    resolution = entity_catalog.resolve(expanded)

    assert resolution.unresolved_targets == ()
    assert resolution.entities["airport"] == airport_name


@pytest.mark.parametrize(
    "highway",
    ("I-95", "I-90", "I-80", "I-70", "I-40", "I-35", "I-10", "I-5", "I-15", "I-405"),
)
def test_catalog_resolves_supported_interstates(highway: str) -> None:
    """Interstate support is catalog-driven rather than state-specific logic."""

    resolution = entity_catalog.resolve(f"TRAFFIC {highway}")

    assert resolution.unresolved_targets == ()
    assert resolution.entities["highway"] == highway


def test_unknown_catalog_entity_is_not_routed_or_sent_to_ai() -> None:
    """Unknown deterministic targets remain safely unknown."""

    context = _context("TRAFFIC NOTAREALPLACE")
    intent = asyncio.run(SMSIntentResolver().resolve(context))

    assert intent is SMSIntent.UNKNOWN
    assert context.metadata["unresolved_entities"] == ["NOTAREALPLACE"]


def test_nationwide_route_reaches_existing_traffic_service() -> None:
    """Catalog canonicalization feeds the unchanged TrafficService route parser."""

    context = _context("TRAFFIC BOSTON TO JFK")
    assert asyncio.run(SMSIntentResolver().resolve(context)) is SMSIntent.TRAFFIC_ROUTE

    preparation = TrafficService().prepare_request(context)

    assert preparation.error_message is None
    assert preparation.request is not None
    assert preparation.request.mode == "route"
    assert preparation.request.origin == "BOSTON"
    assert preparation.request.destination == "JOHN F KENNEDY INTERNATIONAL AIRPORT"
