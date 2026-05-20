"""Local storage helpers for replied Reddit item IDs."""

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

