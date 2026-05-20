"""PRAW client construction."""

from __future__ import annotations

import praw

from reddit_reply_bot.config import RedditConfig


def create_reddit_client(config: RedditConfig) -> praw.Reddit:
    """Create an authenticated PRAW client."""
    return praw.Reddit(
        client_id=config.client_id,
        client_secret=config.client_secret,
        username=config.username,
        password=config.password,
        user_agent=config.user_agent,
    )

