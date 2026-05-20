"""Bot item processing."""

from __future__ import annotations

import logging
import random
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from reddit_reply_bot.matcher import comment_matches, submission_matches
from reddit_reply_bot.quotes import choose_quote
from reddit_reply_bot.reply_flow import ReplyFunction, should_reply
from reddit_reply_bot.runtime import Cooldown, extract_item_metadata, log_reply_event
from reddit_reply_bot.storage import load_replied_ids, mark_replied

TextExtractor = Callable[[Any], str | None]


def process_comment(
    comment: Any,
    quotes: Sequence[str],
    replied_store_path: Path,
    blocked_users: set[str],
    bot_username: str,
    reply: ReplyFunction,
    dry_run: bool,
    logger: logging.Logger,
    cooldown: Cooldown | None = None,
    chooser: random.Random | None = None,
) -> bool:
    """Process one Reddit comment."""
    return _process_item(
        item=comment,
        kind="comment",
        text=getattr(comment, "body", None),
        is_match=comment_matches,
        quotes=quotes,
        replied_store_path=replied_store_path,
        blocked_users=blocked_users,
        bot_username=bot_username,
        reply=reply,
        dry_run=dry_run,
        logger=logger,
        cooldown=cooldown,
        chooser=chooser,
    )


def process_submission(
    submission: Any,
    quotes: Sequence[str],
    replied_store_path: Path,
    blocked_users: set[str],
    bot_username: str,
    reply: ReplyFunction,
    dry_run: bool,
    logger: logging.Logger,
    cooldown: Cooldown | None = None,
    chooser: random.Random | None = None,
) -> bool:
    """Process one Reddit submission."""
    return _process_item(
        item=submission,
        kind="submission",
        text=getattr(submission, "title", None),
        is_match=submission_matches,
        quotes=quotes,
        replied_store_path=replied_store_path,
        blocked_users=blocked_users,
        bot_username=bot_username,
        reply=reply,
        dry_run=dry_run,
        logger=logger,
        cooldown=cooldown,
        chooser=chooser,
    )


def _process_item(
    item: Any,
    kind: str,
    text: str | None,
    is_match: Callable[[str | None], bool],
    quotes: Sequence[str],
    replied_store_path: Path,
    blocked_users: set[str],
    bot_username: str,
    reply: ReplyFunction,
    dry_run: bool,
    logger: logging.Logger,
    cooldown: Cooldown | None = None,
    chooser: random.Random | None = None,
) -> bool:
    metadata = extract_item_metadata(item, kind)

    if not is_match(text):
        log_reply_event(logger, "reply_skip", metadata, "no_match")
        return False

    replied_ids = load_replied_ids(replied_store_path)
    if not should_reply(
        metadata.item_id,
        metadata.username,
        replied_ids,
        blocked_users,
        bot_username,
    ):
        log_reply_event(logger, "reply_skip", metadata, "decision_skip")
        return False

    if cooldown is not None and not cooldown.ready():
        log_reply_event(logger, "reply_skip", metadata, "cooldown")
        return False

    quote = choose_quote(quotes, metadata.username, chooser)

    if dry_run:
        logger.info(
            "dry_run_reply item_id=%s kind=%s subreddit=%s username=%s quote=%r",
            metadata.item_id,
            metadata.kind,
            metadata.subreddit,
            metadata.username,
            quote,
        )
        log_reply_event(logger, "reply_dry_run", metadata, "would_reply")
        return True

    reply(quote)
    mark_replied(replied_store_path, metadata.item_id)

    if cooldown is not None:
        cooldown.mark()

    log_reply_event(logger, "reply_posted", metadata, "posted")
    return True

