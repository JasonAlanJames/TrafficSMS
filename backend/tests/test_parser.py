"""Unit tests for SMS normalization."""

import pytest

from app.sms.parser import SMSParser


@pytest.mark.parametrize(
    ("raw_text", "normalized_text", "tokens", "arguments"),
    [
        ("traffic", "TRAFFIC", ("TRAFFIC",), ()),
        (" Traffic ", "TRAFFIC", ("TRAFFIC",), ()),
        ("traffic     home", "TRAFFIC HOME", ("TRAFFIC", "HOME"), ("HOME",)),
        ("traffic\thome\n", "TRAFFIC HOME", ("TRAFFIC", "HOME"), ("HOME",)),
        ("!!!traffic!!!", "TRAFFIC", ("TRAFFIC",), ()),
        ("traffic i15", "TRAFFIC I-15", ("TRAFFIC", "I-15"), ("I-15",)),
        ("traffic i-15", "TRAFFIC I-15", ("TRAFFIC", "I-15"), ("I-15",)),
        ("traffic i 15", "TRAFFIC I-15", ("TRAFFIC", "I-15"), ("I-15",)),
        ("traffic sr91", "TRAFFIC SR-91", ("TRAFFIC", "SR-91"), ("SR-91",)),
        ("traffic sr 91", "TRAFFIC SR-91", ("TRAFFIC", "SR-91"), ("SR-91",)),
        ("traffic sr-91", "TRAFFIC SR-91", ("TRAFFIC", "SR-91"), ("SR-91",)),
        (
            "traffic Corona to Anaheim!!!",
            "TRAFFIC CORONA TO ANAHEIM",
            ("TRAFFIC", "CORONA", "TO", "ANAHEIM"),
            ("CORONA", "TO", "ANAHEIM"),
        ),
        ("", "", (), ()),
        ("  ?!?  ", "", (), ()),
        ("something unexpected", "SOMETHING UNEXPECTED", ("SOMETHING", "UNEXPECTED"), ("UNEXPECTED",)),
    ],
)
def test_parser_normalizes_inbound_text(
    raw_text: str,
    normalized_text: str,
    tokens: tuple[str, ...],
    arguments: tuple[str, ...],
) -> None:
    """The parser cleans text while preserving a predictable token shape."""

    result = SMSParser().parse(raw_text)

    assert result.raw_text == raw_text
    assert result.normalized_text == normalized_text
    assert result.tokens == tokens
    assert result.arguments == arguments


def test_parser_never_raises_for_non_string_input() -> None:
    """Malformed source data must safely produce an empty parse result."""

    result = SMSParser().parse(None)

    assert result.raw_text == ""
    assert result.normalized_text == ""
    assert result.tokens == ()
