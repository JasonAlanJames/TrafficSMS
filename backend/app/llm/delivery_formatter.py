"""Single-message SMS/MMS delivery decisions for traffic summaries."""

from __future__ import annotations

import re
import logging

from app.core.config import Settings, get_settings
from app.models.delivery_decision import DeliveryDecision
from app.models.traffic_report import TrafficReport

logger = logging.getLogger(__name__)


_WHITESPACE_RE = re.compile(r"\s+")
_REDUNDANT_PREFIX_RE = re.compile(r"^TrafficSMS\s*", re.IGNORECASE)


class DeliveryFormatter:
    """Compress a response when safe, otherwise select a single MMS payload."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def prepare(self, message: str, report: TrafficReport | None = None) -> DeliveryDecision:
        """Return one final payload and its internal transport decision."""

        original = self._clean(message)
        sms_limit = self._settings.sms_character_threshold
        mms_limit = self._settings.mms_character_threshold
        if len(original) <= sms_limit:
            return self._decision(original, "SMS", False, False, "Fits in one SMS.", original, report)

        compressed = self._compress(original)
        if (
            len(original) <= self._settings.delivery_compression_threshold
            and len(compressed) <= sms_limit
        ):
            return self._decision(
                compressed,
                "SMS",
                True,
                False,
                "Compressed without removing traffic facts.",
                original, report,
            )

        if len(compressed) <= mms_limit:
            return self._decision(
                compressed,
                "MMS",
                compressed != original,
                False,
                "Requires one MMS to preserve useful traffic information.",
                original, report,
            )

        truncated = f"{compressed[: max(mms_limit - 3, 0)].rstrip()}..."
        return self._decision(
            truncated,
            "MMS",
            truncated != original,
            True,
            "Exceeded the configured one-MMS limit after compression.",
            original, report,
        )

    @staticmethod
    def _clean(message: str) -> str:
        return _WHITESPACE_RE.sub(" ", message.replace("\r", " ").replace("\n", " ")).strip()

    @staticmethod
    def _compress(message: str) -> str:
        compressed = _REDUNDANT_PREFIX_RE.sub("", message)
        replacements = {
            " minutes": " min",
            " minute": " min",
            "approximately": "about",
            "Traffic: ": "",
            "Updated moments ago.": "Updated now.",
        }
        for original, replacement in replacements.items():
            compressed = compressed.replace(original, replacement)
        return _WHITESPACE_RE.sub(" ", compressed).strip()

    @staticmethod
    def _decision(
        message: str,
        delivery_type: str,
        compression_applied: bool,
        truncation_applied: bool,
        reason: str,
        original: str,
        report: TrafficReport | None,
    ) -> DeliveryDecision:
        original_length = max(len(original), 1)
        metadata = report.summary_metadata if report else None
        decision = DeliveryDecision(
            message=message,
            delivery_type=delivery_type,  # type: ignore[arg-type]
            estimated_segments=1,
            character_count=len(message),
            compression_applied=compression_applied,
            compression_ratio=round(len(message) / original_length, 2),
            truncation_applied=truncation_applied,
            reason=reason,
            formatter_version=metadata.formatter_version if metadata else "4.1",
            llm_used=metadata.summary_used if metadata else False,
            provider=metadata.provider if metadata else "",
            model=metadata.model if metadata else "",
            latency_ms=metadata.generation_latency_ms if metadata else 0,
            fallback_reason=metadata.fallback_reason if metadata else "",
            summary_source=metadata.summary_source if metadata else "deterministic",
            response_time_ms=metadata.generation_latency_ms if metadata else 0,
            summary_version=metadata.summary_version if metadata else "4.1",
            grounding_verified=metadata.grounding_verified if metadata else True,
            hallucination_check_passed=metadata.hallucination_check_passed if metadata else True,
            bedrock_attempted=bool(metadata and metadata.provider == "Bedrock"),
            bedrock_succeeded=bool(metadata and metadata.summary_used),
            bedrock_failure_reason=metadata.fallback_reason if metadata else "",
            original_character_count=len(original),
            compressed_character_count=len(message),
        )
        logger.info("Traffic delivery telemetry", extra={
            "delivery_type": decision.delivery_type,
            "estimated_segments": decision.estimated_segments,
            "latency_ms": decision.latency_ms,
            "compression_ratio": decision.compression_ratio,
            "fallback_reason": decision.fallback_reason,
            "total_tokens": decision.total_tokens,
        })
        return decision
