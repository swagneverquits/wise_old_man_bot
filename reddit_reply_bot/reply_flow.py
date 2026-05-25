"""Reply decision helpers."""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from reddit_reply_bot.quotes import choose_quote
from reddit_reply_bot.storage import load_replied_ids, mark_replied

ReplyFunction = Callable[[str], Any]


def should_reply(
    item_id: str,
    username: str | None,
    replied_ids: set[str],
    blocked_users: set[str],
    bot_username: str | None = None,
) -> bool:
    """Return whether the bot should reply to a matched Reddit item."""
    return skip_reason(item_id, username, replied_ids, blocked_users, bot_username) is None


def skip_reason(
    item_id: str,
    username: str | None,
    replied_ids: set[str],
    blocked_users: set[str],
    bot_username: str | None = None,
) -> str | None:
    """Return the reason a matched item should be skipped, or None if allowed."""
    normalized_username = normalize_username(username)
    normalized_blocked_users = {normalize_username(user) for user in blocked_users}
    normalized_bot_username = normalize_username(bot_username)

    if item_id in replied_ids:
        return "already_replied"

    if normalized_username in normalized_blocked_users:
        return "blocked_user"

    if normalized_bot_username and normalized_username == normalized_bot_username:
        return "self_reply"

    return None


def normalize_username(username: str | None) -> str:
    """Normalize Reddit usernames for comparisons."""
    if not username:
        return "[deleted]"

    return username.strip().lower()


def reply_to_matched_item(
    item_id: str,
    username: str | None,
    quotes: Sequence[str],
    replied_store_path: Path,
    blocked_users: set[str],
    reply: ReplyFunction,
    bot_username: str | None = None,
    chooser: random.Random | None = None,
) -> bool:
    """Reply to a matched item and persist its ID after a successful reply."""
    replied_ids = load_replied_ids(replied_store_path)

    if not should_reply(item_id, username, replied_ids, blocked_users, bot_username):
        return False

    reply(choose_quote(quotes, username, chooser))
    mark_replied(replied_store_path, item_id)
    return True
