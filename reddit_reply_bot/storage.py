"""Local storage helpers for replied Reddit item IDs and reply audit records."""

from __future__ import annotations

import json
from pathlib import Path


def load_replied_ids(path: Path) -> set[str]:
    """Load replied item IDs from a JSON file."""
    if not path.exists():
        return set()

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list")

    return {str(item_id) for item_id in data}


def save_replied_ids(path: Path, replied_ids: set[str]) -> None:
    """Persist replied item IDs as a sorted JSON list."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(sorted(replied_ids), file, indent=2)
        file.write("\n")


def mark_replied(path: Path, item_id: str) -> set[str]:
    """Add one item ID to the replied store and return the updated set."""
    replied_ids = load_replied_ids(path)
    replied_ids.add(item_id)
    save_replied_ids(path, replied_ids)
    return replied_ids


def reply_audit_path(replied_items_path: Path) -> Path:
    """Return the audit file path colocated with replied_items.json."""
    return replied_items_path.with_name("reply_audit.json")


def load_reply_records(path: Path) -> list[dict[str, object]]:
    """Load reply audit records from a JSON file."""
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list")

    records: list[dict[str, object]] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"{path} must contain only JSON objects")
        records.append(item)

    return records


def save_reply_records(path: Path, records: list[dict[str, object]]) -> None:
    """Persist reply audit records."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(records, file, indent=2, sort_keys=True)
        file.write("\n")


def add_reply_record(path: Path, record: dict[str, object]) -> list[dict[str, object]]:
    """Append one reply audit record and return all records."""
    records = load_reply_records(path)
    records.append(record)
    save_reply_records(path, records)
    return records
