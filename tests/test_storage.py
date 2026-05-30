import tempfile
import unittest
from pathlib import Path

from reddit_reply_bot.storage import (
    add_match_record,
    dedupe_match_records_file,
    load_match_records,
    load_replied_ids,
    load_reply_records,
    mark_replied,
    match_audit_path,
    merge_reply_records_into_match_file,
    save_replied_ids,
    save_reply_records,
)


class StorageTests(unittest.TestCase):
    def test_missing_file_loads_empty_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bot_state.sqlite"

            self.assertEqual(load_replied_ids(path), set())

    def test_saves_and_loads_replied_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bot_state.sqlite"

            save_replied_ids(path, {"b", "a"})

            self.assertEqual(load_replied_ids(path), {"a", "b"})

    def test_mark_replied_persists_item_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bot_state.sqlite"

            updated_ids = mark_replied(path, "abc123")

            self.assertEqual(updated_ids, {"abc123"})
            self.assertEqual(load_replied_ids(path), {"abc123"})

    def test_match_audit_path_uses_state_database(self) -> None:
        path = Path("data/bot_state.sqlite")

        self.assertEqual(match_audit_path(path), path)

    def test_add_match_record_preserves_posted_reply_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bot_state.sqlite"

            add_match_record(
                path,
                {
                    "item_id": "comment123",
                    "result": "posted",
                    "bot_reply_id": "reply123",
                    "bot_reply_text": "hello",
                    "reply_status": "active",
                    "last_score": 3,
                },
            )
            add_match_record(path, {"item_id": "comment123", "result": "already_replied"})

            record = load_match_records(path)[0]
            self.assertEqual(record["item_id"], "comment123")
            self.assertEqual(record["result"], "posted")
            self.assertEqual(record["bot_reply_id"], "reply123")
            self.assertEqual(record["bot_reply_text"], "hello")
            self.assertEqual(record["reply_status"], "active")
            self.assertEqual(record["last_score"], 3)

    def test_dedupe_match_records_file_keeps_latest_and_drops_legacy_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "match_audit.json"
            save_reply_records(
                path,
                [
                    {
                        "item_id": "comment123",
                        "result": "would_reply",
                        "match_current_context": "wise old man",
                    },
                    {"item_id": "comment123", "result": "already_replied"},
                ],
            )

            before, after = dedupe_match_records_file(path)

            self.assertEqual((before, after), (2, 1))
            self.assertEqual(
                load_reply_records(path),
                [{"item_id": "comment123", "result": "already_replied"}],
            )

    def test_save_reply_records_preserves_key_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "match_audit.json"

            save_reply_records(path, [{"z": 1, "a": 2}])

            self.assertIn('"z": 1,\n    "a": 2', path.read_text(encoding="utf-8"))

    def test_merge_reply_records_into_match_file_adds_missing_match_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            match_path = Path(directory) / "match_audit.json"
            reply_path = Path(directory) / "reply_audit.json"
            save_reply_records(match_path, [])
            save_reply_records(
                reply_path,
                [
                    {
                        "parent_item_id": "comment123",
                        "parent_kind": "comment",
                        "parent_subreddit": "test",
                        "parent_username": "Player",
                        "parent_permalink": "/r/test/comments/post/comment123",
                        "parent_text": "hello wise old man",
                        "bot_reply_id": "reply123",
                        "bot_reply_text": "hello",
                        "status": "active",
                    }
                ],
            )

            counts = merge_reply_records_into_match_file(match_path, reply_path)

            self.assertEqual(counts, (0, 1, 1))
            self.assertEqual(
                load_reply_records(match_path),
                [
                    {
                        "created_at": "",
                        "item_id": "comment123",
                        "kind": "comment",
                        "subreddit": "test",
                        "username": "Player",
                        "permalink": "/r/test/comments/post/comment123",
                        "result": "posted",
                        "match_reason": "legacy_reply_audit",
                        "match_signals": [],
                        "text": "hello wise old man",
                        "parent_context": "",
                        "bot_reply_id": "reply123",
                        "bot_reply_text": "hello",
                        "reply_status": "active",
                    }
                ],
            )


if __name__ == "__main__":
    unittest.main()
