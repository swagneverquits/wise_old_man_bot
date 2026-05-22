"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class RedditConfig:
    client_id: str
    client_secret: str
    username: str
    password: str
    user_agent: str


@dataclass(frozen=True)
class BotConfig:
    reddit: RedditConfig
    subreddits: str
    quotes_path: Path
    blocked_users_path: Path
    replied_items_path: Path
    dry_run: bool
    allow_self_reply: bool


def load_config(env_file: Path | None = None, load_default_dotenv: bool = True) -> BotConfig:
    """Load bot configuration from environment variables."""
    if env_file is not None:
        load_dotenv(env_file)
    elif load_default_dotenv:
        load_dotenv()

    return BotConfig(
        reddit=RedditConfig(
            client_id=_required_env("REDDIT_CLIENT_ID"),
            client_secret=_required_env("REDDIT_CLIENT_SECRET"),
            username=_required_env("REDDIT_USERNAME"),
            password=_required_env("REDDIT_PASSWORD"),
            user_agent=_required_env("REDDIT_USER_AGENT"),
        ),
        subreddits=_env("REDDIT_SUBREDDITS", "test"),
        quotes_path=Path(_env("QUOTES_PATH", "config/quotes.json")),
        blocked_users_path=Path(_env("BLOCKED_USERS_PATH", "config/blocked_users.json")),
        replied_items_path=Path(_env("REPLIED_ITEMS_PATH", "data/replied_items.json")),
        dry_run=_bool_env("DRY_RUN", default=True),
        allow_self_reply=_bool_env("ALLOW_SELF_REPLY", default=False),
    )


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise ValueError(f"Missing required environment variable: {name}")

    return value


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default

    return value


def _bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}
