"""Amazon Bedrock adapter for presentation-only traffic summaries."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from app.core.config import Settings, get_settings
from app.llm.prompts import TrafficPromptRenderer
from app.llm.providers.provider import TrafficSummaryProviderError
from app.models.traffic_summary_request import TrafficSummaryRequest


logger = logging.getLogger(__name__)


class BedrockProvider:
    """Call Bedrock with only a sanitized TrafficSummaryRequest."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        prompt_renderer: TrafficPromptRenderer | None = None,
        client: Any | None = None,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._prompt_renderer = prompt_renderer or TrafficPromptRenderer()
        self._client = client
        self._client_factory = client_factory

    async def summarize(self, request: TrafficSummaryRequest) -> str:
        """Return text only, retrying transient Bedrock failures within a timeout."""

        if not self._settings.bedrock_enabled:
            raise TrafficSummaryProviderError("Bedrock traffic summaries are disabled.")
        if not self._settings.bedrock_model_id.strip():
            raise TrafficSummaryProviderError("BEDROCK_MODEL_ID is not configured.")

        prompt = self._prompt_renderer.render("traffic_summary.txt", request)
        attempts = self._settings.bedrock_retry_count + 1
        for attempt in range(1, attempts + 1):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(self._invoke, prompt),
                    timeout=self._settings.bedrock_timeout_seconds,
                )
                return self._extract_text(response)
            except Exception as exc:
                logger.warning(
                    "Bedrock traffic summary attempt failed",
                    extra={"attempt": attempt, "attempts": attempts, "error": type(exc).__name__},
                )
                if attempt == attempts:
                    raise TrafficSummaryProviderError(
                        "Bedrock traffic summary is unavailable."
                    ) from exc
                await asyncio.sleep(0.05 * attempt)

        raise TrafficSummaryProviderError("Bedrock traffic summary is unavailable.")

    def _invoke(self, prompt: str) -> Any:
        client = self._client or self._create_client()
        return client.converse(
            modelId=self._settings.bedrock_model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={
                "maxTokens": self._settings.bedrock_max_tokens,
                "temperature": self._settings.bedrock_temperature,
                "topP": self._settings.bedrock_top_p,
            },
        )

    def _create_client(self) -> Any:
        if self._client_factory is not None:
            self._client = self._client_factory()
            return self._client

        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise TrafficSummaryProviderError(
                "boto3 is required for Bedrock traffic summaries."
            ) from exc

        self._client = boto3.client(
            "bedrock-runtime",
            region_name=self._settings.bedrock_region,
            config=Config(
                connect_timeout=self._settings.bedrock_timeout_seconds,
                read_timeout=self._settings.bedrock_timeout_seconds,
                retries={"max_attempts": 0},
            ),
        )
        return self._client

    @staticmethod
    def _extract_text(response: Any) -> str:
        try:
            content = response["output"]["message"]["content"]
            text = "".join(part.get("text", "") for part in content).strip()
        except (KeyError, TypeError) as exc:
            raise TrafficSummaryProviderError("Bedrock returned an invalid response.") from exc
        if not text:
            raise TrafficSummaryProviderError("Bedrock returned an empty response.")
        return text
