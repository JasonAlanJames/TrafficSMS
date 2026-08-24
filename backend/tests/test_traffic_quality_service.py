"""Nationwide deterministic request-quality coverage."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import cast

import pytest
from sqlalchemy.orm import Session

from app.models.entities import User
from app.models.traffic_request import TrafficRequest
from app.services.traffic_parser import parse_traffic_command
from app.services.traffic_quality_service import TrafficQualityService
from app.services.traffic_service import TrafficService
from app.sms.context import SMSContext
from app.sms.intent_resolver import SMSIntentResolver
from app.sms.intents import SMSIntent
from app.sms.parser import SMSParser


@pytest.mark.parametrize(
    ("query", "normalized", "state"),
    [
        ("Corona CA", "CORONA, CA", "CA"), ("Phoenix Arizona", "PHOENIX, AZ", "AZ"),
        ("Las Vegas NV", "LAS VEGAS, NV", "NV"), ("Dallas TX", "DALLAS, TX", "TX"),
        ("Miami FL", "MIAMI, FL", "FL"), ("Atlanta GA", "ATLANTA, GA", "GA"),
        ("Chicago IL", "CHICAGO, IL", "IL"), ("New York NY", "NEW YORK, NY", "NY"),
        ("Seattle WA", "SEATTLE, WA", "WA"),
    ],
)
def test_nationwide_city_state_inputs_are_normalized(query: str, normalized: str, state: str) -> None:
    quality = TrafficQualityService().assess(TrafficRequest(mode="area", area=query))
    assert quality.is_supported is True
    assert quality.normalized_query == normalized
    assert quality.state_abbreviation == state


@pytest.mark.parametrize(
    ("command", "corridor", "direction"),
    [
        ("TRAFFIC I-5 N", "I-5", "N"), ("TRAFFIC I-10 E", "I-10", "E"),
        ("TRAFFIC I15 NORTH", "I-15", "N"), ("TRAFFIC I-40 W", "I-40", "W"),
        ("TRAFFIC I-95 S", "I-95", "S"), ("TRAFFIC I-405 S", "I-405", "S"),
        ("TRAFFIC US-101 N", "US-101", "N"), ("TRAFFIC Route 66 N", "US-66", "N"), ("TRAFFIC SR-91 W", "SR-91", "W"),
        ("TRAFFIC 91 WEST CA", "SR-91", "W"),
    ],
)
def test_nationwide_corridor_formats_are_canonical(command: str, corridor: str, direction: str) -> None:
    request = parse_traffic_command(command)
    quality = TrafficQualityService().assess(request)
    assert request.mode == "corridor"
    assert quality.is_supported is True
    assert quality.corridor == corridor
    assert quality.direction == direction


def test_zip_ambiguous_and_unsupported_inputs_have_safe_assessments() -> None:
    service = TrafficQualityService()
    zip_quality = service.assess(TrafficRequest(mode="area", area="92882"))
    assert zip_quality.request_type == "zip"
    assert zip_quality.zip_code == "92882"
    for value in ("91", "10", "Springfield", "Washington", "downtown"):
        quality = service.assess(TrafficRequest(mode="area", area=value))
        assert quality.is_ambiguous is True
        assert quality.requires_more_detail is True
    for value in ("Mars", "Atlantis", "London UK"):
        quality = service.assess(TrafficRequest(mode="area", area=value))
        assert quality.is_supported is False
        assert "supported U.S." in quality.user_message


def _context(command: str) -> SMSContext:
    parsed = SMSParser().parse(command)
    return SMSContext(
        db=cast(Session, object()), phone_number="+17145550123",
        user=User(id=1, email="quality@trafficsms.local", phone_e164="+17145550123"),
        subscription=None, normalized_text=parsed.normalized_text, raw_text=command,
        tokens=parsed.tokens, parsed_arguments=parsed.arguments, timestamp=datetime.now(UTC),
    )


def test_traffic_service_returns_safe_quality_fallback_before_engine_work() -> None:
    context = _context("TRAFFIC Springfield")
    assert asyncio.run(SMSIntentResolver().resolve(context)) is SMSIntent.TRAFFIC_ROUTE
    preparation = TrafficService().prepare_request(context)
    assert preparation.request is None
    assert preparation.quality is not None
    assert preparation.quality.is_ambiguous is True
    assert "little more detail" in (preparation.error_message or "")


def test_saved_route_quality_rejects_ambiguous_route_endpoints() -> None:
    quality = TrafficQualityService().assess(TrafficRequest(
        mode="route", origin="Springfield", destination="Chicago IL",
    ))
    assert quality.is_supported is False
    assert quality.is_ambiguous is True
