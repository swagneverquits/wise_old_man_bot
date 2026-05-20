"""Runnable Reddit polling workflow."""

from __future__ import annotations

import argparse
import logging

from prawcore.exceptions import PrawcoreException

from reddit_reply_bot.bot import process_comment, process_submission
from reddit_reply_bot.config import load_config
from reddit_reply_bot.data_files import load_blocked_users, load_quotes
from reddit_reply_bot.reddit_client import create_reddit_client
from reddit_reply_bot.runtime import Cooldown, configure_logging, retry_with_backoff

LOGGER = logging.getLogger("reddit_reply_bot")


def main() -> None:
    parser = argparse.ArgumentParser(description="Wise Old Man Reddit reply bot")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--cooldown-seconds", type=float, default=10)
    args = parser.parse_args()

    configure_logging()
    config = load_config()
    quotes = load_quotes(config.quotes_path)
    blocked_users = load_blocked_users(config.blocked_users_path)
    reddit = create_reddit_client(config.reddit)
    subreddit = reddit.subreddit(config.subreddits)
    cooldown = Cooldown(args.cooldown_seconds)

    LOGGER.info(
        "starting_poll subreddits=%s dry_run=%s limit=%s",
        config.subreddits,
        config.dry_run,
        args.limit,
    )

    def poll() -> None:
        for comment in subreddit.comments(limit=args.limit):
            process_comment(
                comment=comment,
                quotes=quotes,
                replied_store_path=config.replied_items_path,
                blocked_users=blocked_users,
                bot_username=config.reddit.username,
                reply=comment.reply,
                dry_run=config.dry_run,
                logger=LOGGER,
                cooldown=cooldown,
            )

        for submission in subreddit.new(limit=args.limit):
            process_submission(
                submission=submission,
                quotes=quotes,
                replied_store_path=config.replied_items_path,
                blocked_users=blocked_users,
                bot_username=config.reddit.username,
                reply=submission.reply,
                dry_run=config.dry_run,
                logger=LOGGER,
                cooldown=cooldown,
            )

    retry_with_backoff(
        poll,
        retry_exceptions=(PrawcoreException,),
        attempts=3,
        initial_delay_seconds=2,
    )


if __name__ == "__main__":
    main()

