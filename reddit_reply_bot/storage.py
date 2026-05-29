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


def match_audit_path(replied_items_path: Path) -> Path:
    """Return the matched-item audit file path colocated with replied_items.json."""
    return replied_items_path.with_name("match_audit.json")


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
        json.dump(records, file, indent=2)
        file.write("\n")


def add_reply_record(path: Path, record: dict[str, object]) -> list[dict[str, object]]:
    """Append one reply audit record and return all records."""
    records = load_reply_records(path)
    records.append(record)
    save_reply_records(path, records)
    return records


def add_match_record(path: Path, record: dict[str, object]) -> list[dict[str, object]]:
    """Upsert one matched-item audit record by item_id and return all records."""
    item_id = record.get("item_id")
    if item_id is None:
        return add_reply_record(path, record)

    records = load_reply_records(path)
    for index, existing_record in enumerate(records):
        if existing_record.get("item_id") == item_id:
            records[index] = merge_match_record(existing_record, record)
            save_reply_records(path, records)
            return records

    records.append(record)
    save_reply_records(path, records)
    return records


def merge_match_record(
    existing_record: dict[str, object],
    new_record: dict[str, object],
) -> dict[str, object]:
    """Merge an updated match record without losing posted-reply metadata."""
    merged = dict(new_record)
    if "bot_reply_id" in new_record:
        return merged

    reply_fields = [
        "bot_reply_id",
        "bot_reply_text",
        "reply_status",
        "last_score",
        "deleted_score",
        "deleted_at",
    ]
    for field in reply_fields:
        if field in existing_record:
            merged[field] = existing_record[field]

    if existing_record.get("result") == "posted" and existing_record.get("bot_reply_id"):
        merged["result"] = "posted"

    return merged


def dedupe_match_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Return match records with only the latest record for each item_id."""
    seen_item_ids: set[object] = set()
    deduped_reversed: list[dict[str, object]] = []

    for record in reversed(records):
        item_id = record.get("item_id")
        if item_id is None:
            deduped_reversed.append(record)
            continue

        if item_id in seen_item_ids:
            continue

        seen_item_ids.add(item_id)
        deduped_reversed.append(record)

    return list(reversed(deduped_reversed))


def clean_match_record(record: dict[str, object]) -> dict[str, object]:
    """Return a match audit record with legacy fields removed and readable key order."""
    cleaned = dict(record)
    cleaned.pop("match_current_context", None)
    cleaned.pop("match_parent_context", None)

    key_order = [
        "created_at",
        "item_id",
        "kind",
        "subreddit",
        "username",
        "permalink",
        "result",
        "match_reason",
        "match_mention",
        "match_signals",
        "text",
        "parent_context",
        "bot_reply_text",
        "bot_reply_id",
        "reply_status",
        "last_score",
        "deleted_score",
        "deleted_at",
    ]
    ordered = {key: cleaned[key] for key in key_order if key in cleaned}
    ordered.update({key: value for key, value in cleaned.items() if key not in ordered})
    return ordered


def merge_reply_record_into_match_records(
    records: list[dict[str, object]],
    reply_record: dict[str, object],
) -> list[dict[str, object]]:
    """Merge one legacy reply audit record into matching match-audit records."""
    parent_item_id = reply_record.get("parent_item_id")
    if parent_item_id is None:
        return records

    merged = False
    for record in records:
        if record.get("item_id") != parent_item_id:
            continue

        _copy_reply_fields(record, reply_record)
        merged = True
        break

    if not merged:
        record = {
            "created_at": reply_record.get("created_at", ""),
            "item_id": parent_item_id,
            "kind": reply_record.get("parent_kind", ""),
            "subreddit": reply_record.get("parent_subreddit", ""),
            "username": reply_record.get("parent_username", ""),
            "permalink": reply_record.get("parent_permalink", ""),
            "result": "posted",
            "match_reason": "legacy_reply_audit",
            "match_signals": [],
            "text": reply_record.get("parent_text", ""),
            "parent_context": "",
        }
        _copy_reply_fields(record, reply_record)
        records.append(record)

    return records


def merge_reply_records_into_match_file(
    match_path: Path,
    reply_path: Path,
) -> tuple[int, int, int]:
    """Merge legacy reply audit records into match_audit.json."""
    match_records = load_reply_records(match_path)
    reply_records = load_reply_records(reply_path)
    before_count = len(match_records)

    for reply_record in reply_records:
        merge_reply_record_into_match_records(match_records, reply_record)

    deduped = [clean_match_record(record) for record in dedupe_match_records(match_records)]
    save_reply_records(match_path, deduped)
    return before_count, len(reply_records), len(deduped)


def dedupe_match_records_file(path: Path) -> tuple[int, int]:
    """Dedupe a match audit file by item_id and return before/after counts."""
    records = load_reply_records(path)
    deduped = [clean_match_record(record) for record in dedupe_match_records(records)]
    save_reply_records(path, deduped)
    return len(records), len(deduped)


def _copy_reply_fields(
    record: dict[str, object],
    reply_record: dict[str, object],
) -> None:
    record["result"] = "posted"
    record["bot_reply_id"] = reply_record.get("bot_reply_id", "")
    record["bot_reply_text"] = reply_record.get("bot_reply_text", "")
    record["reply_status"] = reply_record.get("reply_status", reply_record.get("status", ""))

    for key in ["last_score", "deleted_score", "deleted_at"]:
        if key in reply_record:
            record[key] = reply_record[key]
