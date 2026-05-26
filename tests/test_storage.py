import tempfile
import unittest
from pathlib import Path

from reddit_reply_bot.storage import (
    add_reply_record,
    load_replied_ids,
    load_reply_records,
    mark_replied,
    match_audit_path,
    reply_audit_path,
    save_replied_ids,
)


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

    def test_reply_audit_path_is_colocated_with_replied_items(self) -> None:
        path = Path("data/replied_items.json")

        self.assertEqual(reply_audit_path(path), Path("data/reply_audit.json"))

    def test_match_audit_path_is_colocated_with_replied_items(self) -> None:
        path = Path("data/replied_items.json")

        self.assertEqual(match_audit_path(path), Path("data/match_audit.json"))

    def test_add_reply_record_persists_audit_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reply_audit.json"

            add_reply_record(path, {"bot_reply_id": "reply123", "status": "active"})

            self.assertEqual(
                load_reply_records(path),
                [{"bot_reply_id": "reply123", "status": "active"}],
            )


if __name__ == "__main__":
    unittest.main()
