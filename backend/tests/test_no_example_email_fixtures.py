"""Prevent documentation domains from returning to backend test fixtures."""

from __future__ import annotations

from pathlib import Path


def test_backend_tests_do_not_use_documentation_email_domains() -> None:
    forbidden_domains = tuple("example" + suffix for suffix in (".com", ".org", ".net"))
    tests_root = Path(__file__).parent
    matches = [
        path
        for path in tests_root.rglob("*.py")
        if any(domain in path.read_text(encoding="utf-8") for domain in forbidden_domains)
    ]

    assert matches == []
