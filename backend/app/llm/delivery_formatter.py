"""Single-message SMS/MMS delivery decisions for traffic summaries."""

from __future__ import annotations

import re

from app.core.config import Settings, get_settings
from app.models.delivery_decision import DeliveryDecision


_WHITESPACE_RE = re.compile(r"\s+")
_REDUNDANT_PREFIX_RE = re.compile(r"^TrafficSMS\s*", re.IGNORECASE)


class DeliveryFormatter:
    """Compress a response when safe, otherwise select a single MMS payload."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def prepare(self, message: str) -> DeliveryDecision:
        """Return one final payload and its internal transport decision."""

        original = self._clean(message)
        sms_limit = self._settings.sms_character_threshold
        mms_limit = self._settings.mms_character_threshold
        if len(original) <= sms_limit:
            return self._decision(original, "SMS", False, False, "Fits in one SMS.", original)

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
                original,
            )

        if len(compressed) <= mms_limit:
            return self._decision(
                compressed,
                "MMS",
                compressed != original,
                False,
                "Requires one MMS to preserve useful traffic information.",
                original,
            )

        truncated = f"{compressed[: max(mms_limit - 3, 0)].rstrip()}..."
        return self._decision(
            truncated,
            "MMS",
            truncated != original,
            True,
            "Exceeded the configured one-MMS limit after compression.",
            original,
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
    ) -> DeliveryDecision:
        original_length = max(len(original), 1)
        return DeliveryDecision(
            message=message,
            delivery_type=delivery_type,  # type: ignore[arg-type]
            estimated_segments=1,
            character_count=len(message),
            compression_applied=compression_applied,
            compression_ratio=round(len(message) / original_length, 2),
            truncation_applied=truncation_applied,
            reason=reason,
        )
