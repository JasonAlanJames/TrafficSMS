"""Optional, failure-safe Bedrock presentation for deterministic traffic reports."""

from __future__ import annotations

import logging

from app.core.config import Settings, get_settings
from app.llm.providers.bedrock_provider import BedrockProvider
from app.llm.providers.provider import TrafficSummaryProvider
from app.llm.summary_formatter import SummaryFormatter
from app.models.traffic_report import TrafficReport
from app.models.traffic_summary_request import TrafficSummaryRequest


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
        self._summary_formatter = summary_formatter or SummaryFormatter()

    async def summarize(
        self,
        report: TrafficReport,
        deterministic_summary: str,
    ) -> str:
        """Return an optional grounded summary or the deterministic fallback."""

        if not self._settings.bedrock_enabled:
            return deterministic_summary

        request = TrafficSummaryRequest.from_report(report)
        provider = self._provider or BedrockProvider(settings=self._settings)
        try:
            raw_summary = await provider.summarize(request)
            summary = self._summary_formatter.format(raw_summary, request)
            if summary is None:
                logger.warning(
                    "Bedrock traffic summary rejected by deterministic guardrails",
                    extra={"location": report.location},
                )
                return deterministic_summary
            logger.info(
                "Bedrock traffic summary accepted",
                extra={"location": report.location, "report_confidence": report.confidence},
            )
            return summary
        except Exception as exc:
            logger.warning(
                "Bedrock traffic summary unavailable; using deterministic fallback",
                extra={"error": type(exc).__name__, "location": report.location},
            )
            return deterministic_summary
