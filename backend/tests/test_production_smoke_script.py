from pathlib import Path

import pytest


def test_production_smoke_script_declares_required_safe_endpoint_checks() -> None:
    script_path = Path(__file__).parents[2] / "scripts" / "smoke_test_production.ps1"
    if not script_path.exists():
        pytest.skip("Repository-root scripts are not mounted in the backend container.")
    script = script_path.read_text(encoding="utf-8")
    for value in ("FrontendUrl", "BackendUrl", "/privacy-policy", "/terms", "/support", "/sms-disclosure", "/sms-opt-in", "/health", "/live", "/ready", "exit 1"):
        assert value in script
    for forbidden in ("stripe", "twilio", "smtp", "google", "bedrock", "password="):
        assert forbidden not in script.lower()
