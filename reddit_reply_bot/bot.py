"""Bot item processing."""

from __future__ import annotations

import logging
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from reddit_reply_bot.matcher import comment_matches, submission_matches
from reddit_reply_bot.quotes import choose_quote
from reddit_reply_bot.reply_flow import ReplyFunction, should_reply
from reddit_reply_bot.runtime import Cooldown, extract_item_metadata, log_reply_event
from reddit_reply_bot.storage import load_replied_ids, mark_replied

TextExtractor = Callable[[Any], str | None]


@dataclass(frozen=True)
class ProcessResult:
    kind: str
    item_id: str
    result: str

    @property
    def did_reply(self) -> bool:
        return self.result in {"posted", "would_reply"}


def process_comment(
    comment: Any,
    quotes: Sequence[str],
    replied_store_path: Path,
    blocked_users: set[str],
    bot_username: str,
    allow_self_reply: bool,
    reply: ReplyFunction,
    dry_run: bool,
    logger: logging.Logger,
    cooldown: Cooldown | None = None,
    chooser: random.Random | None = None,
) -> ProcessResult:
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
        allow_self_reply=allow_self_reply,
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
    allow_self_reply: bool,
    reply: ReplyFunction,
    dry_run: bool,
    logger: logging.Logger,
    cooldown: Cooldown | None = None,
    chooser: random.Random | None = None,
) -> ProcessResult:
    """Process one Reddit submission."""
    title = getattr(submission, "title", None) or ""
    selftext = getattr(submission, "selftext", None) or ""

    return _process_item(
        item=submission,
        kind="submission",
        text=f"{title}\n{selftext}",
        is_match=submission_matches,
        quotes=quotes,
        replied_store_path=replied_store_path,
        blocked_users=blocked_users,
        bot_username=bot_username,
        allow_self_reply=allow_self_reply,
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
    allow_self_reply: bool,
    reply: ReplyFunction,
    dry_run: bool,
    logger: logging.Logger,
    cooldown: Cooldown | None = None,
    chooser: random.Random | None = None,
) -> ProcessResult:
    metadata = extract_item_metadata(item, kind)

    if not is_match(text):
        return ProcessResult(kind=metadata.kind, item_id=metadata.item_id, result="no_match")

    replied_ids = load_replied_ids(replied_store_path)
    if not should_reply(
        metadata.item_id,
        metadata.username,
        replied_ids,
        blocked_users,
        None if allow_self_reply else bot_username,
    ):
        log_reply_event(logger, "reply_skip", metadata, "decision_skip")
        return ProcessResult(kind=metadata.kind, item_id=metadata.item_id, result="decision_skip")

    if cooldown is not None and not cooldown.ready():
        log_reply_event(logger, "reply_skip", metadata, "cooldown")
        return ProcessResult(kind=metadata.kind, item_id=metadata.item_id, result="cooldown")

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
        return ProcessResult(kind=metadata.kind, item_id=metadata.item_id, result="would_reply")

    reply(quote)
    mark_replied(replied_store_path, metadata.item_id)

    if cooldown is not None:
        cooldown.mark()

    log_reply_event(logger, "reply_posted", metadata, "posted")
    return ProcessResult(kind=metadata.kind, item_id=metadata.item_id, result="posted")
