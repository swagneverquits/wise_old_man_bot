import tempfile
import unittest
from pathlib import Path

from reddit_reply_bot.storage import load_replied_ids, mark_replied, save_replied_ids


class StorageTests(unittest.TestCase):
    def test_missing_file_loads_empty_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replied_items.json"

            self.assertEqual(load_replied_ids(path), set())

    def test_saves_and_loads_replied_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replied_items.json"

            save_replied_ids(path, {"b", "a"})

            self.assertEqual(load_replied_ids(path), {"a", "b"})

    def test_mark_replied_persists_item_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replied_items.json"

            updated_ids = mark_replied(path, "abc123")

            self.assertEqual(updated_ids, {"abc123"})
            self.assertEqual(load_replied_ids(path), {"abc123"})


if __name__ == "__main__":
    unittest.main()

