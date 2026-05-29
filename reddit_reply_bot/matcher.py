"""Trigger detection for Wise Old Man mentions."""

from __future__ import annotations

import re
from dataclasses import dataclass

WISE_OLD_MAN_PATTERN = re.compile(r"\bwise\s+old\s+man\b", re.IGNORECASE)
WORD_PATTERN = re.compile(r"\b[\w.']+\b")

TRACKER_PHRASES = {
    "on wise old man",
    "on the wise old man",
    "check wise old man",
    "checked wise old man",
    "logged on wise old man",
    "tracked by wise old man",
    "wise old man profile",
}

TRACKER_TERMS = {
    "account": "account",
    "ehp": "xp_rates",
    "exp": "xp_rates",
    "gains": "xp_rates",
    "log": "log",
    "logged": "log",
    "profile": "profile",
    "rank": "rank",
    "ranks": "rank",
    "rates": "xp_rates",
    "site": "site",
    "tracked": "tracker",
    "tracker": "tracker",
    "tracking": "tracker",
    "website": "site",
    "wiseoldman.net": "site",
    "wom": "site",
    "xp": "xp_rates",
}

NPC_PHRASES = {
    "old man npc": "npc",
    "talk to": "talk_to",
    "wise old man says": "dialogue",
}

NPC_TERMS = {
    "ask": "ask",
    "asked": "ask",
    "bank": "bank",
    "dialogue": "dialogue",
    "draynor": "draynor",
    "lore": "lore",
    "npc": "npc",
    "quest": "quest",
}


@dataclass(frozen=True)
class MatchDecision:
    """Context-aware decision for a Wise Old Man mention."""

    should_reply: bool
    reason: str
    mention: str = ""
    signals: tuple[str, ...] = ()
    current_context: str = ""
    parent_context: str = ""


def contains_wise_old_man(text: str | None) -> bool:
    """Return whether text mentions the Wise Old Man."""
    if not text:
        return False

    return WISE_OLD_MAN_PATTERN.search(text) is not None


def decide_wise_old_man_match(
    current_text: str | None,
    parent_text: str | None = None,
) -> MatchDecision:
    """Classify whether a current-text mention should trigger a reply."""
    if not current_text:
        return MatchDecision(should_reply=False, reason="no_match")

    match = WISE_OLD_MAN_PATTERN.search(current_text)
    if match is None:
        return MatchDecision(should_reply=False, reason="no_match")

    current_context = current_text
    parent_context = parent_text or ""
    signals = tuple(
        sorted(
            {
                *_tracker_signals(current_context, "current"),
                *_tracker_signals(parent_context, "parent"),
            }
        )
    )
    npc_signals = tuple(
        sorted(
            {
                *_npc_signals(current_context, "current"),
                *_npc_signals(parent_context, "parent"),
            }
        )
    )

    if signals:
        return MatchDecision(
            should_reply=False,
            reason="tracker_context",
            mention=match.group(0),
            signals=signals,
            current_context=current_context,
            parent_context=parent_context,
        )

    return MatchDecision(
        should_reply=True,
        reason="matched_npc_context" if npc_signals else "matched",
        mention=match.group(0),
        signals=npc_signals,
        current_context=current_context,
        parent_context=parent_context,
    )


def comment_matches(comment_body: str | None) -> bool:
    """Return whether a Reddit comment body should trigger the bot."""
    return decide_wise_old_man_match(comment_body).should_reply


def submission_matches(text: str | None) -> bool:
    """Return whether a Reddit submission should trigger the bot."""
    return decide_wise_old_man_match(text).should_reply


def _tracker_signals(text: str, source: str) -> set[str]:
    normalized = _normalize_text(text)
    signals = {
        f"{source}:phrase:{phrase.replace(' ', '_')}"
        for phrase in TRACKER_PHRASES
        if phrase in normalized
    }
    signals.update(_term_signals(normalized, source, TRACKER_TERMS))
    return signals


def _npc_signals(text: str, source: str) -> set[str]:
    normalized = _normalize_text(text)
    signals = {
        f"{source}:{signal}"
        for phrase, signal in NPC_PHRASES.items()
        if phrase in normalized
    }
    signals.update(_term_signals(normalized, source, NPC_TERMS))
    return signals


def _term_signals(text: str, source: str, terms: dict[str, str]) -> set[str]:
    words = {word.group(0) for word in WORD_PATTERN.finditer(text)}
    return {
        f"{source}:{signal}"
        for term, signal in terms.items()
        if term in words
    }


def _normalize_text(text: str) -> str:
    return " ".join(text.casefold().split())
