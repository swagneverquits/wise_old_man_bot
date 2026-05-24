"""Runtime reliability helpers."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RedditItemMetadata:
    item_id: str
    username: str
    subreddit: str
    kind: str


class Cooldown:
    """Track whether actions are happening too frequently."""

    def __init__(self, seconds: float, clock: Callable[[], float] | None = None) -> None:
        self.seconds = seconds
        self.clock = clock or time.monotonic
        self._last_action_at: float | None = None

    def ready(self) -> bool:
        if self._last_action_at is None:
            return True

        return self.clock() - self._last_action_at >= self.seconds

    def mark(self) -> None:
        self._last_action_at = self.clock()


def extract_item_metadata(item: Any, kind: str) -> RedditItemMetadata:
    """Extract stable metadata from a PRAW comment or submission."""
    author = getattr(item, "author", None)
    username = getattr(author, "name", None) or "[deleted]"

    return RedditItemMetadata(
        item_id=str(getattr(item, "id")),
        username=username,
        subreddit=str(getattr(item, "subreddit", "")),
        kind=kind,
    )


def retry_with_backoff(
    operation: Callable[[], T],
    retry_exceptions: tuple[type[Exception], ...],
    attempts: int = 3,
    initial_delay_seconds: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Run an operation with exponential backoff for transient failures."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    delay = initial_delay_seconds

    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except retry_exceptions:
            if attempt == attempts:
                raise

            sleep(delay)
            delay *= 2

    raise RuntimeError("unreachable retry state")


def log_reply_event(
    logger: logging.Logger,
    event: str,
    metadata: RedditItemMetadata,
    result: str,
) -> None:
    """Log reply flow events in a readable key/value format."""
    logger.info(
        "%s result=%s kind=%s item_id=%s subreddit=%s username=%s",
        event,
        result,
        metadata.kind,
        metadata.item_id,
        metadata.subreddit,
        metadata.username,
    )


def configure_logging(level: int = logging.INFO) -> None:
    """Configure basic application logging."""
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")
