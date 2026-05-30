"""SQLite runtime storage and legacy JSON migration helpers."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

MATCH_COLUMNS = [
    "created_at",
    "item_id",
    "kind",
    "subreddit",
    "username",
    "permalink",
    "result",
    "match_reason",
    "match_mention",
    "match_signals_json",
    "text",
    "parent_context",
    "bot_reply_text",
    "bot_reply_id",
    "reply_status",
    "last_score",
    "deleted_score",
    "deleted_at",
]


def connect_state_db(path: Path) -> sqlite3.Connection:
    """Open the runtime state database and ensure its schema exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        create table if not exists replied_items (
            item_id text primary key
        )
        """
    )
    conn.execute(
        """
        create table if not exists match_audit (
            created_at text not null default '',
            item_id text primary key,
            kind text,
            subreddit text,
            username text,
            permalink text,
            result text,
            match_reason text,
            match_mention text,
            match_signals_json text not null default '[]',
            text text,
            parent_context text,
            bot_reply_text text,
            bot_reply_id text,
            reply_status text,
            last_score integer,
            deleted_score integer,
            deleted_at text
        )
        """
    )
    conn.commit()
    return conn


@contextmanager
def state_db(path: Path) -> Iterator[sqlite3.Connection]:
    """Open a transaction and close the SQLite connection afterward."""
    conn = connect_state_db(path)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def load_replied_ids(path: Path) -> set[str]:
    """Load replied item IDs from SQLite."""
    with state_db(path) as conn:
        return {str(row["item_id"]) for row in conn.execute("select item_id from replied_items")}


def save_replied_ids(path: Path, replied_ids: set[str]) -> None:
    """Replace the replied item IDs in SQLite."""
    with state_db(path) as conn:
        conn.execute("delete from replied_items")
        conn.executemany(
            "insert into replied_items (item_id) values (?)",
            [(item_id,) for item_id in sorted(replied_ids)],
        )


def mark_replied(path: Path, item_id: str) -> set[str]:
    """Add one replied item ID and return all replied IDs."""
    with state_db(path) as conn:
        conn.execute("insert or ignore into replied_items (item_id) values (?)", (item_id,))
    return load_replied_ids(path)


def match_audit_path(state_db_path: Path) -> Path:
    """Return the SQLite state path used for match audits."""
    return state_db_path


def load_match_records(path: Path) -> list[dict[str, object]]:
    """Load match audit records from SQLite."""
    with state_db(path) as conn:
        rows = conn.execute("select * from match_audit order by created_at, item_id").fetchall()
    return [_row_to_match_record(row) for row in rows]


def save_match_records(path: Path, records: list[dict[str, object]]) -> None:
    """Replace match audit records in SQLite."""
    with state_db(path) as conn:
        conn.execute("delete from match_audit")
        for record in records:
            _upsert_match_record(conn, record)


def add_match_record(path: Path, record: dict[str, object]) -> list[dict[str, object]]:
    """Upsert one match audit record by item_id and return all records."""
    item_id = record.get("item_id")
    if item_id is None:
        raise ValueError("match audit records require item_id")

    with state_db(path) as conn:
        row = conn.execute("select * from match_audit where item_id = ?", (item_id,)).fetchone()
        merged = merge_match_record(_row_to_match_record(row), record) if row else record
        _upsert_match_record(conn, merged)
    return load_match_records(path)


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


def load_reply_records(path: Path) -> list[dict[str, object]]:
    """Load legacy reply audit records from a JSON file."""
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError(f"{path} must contain a JSON list of objects")
    return data


def save_reply_records(path: Path, records: list[dict[str, object]]) -> None:
    """Persist legacy JSON audit records."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


def dedupe_match_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Return match records with only the latest record for each item_id."""
    seen_item_ids: set[object] = set()
    deduped_reversed: list[dict[str, object]] = []
    for record in reversed(records):
        item_id = record.get("item_id")
        if item_id is None or item_id not in seen_item_ids:
            deduped_reversed.append(record)
        if item_id is not None:
            seen_item_ids.add(item_id)
    return list(reversed(deduped_reversed))


def clean_match_record(record: dict[str, object]) -> dict[str, object]:
    """Return a match audit record with legacy fields removed and readable key order."""
    cleaned = dict(record)
    cleaned.pop("match_current_context", None)
    cleaned.pop("match_parent_context", None)
    key_order = [
        "created_at", "item_id", "kind", "subreddit", "username", "permalink",
        "result", "match_reason", "match_mention", "match_signals", "text",
        "parent_context", "bot_reply_text", "bot_reply_id", "reply_status",
        "last_score", "deleted_score", "deleted_at",
    ]
    ordered = {key: cleaned[key] for key in key_order if key in cleaned}
    ordered.update({key: value for key, value in cleaned.items() if key not in ordered})
    return ordered


def merge_reply_records_into_match_file(match_path: Path, reply_path: Path) -> tuple[int, int, int]:
    """Merge legacy reply audit records into match_audit.json."""
    match_records = load_reply_records(match_path)
    reply_records = load_reply_records(reply_path)
    before_count = len(match_records)
    for reply_record in reply_records:
        _merge_reply_record(match_records, reply_record)
    deduped = [clean_match_record(record) for record in dedupe_match_records(match_records)]
    save_reply_records(match_path, deduped)
    return before_count, len(reply_records), len(deduped)


def dedupe_match_records_file(path: Path) -> tuple[int, int]:
    """Dedupe a legacy JSON match audit file."""
    records = load_reply_records(path)
    deduped = [clean_match_record(record) for record in dedupe_match_records(records)]
    save_reply_records(path, deduped)
    return len(records), len(deduped)


def _upsert_match_record(conn: sqlite3.Connection, record: dict[str, object]) -> None:
    values = dict(record)
    values["match_signals_json"] = json.dumps(values.pop("match_signals", []))
    columns = [column for column in MATCH_COLUMNS if column in values]
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(f"{column} = excluded.{column}" for column in columns if column != "item_id")
    conn.execute(
        f"insert into match_audit ({', '.join(columns)}) values ({placeholders}) "
        f"on conflict(item_id) do update set {updates}",
        [values[column] for column in columns],
    )


def _row_to_match_record(row: sqlite3.Row) -> dict[str, object]:
    record = {key: row[key] for key in row.keys() if row[key] is not None}
    signals_json = record.pop("match_signals_json", "[]")
    record["match_signals"] = json.loads(str(signals_json))
    return clean_match_record(record)


def _merge_reply_record(records: list[dict[str, object]], reply_record: dict[str, object]) -> None:
    parent_item_id = reply_record.get("parent_item_id")
    if parent_item_id is None:
        return
    record = next((item for item in records if item.get("item_id") == parent_item_id), None)
    if record is None:
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
        records.append(record)
    record["result"] = "posted"
    record["bot_reply_id"] = reply_record.get("bot_reply_id", "")
    record["bot_reply_text"] = reply_record.get("bot_reply_text", "")
    record["reply_status"] = reply_record.get("reply_status", reply_record.get("status", ""))
    for key in ["last_score", "deleted_score", "deleted_at"]:
        if key in reply_record:
            record[key] = reply_record[key]
