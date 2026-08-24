"""Tests for the isolated Bedrock traffic-summary provider."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.llm.prompts import TrafficPromptRenderer
from app.llm.providers.bedrock_provider import BedrockProvider
from app.llm.providers.provider import TrafficSummaryProviderError
from app.models.traffic_summary_request import TrafficSummaryRequest


def _settings(**overrides: object) -> SimpleNamespace:
    values = {
        "bedrock_enabled": True,
        "bedrock_model_id": "test-model",
        "bedrock_region": "us-east-1",
        "bedrock_timeout_seconds": 1,
        "bedrock_retry_count": 1,
        "bedrock_max_tokens": 160,
        "bedrock_temperature": 0.0,
        "bedrock_top_p": 0.9,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _request() -> TrafficSummaryRequest:
    return TrafficSummaryRequest(
        location="Corona -> Anaheim",
        travel_time=42,
        normal_travel_time=30,
        delay_minutes=12,
        congestion_level="HIGH",
        severity="HIGH",
        incidents=(),
        alternate_routes=(),
        confidence=1.0,
        provenance=(),
        report_age=None,
        generated_timestamp=datetime(2026, 8, 23, tzinfo=UTC),
    )


def test_prompt_templates_are_externalized_and_include_guardrails() -> None:
    """Every externally stored prompt explicitly prohibits fabrication."""

    renderer = TrafficPromptRenderer()
    for template in ("traffic_summary.txt", "incident_summary.txt", "route_summary.txt"):
        prompt = renderer.render(template, _request())
        assert "Never invent traffic information" in prompt
        assert "Never estimate, infer, or fabricate missing information" in prompt
        assert "Corona -> Anaheim" in prompt
        assert "{{traffic_data}}" not in prompt


def test_bedrock_provider_sends_only_a_rendered_summary_request() -> None:
    """The Bedrock client receives prompt text and never an application object."""

    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def converse(self, **kwargs: object) -> dict[str, object]:
            self.calls.append(kwargs)
            return {"output": {"message": {"content": [{"text": "42 min, 12 min delay."}]}}}

    client = FakeClient()
    summary = asyncio.run(
        BedrockProvider(settings=_settings(), client=client).summarize(_request())
    )

    assert summary == "42 min, 12 min delay."
    call = client.calls[0]
    assert call["modelId"] == "test-model"
    assert "Corona -> Anaheim" in call["messages"][0]["content"][0]["text"]
    assert "TrafficSummaryRequest(" not in call["messages"][0]["content"][0]["text"]


def test_bedrock_provider_never_creates_a_client_when_disabled() -> None:
    """Opt-out prevents any AWS client creation or provider request."""

    called = False

    def client_factory():
        nonlocal called
        called = True
        raise AssertionError("disabled provider must not create a client")

    provider = BedrockProvider(
        settings=_settings(bedrock_enabled=False), client_factory=client_factory,
    )
    with pytest.raises(TrafficSummaryProviderError):
        asyncio.run(provider.summarize(_request()))
    assert called is False


def test_bedrock_provider_rejects_malformed_responses() -> None:
    """Malformed provider payloads become safe fallback conditions."""

    class MalformedClient:
        def converse(self, **_kwargs: object) -> dict[str, object]:
            return {"output": {}}

    with pytest.raises(TrafficSummaryProviderError):
        asyncio.run(BedrockProvider(
            settings=_settings(bedrock_retry_count=0), client=MalformedClient(),
        ).summarize(_request()))


def test_bedrock_provider_retries_transient_failures() -> None:
    """A transient client failure is retried within the configured retry budget."""

    class FlakyClient:
        def __init__(self) -> None:
            self.calls = 0

        def converse(self, **_kwargs: object) -> dict[str, object]:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary")
            return {"output": {"message": {"content": [{"text": "Recovered."}]}}}

    client = FlakyClient()
    assert asyncio.run(
        BedrockProvider(settings=_settings(), client=client).summarize(_request())
    ) == "Recovered."
    assert client.calls == 2


def test_bedrock_provider_times_out_and_reports_a_provider_error() -> None:
    """A timed-out Bedrock call cannot block deterministic traffic delivery."""

    class SlowClient:
        def converse(self, **_kwargs: object) -> dict[str, object]:
            time.sleep(0.05)
            return {"output": {"message": {"content": [{"text": "Late."}]}}}

    provider = BedrockProvider(
        settings=_settings(bedrock_timeout_seconds=0.01, bedrock_retry_count=0),
        client=SlowClient(),
    )
    with pytest.raises(TrafficSummaryProviderError):
        asyncio.run(provider.summarize(_request()))
