"""Small, deterministic parsers for saved-route SMS management commands."""

from __future__ import annotations


def parse_save_route(text: str) -> tuple[str, str, str] | None:
    """Parse ``SAVE ROUTE <alias> <origin> TO <destination>`` safely."""

    tokens = text.split()
    if len(tokens) < 6 or tokens[:2] != ["SAVE", "ROUTE"] or tokens.count("TO") != 1:
        return None
    separator = tokens.index("TO")
    if separator < 4 or separator == len(tokens) - 1:
        return None
    return (
        " ".join(tokens[2:separator - 1]),
        tokens[separator - 1],
        " ".join(tokens[separator + 1:]),
    )


def parse_route_alias(text: str) -> str | None:
    """Extract an alias from explicit route lookup and deletion commands."""

    tokens = text.split()
    if tokens[:1] == ["ROUTE"] and len(tokens) > 1:
        return " ".join(tokens[1:])
    if tokens[:2] == ["TRAFFIC", "ROUTE"] and len(tokens) > 2:
        return " ".join(tokens[2:])
    if tokens[:2] in (["DELETE", "ROUTE"], ["REMOVE", "ROUTE"]) and len(tokens) > 2:
        return " ".join(tokens[2:])
    return None
