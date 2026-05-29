"""Maintenance commands for local bot state files."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from reddit_reply_bot.storage import (
    clean_match_record,
    dedupe_match_records_file,
    merge_reply_records_into_match_file,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Wise Old Man bot maintenance tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dedupe_parser = subparsers.add_parser(
        "dedupe-match-audit",
        help="Remove duplicate match audit records by item_id",
    )
    dedupe_parser.add_argument(
        "--path",
        type=Path,
        default=Path("data/match_audit.json"),
        help="Path to match_audit.json",
    )
    dedupe_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print counts without rewriting the file",
    )

    merge_parser = subparsers.add_parser(
        "merge-reply-audit",
        help="Merge legacy reply_audit.json records into match_audit.json",
    )
    merge_parser.add_argument(
        "--match-path",
        type=Path,
        default=Path("data/match_audit.json"),
        help="Path to match_audit.json",
    )
    merge_parser.add_argument(
        "--reply-path",
        type=Path,
        default=Path("data/reply_audit.json"),
        help="Path to legacy reply_audit.json",
    )

    export_parser = subparsers.add_parser(
        "export-sqlite",
        help="Export bot_state.sqlite tables to readable JSON files",
    )
    export_parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/bot_state.sqlite"),
        help="Path to bot_state.sqlite",
    )
    export_parser.add_argument(
        "--out",
        type=Path,
        default=Path("data"),
        help="Directory to write match_audit.json and replied_items.json",
    )

    args = parser.parse_args()
    if args.command == "dedupe-match-audit":
        dedupe_match_audit(args.path, args.dry_run)
    elif args.command == "merge-reply-audit":
        merge_reply_audit(args.match_path, args.reply_path)
    elif args.command == "export-sqlite":
        export_sqlite(args.db, args.out)


def dedupe_match_audit(path: Path, dry_run: bool = False) -> tuple[int, int]:
    """Dedupe a match audit file and print before/after counts."""
    if dry_run:
        from reddit_reply_bot.storage import dedupe_match_records, load_reply_records

        records = load_reply_records(path)
        deduped = dedupe_match_records(records)
        counts = (len(records), len(deduped))
    else:
        counts = dedupe_match_records_file(path)

    print(f"match_audit_dedupe path={path} before={counts[0]} after={counts[1]}")
    return counts


def merge_reply_audit(match_path: Path, reply_path: Path) -> tuple[int, int, int]:
    """Merge legacy reply audit records into match audit and print counts."""
    before, reply_count, after = merge_reply_records_into_match_file(match_path, reply_path)
    print(
        "reply_audit_merge "
        f"match_path={match_path} reply_path={reply_path} "
        f"match_before={before} reply_records={reply_count} match_after={after}"
    )
    return before, reply_count, after


def export_sqlite(db_path: Path, out_dir: Path) -> tuple[int, int]:
    """Export SQLite state tables to readable JSON files."""
    out_dir.mkdir(parents=True, exist_ok=True)
    match_records: list[dict[str, object]] = []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        for row in conn.execute("select * from match_audit order by created_at, item_id"):
            record = dict(row)
            signals_json = record.pop("match_signals_json", "[]")
            record["match_signals"] = json.loads(str(signals_json))
            match_records.append(clean_match_record(record))

        replied_items = [
            row["item_id"]
            for row in conn.execute("select item_id from replied_items order by item_id")
        ]
    finally:
        conn.close()

    _write_json(out_dir / "match_audit.json", match_records)
    _write_json(out_dir / "replied_items.json", replied_items)
    print(
        "sqlite_export "
        f"db={db_path} out={out_dir} "
        f"match_records={len(match_records)} replied_items={len(replied_items)}"
    )
    return len(match_records), len(replied_items)


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
