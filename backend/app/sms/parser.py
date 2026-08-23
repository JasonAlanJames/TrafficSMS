"""Normalization-only parsing for inbound SMS messages."""

from __future__ import annotations

import re
import unicodedata

from app.sms.models import SMSParseResult


_DASH_RE = re.compile(r"[\u2010-\u2015\u2212]+")
_PUNCTUATION_RE = re.compile(r"[^\w\s-]+")
_HYPHEN_RE = re.compile(r"\s*-+\s*")
_HIGHWAY_RE = re.compile(r"\b(I|SR)\s*-?\s*(\d{1,3})\b")
_WHITESPACE_RE = re.compile(r"\s+")


class SMSParser:
    """Normalize inbound text without making routing or business decisions."""

    def parse(self, raw_text: object) -> SMSParseResult:
        """Return a safe, normalized parse result for any incoming value."""

        raw_value = raw_text if isinstance(raw_text, str) else ""

        try:
            normalized = unicodedata.normalize("NFKC", raw_value).upper()
            normalized = _DASH_RE.sub("-", normalized)
            normalized = _PUNCTUATION_RE.sub(" ", normalized)
            normalized = _HYPHEN_RE.sub("-", normalized)
            normalized = _HIGHWAY_RE.sub(self._format_highway, normalized)
            normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
        except (TypeError, ValueError):
            normalized = ""

        tokens = tuple(normalized.split()) if normalized else ()
        return SMSParseResult(
            raw_text=raw_value,
            normalized_text=normalized,
            tokens=tokens,
            arguments=tokens[1:],
        )

    @staticmethod
    def _format_highway(match: re.Match[str]) -> str:
        """Format interstate and state-route references consistently."""

        return f"{match.group(1)}-{match.group(2)}"
