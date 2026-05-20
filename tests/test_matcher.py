import unittest

from reddit_reply_bot.matcher import (
    comment_matches,
    contains_wise_old_man,
    submission_matches,
)


class WiseOldManMatcherTests(unittest.TestCase):
    def test_matches_keyword_variants(self) -> None:
        examples = [
            "wise old man",
            "wise oldman",
            "wiseold man",
            "wiseoldman",
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
            None,
        ]

        for example in examples:
            with self.subTest(example=example):
                self.assertFalse(contains_wise_old_man(example))


if __name__ == "__main__":
    unittest.main()

