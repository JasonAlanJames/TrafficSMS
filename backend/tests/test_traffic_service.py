"""Unit tests for deterministic TrafficService command preparation."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import cast

import pytest
from sqlalchemy.orm import Session

from app.models.entities import User
from app.services.location_resolver import LocationResolver
from app.services.traffic_service import TrafficService
from app.sms.context import SMSContext
from app.sms.parser import SMSParser


def _context(message: str, user: User) -> SMSContext:
    parsed = SMSParser().parse(message)
    return SMSContext(
        db=cast(Session, object()),
        phone_number=user.phone_e164 or "+17145550123",
        user=user,
        subscription=None,
        normalized_text=parsed.normalized_text,
        raw_text=parsed.raw_text,
        tokens=parsed.tokens,
        parsed_arguments=parsed.arguments,
        timestamp=datetime.now(UTC),
    )


@pytest.fixture()
def user() -> User:
    """Return a user with all saved locations configured."""

    return User(
        id=1,
        email="driver@example.com",
        phone_e164="+17145550123",
        home_location="Corona, CA",
        work_location="Anaheim, CA",
        gym_location="Riverside, CA",
        school_location="Fullerton, CA",
        default_state="CA",
    )


@pytest.mark.parametrize(
    ("message", "mode", "field", "value", "direction"),
    [
        ("TRAFFIC CORONA", "area", "area", "CORONA", None),
        ("TRAFFIC RIVERSIDE", "area", "area", "RIVERSIDE", None),
        ("TRAFFIC LAX", "area", "area", "LAX", None),
        ("TRAFFIC I15", "area", "area", "I-15", None),
        ("TRAFFIC I-15 NORTH", "corridor", "corridor", "I-15", "NORTH"),
        ("TRAFFIC SR91 WEST", "corridor", "corridor", "SR-91", "WEST"),
        ("TRAFFIC HOME", "area", "area", "HOME", None),
        ("TRAFFIC WORK", "area", "area", "WORK", None),
        ("TRAFFIC GYM", "area", "area", "GYM", None),
        ("TRAFFIC SCHOOL", "area", "area", "SCHOOL", None),
    ],
)
def test_traffic_service_prepares_area_and_highway_commands(
    user: User,
    message: str,
    mode: str,
    field: str,
    value: str,
    direction: str | None,
) -> None:
    """Cities, highways, and named profile locations share one request path."""

    preparation = TrafficService().prepare_request(_context(message, user))

    assert preparation.error_message is None
    assert preparation.request is not None
    assert preparation.request.mode == mode
    assert getattr(preparation.request, field) == value
    assert preparation.request.direction == direction


@pytest.mark.parametrize(
    ("message", "origin", "destination"),
    [
        ("TRAFFIC HOME TO WORK", "HOME", "WORK"),
        ("TRAFFIC CORONA TO LAX", "CORONA", "LAX"),
        ("TRAFFIC HOME TO LAX", "HOME", "LAX"),
    ],
)
def test_traffic_service_prepares_routes(
    user: User,
    message: str,
    origin: str,
    destination: str,
) -> None:
    """Route endpoints are preserved for the existing route engine to resolve."""

    preparation = TrafficService().prepare_request(_context(message, user))

    assert preparation.error_message is None
    assert preparation.request is not None
    assert preparation.request.mode == "route"
    assert preparation.request.origin == origin
    assert preparation.request.destination == destination


def test_traffic_service_prepares_saved_commute(user: User) -> None:
    """The original TRAFFIC commute command retains saved home/work behavior."""

    preparation = TrafficService().prepare_request(_context("TRAFFIC", user))

    assert preparation.error_message is None
    assert preparation.request is not None
    assert preparation.request.mode == "commute"
    assert preparation.request.origin == "Corona, CA"
    assert preparation.request.destination == "Anaheim, CA"


def test_traffic_service_rejects_missing_saved_route_location(user: User) -> None:
    """Saved-location failures are returned before SMS quota is consumed."""

    user.work_location = None
    preparation = TrafficService().prepare_request(_context("TRAFFIC HOME TO WORK", user))

    assert preparation.request is None
    assert preparation.error_message == (
        "Please configure your Work location before using TRAFFIC WORK."
    )


def test_traffic_service_bridges_to_existing_engine(user: User, monkeypatch) -> None:
    """TrafficService delegates responses to the established traffic engine."""

    context = _context("TRAFFIC CORONA", user)
    preparation = TrafficService().prepare_request(context)
    assert preparation.request is not None

    async def fake_build_traffic_reply(**kwargs: object) -> str:
        request = kwargs["request"]
        assert getattr(request, "area") == "CORONA"
        assert kwargs["user"] is user
        return "Corona traffic is clear."

    monkeypatch.setattr(
        "app.services.traffic_service.build_traffic_reply",
        fake_build_traffic_reply,
    )

    result = asyncio.run(
        TrafficService().build_reply(context, preparation.request)
    )

    assert result.message == "Corona traffic is clear."
    assert result.metadata == {"traffic_mode": "area"}


@pytest.mark.parametrize(
    ("command", "expected_source", "expected_candidate"),
    [
        ("HOME", "home", "Corona, CA"),
        ("WORK", "work", "Anaheim, CA"),
        ("GYM", "gym", "Riverside, CA"),
        ("SCHOOL", "school", "Fullerton, CA"),
    ],
)
def test_location_resolver_handles_all_saved_locations(
    user: User,
    command: str,
    expected_source: str,
    expected_candidate: str,
    monkeypatch,
) -> None:
    """Saved locations are resolved through the existing geocoding boundary."""

    async def fake_geocode(candidate: str) -> dict[str, object]:
        assert candidate == expected_candidate
        return {
            "formatted_address": candidate,
            "latitude": 33.0,
            "longitude": -117.0,
            "place_id": "place_test",
        }

    monkeypatch.setattr(
        "app.services.location_resolver.google_maps.geocode",
        fake_geocode,
    )

    location = asyncio.run(
        LocationResolver().resolve_location(
            db=cast(Session, object()),
            user=user,
            query=command,
        )
    )

    assert location.source == expected_source
    assert location.formatted_address == expected_candidate
