import random
import unittest

from reddit_reply_bot.quotes import choose_quote, format_quote


class QuoteTests(unittest.TestCase):
    def test_replaces_player_name_placeholder(self) -> None:
        quote = "Greetings, [player name]."

        self.assertEqual(format_quote(quote, "Zezima"), "Greetings, Zezima.")

    def test_uses_fallback_name_for_missing_user(self) -> None:
        quote = "Greetings, [player name]."

        self.assertEqual(format_quote(quote, None), "Greetings, adventurer.")

    def test_selects_quote_with_injected_random_source(self) -> None:
        quotes = ["First", "Second", "Third"]

        self.assertEqual(choose_quote(quotes, "Player", random.Random(1)), "First")

    def test_rejects_empty_quote_list(self) -> None:
        with self.assertRaises(ValueError):
            choose_quote([], "Player")


if __name__ == "__main__":
    unittest.main()

