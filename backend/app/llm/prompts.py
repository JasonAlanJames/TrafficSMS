"""External prompt-template loading for traffic summarization."""

from __future__ import annotations

import json
from pathlib import Path

from app.models.traffic_summary_request import TrafficSummaryRequest


_PROMPT_DIRECTORY = Path(__file__).with_name("prompts")


class TrafficPromptRenderer:
    """Render external prompt files with the approved summary-request payload."""

    def render(
        self,
        template_name: str,
        request: TrafficSummaryRequest,
    ) -> str:
        """Render a named prompt without exposing application implementation data."""

        template_path = _PROMPT_DIRECTORY / template_name
        template = template_path.read_text(encoding="utf-8")
        return template.replace(
            "{{traffic_data}}",
            json.dumps(request.as_prompt_payload(), sort_keys=True),
        )
