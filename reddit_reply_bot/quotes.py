"""Quote selection and formatting."""

from __future__ import annotations

import random
from collections.abc import Sequence


def format_quote(quote: str, username: str | None) -> str:
    """Replace supported placeholders in a quote."""
    player_name = username or "adventurer"
    return quote.replace("[player name]", player_name)


def choose_quote(
    quotes: Sequence[str],
    username: str | None,
    chooser: random.Random | None = None,
) -> str:
    """Select and format a quote."""
    if not quotes:
        raise ValueError("quotes must contain at least one quote")

    random_source = chooser or random
    return format_quote(random_source.choice(quotes), username)

