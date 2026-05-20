import json
import tempfile
import unittest
from pathlib import Path

from reddit_reply_bot.data_files import load_blocked_users, load_quotes


class DataFileTests(unittest.TestCase):
    def test_loads_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quotes.json"
            path.write_text(json.dumps(["Hello", "Hi"]), encoding="utf-8")

            self.assertEqual(load_quotes(path), ["Hello", "Hi"])

    def test_rejects_empty_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quotes.json"
            path.write_text("[]", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "at least one quote"):
                load_quotes(path)

    def test_rejects_non_string_quote(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quotes.json"
            path.write_text(json.dumps(["Hello", 123]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "non-empty strings"):
                load_quotes(path)

    def test_loads_blocked_users_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blocked_users.json"
            path.write_text(json.dumps(["Player", " OtherUser "]), encoding="utf-8")

            self.assertEqual(load_blocked_users(path), {"player", "otheruser"})

    def test_missing_blocked_users_file_returns_empty_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blocked_users.json"

            self.assertEqual(load_blocked_users(path), set())


if __name__ == "__main__":
    unittest.main()

