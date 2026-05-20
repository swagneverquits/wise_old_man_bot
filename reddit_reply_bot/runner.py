"""Runnable Reddit polling workflow."""

from __future__ import annotations

import argparse
import logging
import time
from collections.abc import Callable

from prawcore.exceptions import PrawcoreException

from reddit_reply_bot.bot import process_comment, process_submission
from reddit_reply_bot.config import load_config
from reddit_reply_bot.data_files import load_blocked_users, load_quotes
from reddit_reply_bot.reddit_client import create_reddit_client
from reddit_reply_bot.runtime import Cooldown, configure_logging, retry_with_backoff

LOGGER = logging.getLogger("reddit_reply_bot")


def main() -> None:
    parser = argparse.ArgumentParser(description="Wise Old Man Reddit reply bot")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--cooldown-seconds", type=float, default=10)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval-seconds", type=float, default=300)
    args = parser.parse_args()

    configure_logging()
    config = load_config()
    quotes = load_quotes(config.quotes_path)
    blocked_users = load_blocked_users(config.blocked_users_path)
    reddit = create_reddit_client(config.reddit)
    subreddit = reddit.subreddit(config.subreddits)
    cooldown = Cooldown(args.cooldown_seconds)

    LOGGER.info(
        "starting_bot subreddits=%s dry_run=%s allow_self_reply=%s limit=%s loop=%s interval_seconds=%s",
        config.subreddits,
        config.dry_run,
        config.allow_self_reply,
        args.limit,
        args.loop,
        args.interval_seconds,
    )

    poll_once = lambda: poll_subreddit(
        subreddit=subreddit,
        limit=args.limit,
        quotes=quotes,
        replied_store_path=config.replied_items_path,
        blocked_users=blocked_users,
        bot_username=config.reddit.username,
        allow_self_reply=config.allow_self_reply,
        dry_run=config.dry_run,
        cooldown=cooldown,
        logger=LOGGER,
    )

    if args.loop:
        run_loop(poll_once, args.interval_seconds, LOGGER)
        return

    run_poll_with_retry(poll_once)


def run_loop(
    poll_once: Callable[[], None],
    interval_seconds: float,
    logger: logging.Logger,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Run polling continuously until interrupted."""
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be greater than 0")

    try:
        while True:
            run_poll_with_retry(poll_once)
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
) -> None:
    """Poll recent subreddit comments and submissions once."""
    for comment in subreddit.comments(limit=limit):
        process_comment(
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

    for submission in subreddit.new(limit=limit):
        process_submission(
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


if __name__ == "__main__":
    main()
