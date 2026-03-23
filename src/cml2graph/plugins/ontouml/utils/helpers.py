"""
Shared helpers used by both the validator and the parser.

Kept here so that neither module imports private symbols from the other.
"""

from __future__ import annotations

from typing import Any


def extract_contents(data: dict) -> list[dict] | None:
    """
    Walk the JSON to find the flat list of model elements.

    Handles both ``{"contents": [...]}`` and
    ``{"model": {"contents": [...]}}`` layouts.
    """
    if "contents" in data and isinstance(data["contents"], list):
        return flatten_contents(data["contents"])
    model = data.get("model", data)
    if "contents" in model and isinstance(model["contents"], list):
        return flatten_contents(model["contents"])
    return None


def flatten_contents(items: list) -> list[dict]:
    """Recursively flatten nested ``contents`` arrays (packages)."""
    flat: list[dict] = []
    for item in items:
        if isinstance(item, dict):
            flat.append(item)
            nested = item.get("contents")
            if isinstance(nested, list):
                flat.extend(flatten_contents(nested))
    return flat


def ref_id(obj: Any) -> str | None:
    """Extract an id from a reference dict or a plain string."""
    if isinstance(obj, dict):
        return obj.get("id")
    if isinstance(obj, str):
        return obj
    return None