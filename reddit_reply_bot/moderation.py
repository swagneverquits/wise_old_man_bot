"""Moderation checks for bot replies."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from reddit_reply_bot.storage import load_match_records, save_match_records


def delete_low_karma_replies(
    reddit: Any,
    reply_records_path: Path,
    karma_threshold: int,
    logger: logging.Logger,
) -> Counter[str]:
    """Delete active bot replies with score below the configured threshold."""
    records = load_match_records(reply_records_path)
    results: Counter[str] = Counter()
    changed = False

    for record in records:
        reply_status = record.get("reply_status", record.get("status"))
        if reply_status != "active":
            results["ignored"] += 1
            continue

        bot_reply_id = record.get("bot_reply_id")
        if not bot_reply_id:
            results["missing_reply_id"] += 1
            continue

        bot_comment = reddit.comment(id=str(bot_reply_id))
        score = int(getattr(bot_comment, "score", 0))
        record["last_score"] = score
        changed = True

        if score >= karma_threshold:
            results["kept"] += 1
            continue

        bot_comment.delete()
        record["reply_status"] = "deleted_low_karma"
        record["deleted_score"] = score
        record["deleted_at"] = datetime.now(UTC).isoformat()
        changed = True
        results["deleted"] += 1
        logger.info(
            "reply_deleted_low_karma bot_reply_id=%s score=%s parent_kind=%s parent_id=%s parent_subreddit=%s parent_username=%s",
            bot_reply_id,
            score,
            record.get("kind", record.get("parent_kind", "")),
            record.get("item_id", record.get("parent_item_id", "")),
            record.get("subreddit", record.get("parent_subreddit", "")),
            record.get("username", record.get("parent_username", "")),
        )

    if changed:
        save_match_records(reply_records_path, records)

    return results
