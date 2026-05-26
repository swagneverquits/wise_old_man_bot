"""Bot item processing."""

from __future__ import annotations

import logging
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from reddit_reply_bot.matcher import MatchDecision, contains_wise_old_man, decide_wise_old_man_match
from reddit_reply_bot.quotes import choose_quote
from reddit_reply_bot.reply_flow import ReplyFunction, skip_reason
from reddit_reply_bot.runtime import Cooldown, extract_item_metadata, log_reply_event
from reddit_reply_bot.storage import (
    add_match_record,
    add_reply_record,
    load_replied_ids,
    mark_replied,
    match_audit_path,
    reply_audit_path,
)

ParentTextExtractor = Callable[[Any], str]


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
        parent_text=comment_parent_text,
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
        parent_text=lambda _: "",
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
    parent_text: ParentTextExtractor,
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

    if not contains_wise_old_man(text):
        return ProcessResult(kind=metadata.kind, item_id=metadata.item_id, result="no_match")

    parent_context = parent_text(item)
    match_decision = decide_wise_old_man_match(text, parent_context)
    if not match_decision.should_reply:
        record_match(
            replied_store_path=replied_store_path,
            item=item,
            metadata=metadata,
            text=text,
            parent_context=parent_context,
            decision=match_decision,
            result=match_decision.reason,
        )
        log_reply_event(logger, "reply_skip", metadata, match_decision.reason)
        return ProcessResult(
            kind=metadata.kind,
            item_id=metadata.item_id,
            result=match_decision.reason,
        )

    replied_ids = load_replied_ids(replied_store_path)
    reason = skip_reason(
        metadata.item_id,
        metadata.username,
        replied_ids,
        blocked_users,
        None if allow_self_reply else bot_username,
    )
    if reason is not None:
        record_match(
            replied_store_path=replied_store_path,
            item=item,
            metadata=metadata,
            text=text,
            parent_context=parent_context,
            decision=match_decision,
            result=reason,
        )
        if reason != "already_replied":
            log_reply_event(logger, "reply_skip", metadata, reason)
        return ProcessResult(kind=metadata.kind, item_id=metadata.item_id, result=reason)

    if cooldown is not None and not cooldown.ready():
        record_match(
            replied_store_path=replied_store_path,
            item=item,
            metadata=metadata,
            text=text,
            parent_context=parent_context,
            decision=match_decision,
            result="cooldown",
        )
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
        record_match(
            replied_store_path=replied_store_path,
            item=item,
            metadata=metadata,
            text=text,
            parent_context=parent_context,
            decision=match_decision,
            result="would_reply",
            quote=quote,
        )
        return ProcessResult(kind=metadata.kind, item_id=metadata.item_id, result="would_reply")

    reply_result = reply(quote)
    mark_replied(replied_store_path, metadata.item_id)
    record_posted_reply(
        replied_store_path=replied_store_path,
        item=item,
        metadata=metadata,
        quote=quote,
        reply_result=reply_result,
    )

    if cooldown is not None:
        cooldown.mark()

    log_reply_event(logger, "reply_posted", metadata, "posted")
    record_match(
        replied_store_path=replied_store_path,
        item=item,
        metadata=metadata,
        text=text,
        parent_context=parent_context,
        decision=match_decision,
        result="posted",
        quote=quote,
        reply_result=reply_result,
    )
    return ProcessResult(kind=metadata.kind, item_id=metadata.item_id, result="posted")


def record_posted_reply(
    replied_store_path: Path,
    item: Any,
    metadata,
    quote: str,
    reply_result: Any,
) -> None:
    """Record bot reply metadata needed for later low-karma moderation."""
    bot_reply_id = getattr(reply_result, "id", None)
    if not bot_reply_id:
        return

    add_reply_record(
        reply_audit_path(replied_store_path),
        {
            "status": "active",
            "bot_reply_id": str(bot_reply_id),
            "bot_reply_text": quote,
            "parent_item_id": metadata.item_id,
            "parent_kind": metadata.kind,
            "parent_subreddit": metadata.subreddit,
            "parent_username": metadata.username,
            "parent_permalink": str(getattr(item, "permalink", "")),
            "parent_text": parent_text(item, metadata.kind),
        },
    )


def record_match(
    replied_store_path: Path,
    item: Any,
    metadata,
    text: str | None,
    parent_context: str,
    decision: MatchDecision,
    result: str,
    quote: str | None = None,
    reply_result: Any = None,
) -> None:
    """Record every current-text Wise Old Man trigger for later review."""
    record: dict[str, object] = {
        "created_at": datetime.now(UTC).isoformat(),
        "result": result,
        "match_reason": decision.reason,
        "match_signals": list(decision.signals),
        "match_mention": decision.mention,
        "match_current_context": decision.current_context,
        "match_parent_context": decision.parent_context,
        "item_id": metadata.item_id,
        "kind": metadata.kind,
        "subreddit": metadata.subreddit,
        "username": metadata.username,
        "permalink": str(getattr(item, "permalink", "")),
        "text": text or "",
        "parent_context": parent_context,
    }
    if quote is not None:
        record["bot_reply_text"] = quote

    bot_reply_id = getattr(reply_result, "id", None)
    if bot_reply_id:
        record["bot_reply_id"] = str(bot_reply_id)

    add_match_record(match_audit_path(replied_store_path), record)


def parent_text(item: Any, kind: str) -> str:
    """Return a compact parent item text snapshot for moderation review."""
    if kind == "comment":
        return str(getattr(item, "body", "") or "")

    title = str(getattr(item, "title", "") or "")
    selftext = str(getattr(item, "selftext", "") or "")
    return "\n".join(part for part in [title, selftext] if part)


def comment_parent_text(comment: Any) -> str:
    """Return text from a comment's parent comment or submission."""
    parent_method = getattr(comment, "parent", None)
    if not callable(parent_method):
        return ""

    parent = parent_method()
    if hasattr(parent, "body"):
        return str(getattr(parent, "body", "") or "")

    title = str(getattr(parent, "title", "") or "")
    selftext = str(getattr(parent, "selftext", "") or "")
    return "\n".join(part for part in [title, selftext] if part)
