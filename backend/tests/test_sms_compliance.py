"""Production compliance coverage for inbound STOP, HELP, and START messages."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy.orm import Session

from app.models.entities import User
from app.models.subscription import Subscription
from app.sms.context import SMSContext
from app.sms.dispatcher import SMSDispatcher
from app.sms.intent_resolver import SMSIntentResolver
from app.sms.intents import SMSIntent
from app.sms.models import SMSResponse
from app.sms.parser import SMSParser


def _context(text: str) -> SMSContext:
    parsed = SMSParser().parse(text)
    return SMSContext(
        db=cast(Session, object()),
        phone_number="+17145550123",
        user=None,
        subscription=None,
        normalized_text=parsed.normalized_text,
        raw_text=parsed.raw_text,
        tokens=parsed.tokens,
        parsed_arguments=parsed.arguments,
        timestamp=datetime.now(UTC),
    )


@pytest.mark.parametrize(
    ("message", "expected_intent"),
    [
        ("STOP", SMSIntent.STOP),
        ("stopall", SMSIntent.STOP),
        ("unsubscribe", SMSIntent.STOP),
        ("cancel", SMSIntent.STOP),
        ("end", SMSIntent.STOP),
        ("quit", SMSIntent.STOP),
        (" ReVoKe ", SMSIntent.STOP),
        ("optout", SMSIntent.STOP),
        ("opt   out", SMSIntent.STOP),
        ("help", SMSIntent.HELP),
        ("info", SMSIntent.HELP),
        ("support", SMSIntent.HELP),
        ("start", SMSIntent.START),
        ("yes", SMSIntent.START),
        ("in", SMSIntent.START),
        ("unstop", SMSIntent.START),
        ("opt in", SMSIntent.START),
    ],
)
def test_standard_compliance_aliases_resolve_before_normal_sms_processing(
    message: str,
    expected_intent: SMSIntent,
) -> None:
    context = _context(message)

    intent = asyncio.run(SMSIntentResolver().resolve(context))

    assert intent is expected_intent
    assert context.metadata["intent_source"] == "compliance_keyword"


def test_webhook_stop_start_persists_local_consent_and_blocks_service_sms(
    client,
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.api.twilio_webhook.get_settings",
        lambda: SimpleNamespace(
            app_env="development",
            twilio_auth_token="test-token",
            public_base_url="https://trafficsms.local",
        ),
    )
    user = User(
        email="compliance@test.trafficsms.com",
        phone_e164="+17145550123",
        sms_consent_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    db_session.add(user)
    db_session.commit()
    db_session.add(
        Subscription(user_id=user.id, plan="standard", status="active", sms_allowance=60)
    )
    db_session.commit()

    stop_response = client.post(
        "/webhooks/twilio/inbound",
        data={"From": user.phone_e164, "Body": "unsubscribe"},
    )
    assert stop_response.status_code == 200
    assert "unsubscribed" in stop_response.text
    db_session.refresh(user)
    assert user.sms_opted_out_at is not None
    assert user.sms_opt_out_type == "keyword"

    repeated_stop_response = client.post(
        "/webhooks/twilio/inbound",
        data={"From": user.phone_e164, "Body": "STOP"},
    )
    assert repeated_stop_response.status_code == 200

    help_response = client.post(
        "/webhooks/twilio/inbound",
        data={"From": user.phone_e164, "Body": "SUPPORT"},
    )
    assert help_response.status_code == 200
    assert "https://trafficsms.com/support" in help_response.text
    assert "Reply STOP" in help_response.text
    db_session.refresh(user)
    assert user.sms_last_help_at is not None

    blocked_response = client.post(
        "/webhooks/twilio/inbound",
        data={"From": user.phone_e164, "Body": "TRAFFIC CORONA"},
    )
    assert blocked_response.status_code == 200
    assert "currently opted out" in blocked_response.text

    start_response = client.post(
        "/webhooks/twilio/inbound",
        data={"From": user.phone_e164, "Body": "UNSTOP"},
    )
    assert start_response.status_code == 200
    assert "Text TRAFFIC" in start_response.text
    db_session.refresh(user)
    assert user.sms_opted_out_at is None
    assert user.sms_opt_out_type is None
    assert user.sms_resumed_at is not None
    assert user.sms_consent_at is not None
    assert user.sms_consent_at.replace(tzinfo=UTC) == datetime(2026, 8, 1, tzinfo=UTC)

    repeated_start_response = client.post(
        "/webhooks/twilio/inbound",
        data={"From": user.phone_e164, "Body": "START"},
    )
    assert repeated_start_response.status_code == 200


@pytest.mark.parametrize(
    "intent",
    [
        SMSIntent.TRAFFIC,
        SMSIntent.TRAFFIC_ROUTE,
        SMSIntent.SAVE_ROUTE,
        SMSIntent.LIST_ROUTES,
        SMSIntent.DELETE_ROUTE,
        SMSIntent.POLICE_REPORT,
        SMSIntent.POLICE_VOTE,
        SMSIntent.SUBSCRIBE,
    ],
)
def test_dispatcher_does_not_invoke_service_handlers_for_locally_opted_out_user(
    intent: SMSIntent,
) -> None:
    user = User(
        email="blocked@test.trafficsms.com",
        phone_e164="+17145550123",
        sms_opted_out_at=datetime.now(UTC),
    )
    context = _context("TRAFFIC CORONA")
    context.user = user
    called = False

    async def traffic_handler(_: SMSContext) -> SMSResponse:
        nonlocal called
        called = True
        return SMSResponse(True, SMSIntent.TRAFFIC, "traffic")

    dispatcher = SMSDispatcher(
        handlers={intent: traffic_handler for intent in SMSIntent}
    )
    response = asyncio.run(dispatcher.dispatch(intent, context))

    assert called is False
    assert response.success is False
    assert "Reply START" in response.message


@pytest.mark.parametrize("intent", [SMSIntent.STOP, SMSIntent.HELP, SMSIntent.START])
def test_dispatcher_allows_compliance_handlers_for_locally_opted_out_user(
    intent: SMSIntent,
) -> None:
    context = _context("STOP")
    context.user = User(
        email="allowed@test.trafficsms.com",
        phone_e164="+17145550123",
        sms_opted_out_at=datetime.now(UTC),
    )
    called = False

    async def handler(_: SMSContext) -> SMSResponse:
        nonlocal called
        called = True
        return SMSResponse(True, intent, "compliance")

    dispatcher = SMSDispatcher(handlers={candidate: handler for candidate in SMSIntent})
    response = asyncio.run(dispatcher.dispatch(intent, context))

    assert called is True
    assert response.success is True


@pytest.mark.parametrize(
    ("opt_out_type", "expected_text", "should_opt_out"),
    [
        ("STOP", "unsubscribed", True),
        ("HELP", "TrafficSMS help", False),
        ("START", "activate service", False),
    ],
)
def test_twilio_opt_out_type_is_signed_and_processed_before_body(
    client,
    db_session,
    monkeypatch,
    opt_out_type: str,
    expected_text: str,
    should_opt_out: bool,
) -> None:
    user = User(email="twilio@test.trafficsms.com", phone_e164="+17145550124")
    db_session.add(user)
    db_session.commit()

    monkeypatch.setattr(
        "app.api.twilio_webhook.get_settings",
        lambda: SimpleNamespace(
            app_env="production",
            twilio_auth_token="test-token",
            public_base_url="https://trafficsms.com",
        ),
    )

    class ValidatingRequestValidator:
        def __init__(self, token: str) -> None:
            assert token == "test-token"

        def validate(self, url: str, form: dict[str, str], signature: str) -> bool:
            assert url == "https://trafficsms.com/webhooks/twilio/inbound"
            assert form["OptOutType"] == opt_out_type
            assert signature == "valid-signature"
            return True

    monkeypatch.setattr(
        "app.api.twilio_webhook.RequestValidator", ValidatingRequestValidator
    )
    from app.api.twilio_webhook import build_sms_context as build_context

    captured_metadata: dict[str, str] = {}

    def capture_context(**kwargs):
        captured_metadata.update(kwargs["metadata"])
        return build_context(**kwargs)

    monkeypatch.setattr("app.api.twilio_webhook.build_sms_context", capture_context)

    response = client.post(
        "/webhooks/twilio/inbound",
        data={
            "From": user.phone_e164,
            "Body": "TRAFFIC CORONA",
            "OptOutType": opt_out_type,
            "MessageSid": "SM123",
            "AccountSid": "AC123",
            "To": "+18005550123",
        },
        headers={"X-Twilio-Signature": "valid-signature"},
    )

    assert response.status_code == 200
    assert expected_text in response.text
    assert captured_metadata == {
        "twilio_opt_out_type": opt_out_type,
        "twilio_message_sid": "SM123",
        "twilio_account_sid": "AC123",
        "twilio_to": "+18005550123",
        "twilio_from": user.phone_e164,
        "twilio_body": "TRAFFIC CORONA",
    }
    db_session.refresh(user)
    assert (user.sms_opted_out_at is not None) is should_opt_out
    if opt_out_type == "HELP":
        assert user.sms_last_help_at is not None
    if opt_out_type == "START":
        assert user.sms_resumed_at is not None


@pytest.mark.parametrize("command", ["STOP", "HELP", "START"])
def test_compliance_webhooks_bypass_subscription_and_usage(
    client,
    monkeypatch,
    command: str,
) -> None:
    monkeypatch.setattr(
        "app.api.twilio_webhook.get_settings",
        lambda: SimpleNamespace(
            app_env="development",
            twilio_auth_token="test-token",
            public_base_url="https://trafficsms.local",
        ),
    )

    class BillingMustNotRun:
        def __init__(self, *_: object) -> None:
            raise AssertionError("Compliance commands must not initialize billing")

    monkeypatch.setattr("app.sms.handlers.traffic.BillingService", BillingMustNotRun)
    response = client.post(
        "/webhooks/twilio/inbound",
        data={"From": "+17145550127", "Body": command},
    )

    assert response.status_code == 200


def test_unknown_or_inactive_start_uses_the_existing_registration_url(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.twilio_webhook.get_settings",
        lambda: SimpleNamespace(
            app_env="development",
            twilio_auth_token="test-token",
            public_base_url="https://trafficsms.local",
        ),
    )

    response = client.post(
        "/webhooks/twilio/inbound",
        data={"From": "+17145550128", "Body": "START"},
    )

    assert response.status_code == 200
    assert "https://trafficsms.com/sms-opt-in" in response.text


def test_production_webhook_rejects_invalid_twilio_signature(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.twilio_webhook.get_settings",
        lambda: SimpleNamespace(
            app_env="production",
            twilio_auth_token="test-token",
            public_base_url="https://trafficsms.com",
        ),
    )
    monkeypatch.setattr(
        "app.api.twilio_webhook.RequestValidator",
        lambda _: SimpleNamespace(validate=lambda *_: False),
    )

    response = client.post(
        "/webhooks/twilio/inbound",
        data={"From": "+17145550125", "Body": "HELP"},
        headers={"X-Twilio-Signature": "invalid-signature"},
    )

    assert response.status_code == 403
