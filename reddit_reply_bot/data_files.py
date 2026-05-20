"""Load validated JSON data files used by the bot."""

from __future__ import annotations

import json
from pathlib import Path


def load_quotes(path: Path) -> list[str]:
    """Load Wise Old Man quotes from a JSON list."""
    data = _load_json_list(path)
    quotes = [_validate_string(item, path) for item in data]

    if not quotes:
        raise ValueError(f"{path} must contain at least one quote")

    return quotes


def load_blocked_users(path: Path) -> set[str]:
    """Load blocked Reddit usernames from a JSON list."""
    if not path.exists():
        return set()

    data = _load_json_list(path)
    return {_validate_string(item, path).strip().lower() for item in data}


def _load_json_list(path: Path) -> list[object]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list")

    return data


def _validate_string(value: object, path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must contain only non-empty strings")

    return value

