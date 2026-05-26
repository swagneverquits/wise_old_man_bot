import unittest

from reddit_reply_bot.matcher import (
    comment_matches,
    contains_wise_old_man,
    decide_wise_old_man_match,
    submission_matches,
)


class WiseOldManMatcherTests(unittest.TestCase):
    def assertDecision(
        self,
        current_text: str,
        *,
        parent_text: str | None = None,
        should_reply: bool,
        reason: str,
        signals: set[str] | None = None,
    ) -> None:
        decision = decide_wise_old_man_match(current_text, parent_text)

        self.assertEqual(decision.should_reply, should_reply)
        self.assertEqual(decision.reason, reason)
        for signal in signals or set():
            self.assertIn(signal, decision.signals)

    def test_matches_keyword_variants(self) -> None:
        examples = [
            "wise old man",
            "wise  old  man",
            "wise\told\tman",
        ]

        for example in examples:
            with self.subTest(example=example):
                self.assertTrue(contains_wise_old_man(example))

    def test_matches_case_insensitively(self) -> None:
        self.assertTrue(contains_wise_old_man("The WISE Old MAN knows."))

    def test_matches_comment_body(self) -> None:
        self.assertTrue(comment_matches("Has anyone asked the wise old man?"))

    def test_matches_submission_title(self) -> None:
        self.assertTrue(submission_matches("Wise Old Man clue scroll theory"))

    def test_does_not_match_unrelated_text(self) -> None:
        examples = [
            "",
            "old man wise",
            "wise young man",
            "the wisest old mansion",
            "otherwise old manager",
            "wiseoldman",
            "WiseOldMan",
            "wise oldman",
            "wiseold man",
            None,
        ]

        for example in examples:
            with self.subTest(example=example):
                self.assertFalse(contains_wise_old_man(example))

    def test_skips_tracker_site_context_from_current_text(self) -> None:
        self.assertDecision(
            "Edit: although it's far more likely this person just didn't log their account on wise old man for a long time.",
            should_reply=False,
            reason="tracker_context",
            signals={"current:account", "current:log"},
        )

    def test_skips_tracker_site_context_from_parent_text(self) -> None:
        self.assertDecision(
            "Maybe check wise old man?",
            parent_text="What skill is it? You can get 10m/hr plus rates.",
            should_reply=False,
            reason="tracker_context",
            signals={"parent:xp_rates"},
        )

    def test_parent_text_does_not_trigger_by_itself(self) -> None:
        self.assertDecision(
            "It's a site for tracking xp gains.",
            parent_text="What is Wise Old Man?",
            should_reply=False,
            reason="no_match",
        )

    def test_matches_npc_context(self) -> None:
        self.assertDecision(
            "I asked the wise old man in Draynor.",
            should_reply=True,
            reason="matched_npc_context",
            signals={"current:draynor"},
        )


if __name__ == "__main__":
    unittest.main()
