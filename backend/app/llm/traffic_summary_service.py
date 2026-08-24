"""Optional, failure-safe Bedrock presentation for deterministic traffic reports."""

from __future__ import annotations

import logging
from time import perf_counter

from app.core.config import Settings, get_settings
from app.llm.providers.bedrock_provider import BedrockProvider
from app.llm.providers.provider import TrafficSummaryProvider
from app.llm.summary_formatter import SummaryFormatter
from app.models.traffic_report import TrafficReport
from app.models.traffic_summary_request import TrafficSummaryRequest
from app.models.summary_metadata import SummaryMetadata


logger = logging.getLogger(__name__)


class TrafficSummaryService:
    """Use an optional provider without allowing it to affect traffic facts."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        provider: TrafficSummaryProvider | None = None,
        summary_formatter: SummaryFormatter | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._provider = provider
        self._summary_formatter = summary_formatter or SummaryFormatter(
            max_output_chars=getattr(self._settings, "ai_summary_max_output_chars", 320)
        )
        self._metadata = SummaryMetadata()

    @property
    def metadata(self) -> SummaryMetadata:
        return self._metadata

    async def summarize(
        self,
        report: TrafficReport,
        deterministic_summary: str,
    ) -> str:
        """Return an optional grounded summary or the deterministic fallback."""

        if not self._settings.bedrock_enabled:
            self._metadata = SummaryMetadata(summary_source="deterministic")
            return deterministic_summary

        request = TrafficSummaryRequest.from_report(
            report,
            max_input_incidents=getattr(self._settings, "ai_summary_max_input_incidents", 5),
        )
        provider = self._provider or BedrockProvider(settings=self._settings)
        model_id = getattr(self._settings, "bedrock_model_id", "")
        started_at = perf_counter()
        try:
            raw_summary = await provider.summarize(request)
            summary = self._summary_formatter.format(raw_summary, request)
            if summary is None:
                self._metadata = SummaryMetadata(
                    summary_attempted=True,
                    provider="Bedrock",
                    model=model_id,
                    fallback_used=True,
                    fallback_reason="grounding_validation_failed",
                    grounding_verified=False,
                    hallucination_check_passed=False,
                    generation_latency_ms=int((perf_counter() - started_at) * 1000),
                )
                logger.warning(
                    "Bedrock traffic summary rejected by deterministic guardrails",
                )
                return deterministic_summary
            self._metadata = SummaryMetadata(
                summary_attempted=True,
                summary_used=True,
                provider="Bedrock",
                model=model_id,
                grounding_verified=True,
                hallucination_check_passed=True,
                generation_latency_ms=int((perf_counter() - started_at) * 1000),
                summary_source="bedrock",
            )
            logger.info(
                "Bedrock traffic summary accepted",
                extra={"report_confidence": report.confidence},
            )
            return summary
        except Exception as exc:
            self._metadata = SummaryMetadata(
                summary_attempted=True,
                provider="Bedrock",
                model=model_id,
                fallback_used=True,
                fallback_reason=type(exc).__name__,
                grounding_verified=False,
                hallucination_check_passed=False,
                generation_latency_ms=int((perf_counter() - started_at) * 1000),
            )
            logger.warning(
                "Bedrock traffic summary unavailable; using deterministic fallback",
                extra={"error": type(exc).__name__},
            )
            return deterministic_summary
