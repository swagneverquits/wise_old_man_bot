"""Trigger detection for Wise Old Man mentions."""

from __future__ import annotations

import re

WISE_OLD_MAN_PATTERN = re.compile(r"\bwise\s+old\s+man\b", re.IGNORECASE)


def contains_wise_old_man(text: str | None) -> bool:
    """Return whether text mentions the Wise Old Man."""
    if not text:
        return False

    return WISE_OLD_MAN_PATTERN.search(text) is not None


def comment_matches(comment_body: str | None) -> bool:
    """Return whether a Reddit comment body should trigger the bot."""
    return contains_wise_old_man(comment_body)


def submission_matches(title: str | None) -> bool:
    """Return whether a Reddit submission title should trigger the bot."""
    return contains_wise_old_man(title)
