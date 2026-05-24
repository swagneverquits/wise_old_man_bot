"""Runnable Reddit polling workflow."""

from __future__ import annotations

import argparse
import logging
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

from prawcore.exceptions import PrawcoreException

from reddit_reply_bot.bot import process_comment, process_submission
from reddit_reply_bot.config import load_config
from reddit_reply_bot.data_files import load_blocked_users, load_quotes
from reddit_reply_bot.reddit_client import create_reddit_client
from reddit_reply_bot.runtime import Cooldown, configure_logging, retry_with_backoff

LOGGER = logging.getLogger("reddit_reply_bot")


@dataclass(frozen=True)
class PollSummary:
    comments_checked: int
    submissions_checked: int
    comments_new: int
    submissions_new: int
    results: Counter[str]


@dataclass
class SeenItems:
    comment_ids: set[str]
    submission_ids: set[str]

    @classmethod
    def empty(cls) -> "SeenItems":
        return cls(comment_ids=set(), submission_ids=set())


def main() -> None:
    parser = argparse.ArgumentParser(description="Wise Old Man Reddit reply bot")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--startup-limit", type=int, default=1000)
    parser.add_argument("--cooldown-seconds", type=float, default=10)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval-seconds", type=float, default=120)
    args = parser.parse_args()

    configure_logging()
    config = load_config()
    quotes = load_quotes(config.quotes_path)
    blocked_users = load_blocked_users(config.blocked_users_path)
    reddit = create_reddit_client(config.reddit)
    subreddit = reddit.subreddit(config.subreddits)
    cooldown = Cooldown(args.cooldown_seconds)
    seen_items = SeenItems.empty() if args.loop else None

    LOGGER.info(
        "starting_bot subreddits=%s dry_run=%s allow_self_reply=%s limit=%s loop=%s interval_seconds=%s",
        config.subreddits,
        config.dry_run,
        config.allow_self_reply,
        args.limit,
        args.loop,
        args.interval_seconds,
    )

    def poll_once(limit: int = args.limit) -> PollSummary:
        return poll_subreddit(
            subreddit=subreddit,
            limit=limit,
            quotes=quotes,
            replied_store_path=config.replied_items_path,
            blocked_users=blocked_users,
            bot_username=config.reddit.username,
            allow_self_reply=config.allow_self_reply,
            dry_run=config.dry_run,
            cooldown=cooldown,
            logger=LOGGER,
            seen_items=seen_items,
        )

    if args.loop:
        run_loop(
            poll_once,
            args.interval_seconds,
            LOGGER,
            normal_limit=args.limit,
            startup_limit=args.startup_limit,
        )
        return

    run_poll_with_retry(lambda: poll_once(args.limit))


def run_startup_poll(
    poll_once: Callable[[int], PollSummary],
    startup_limit: int,
    logger: logging.Logger,
) -> None:
    """Run a larger initial poll before settling into normal polling."""
    if startup_limit <= 0:
        raise ValueError("startup_limit must be greater than 0")

    logger.info("startup_poll limit=%s", startup_limit)
    run_poll_with_retry(lambda: poll_once(startup_limit))


def run_normal_poll(poll_once: Callable[[int], PollSummary], limit: int) -> None:
    """Run one normal poll."""
    run_poll_with_retry(lambda: poll_once(limit))


def run_loop(
    poll_once: Callable[[int], PollSummary],
    interval_seconds: float,
    logger: logging.Logger,
    normal_limit: int = 200,
    startup_limit: int = 1000,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Run polling continuously until interrupted."""
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be greater than 0")

    try:
        run_startup_poll(poll_once, startup_limit, logger)
        while True:
            run_normal_poll(poll_once, normal_limit)
            logger.info("poll_sleep interval_seconds=%s", interval_seconds)
            sleep(interval_seconds)
    except KeyboardInterrupt:
        logger.info("shutdown_requested")


def run_poll_with_retry(poll_once: Callable[[], None]) -> None:
    """Run one poll with retry handling for transient Reddit failures."""
    retry_with_backoff(
        poll_once,
        retry_exceptions=(PrawcoreException,),
        attempts=3,
        initial_delay_seconds=2,
    )


def poll_subreddit(
    subreddit,
    limit: int,
    quotes: list[str],
    replied_store_path,
    blocked_users: set[str],
    bot_username: str,
    allow_self_reply: bool,
    dry_run: bool,
    cooldown: Cooldown,
    logger: logging.Logger,
    seen_items: SeenItems | None = None,
) -> PollSummary:
    """Poll recent subreddit comments and submissions once."""
    comments_checked = 0
    submissions_checked = 0
    current_comment_ids: set[str] = set()
    current_submission_ids: set[str] = set()
    results: Counter[str] = Counter()

    for comment in subreddit.comments(limit=limit):
        comments_checked += 1
        current_comment_ids.add(str(getattr(comment, "id")))
        result = process_comment(
            comment=comment,
            quotes=quotes,
            replied_store_path=replied_store_path,
            blocked_users=blocked_users,
            bot_username=bot_username,
            allow_self_reply=allow_self_reply,
            reply=comment.reply,
            dry_run=dry_run,
            logger=logger,
            cooldown=cooldown,
        )
        results[result.result] += 1

    for submission in subreddit.new(limit=limit):
        submissions_checked += 1
        current_submission_ids.add(str(getattr(submission, "id")))
        result = process_submission(
            submission=submission,
            quotes=quotes,
            replied_store_path=replied_store_path,
            blocked_users=blocked_users,
            bot_username=bot_username,
            allow_self_reply=allow_self_reply,
            reply=submission.reply,
            dry_run=dry_run,
            logger=logger,
            cooldown=cooldown,
        )
        results[result.result] += 1

    if seen_items is None:
        comments_new = comments_checked
        submissions_new = submissions_checked
    else:
        comments_new = len(current_comment_ids - seen_items.comment_ids)
        submissions_new = len(current_submission_ids - seen_items.submission_ids)
        seen_items.comment_ids = current_comment_ids
        seen_items.submission_ids = current_submission_ids

    summary = PollSummary(
        comments_checked=comments_checked,
        submissions_checked=submissions_checked,
        comments_new=comments_new,
        submissions_new=submissions_new,
        results=results,
    )
    logger.info(
        "poll_summary comments=%s new_comments=%s submissions=%s new_submissions=%s posted=%s dry_run=%s skipped=%s no_match=%s cooldown=%s",
        summary.comments_checked,
        summary.comments_new,
        summary.submissions_checked,
        summary.submissions_new,
        summary.results["posted"],
        summary.results["would_reply"],
        summary.results["decision_skip"],
        summary.results["no_match"],
        summary.results["cooldown"],
    )
    return summary


if __name__ == "__main__":
    main()
