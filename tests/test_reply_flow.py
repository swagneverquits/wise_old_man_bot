import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from reddit_reply_bot.reply_flow import (
    normalize_username,
    reply_to_matched_item,
    should_reply,
    skip_reason,
)
from reddit_reply_bot.storage import load_replied_ids


class ReplyFlowTests(unittest.TestCase):
    def test_allows_new_unblocked_user(self) -> None:
        self.assertTrue(should_reply("abc123", "Player", set(), set()))

    def test_skips_already_replied_item(self) -> None:
        self.assertFalse(should_reply("abc123", "Player", {"abc123"}, set()))
        self.assertEqual(skip_reason("abc123", "Player", {"abc123"}, set()), "already_replied")

    def test_skips_blocked_user_case_insensitively(self) -> None:
        self.assertFalse(should_reply("abc123", "Player", set(), {"player"}))
        self.assertEqual(skip_reason("abc123", "Player", set(), {"player"}), "blocked_user")

    def test_skips_bot_username(self) -> None:
        self.assertFalse(
            should_reply("abc123", "wise-old-man-bot", set(), set(), "Wise-Old-Man-Bot")
        )
        self.assertEqual(
            skip_reason("abc123", "wise-old-man-bot", set(), set(), "Wise-Old-Man-Bot"),
            "self_reply",
        )

    def test_normalizes_deleted_author(self) -> None:
        self.assertEqual(normalize_username(None), "[deleted]")

    def test_replies_and_persists_after_success(self) -> None:
        with TemporaryDirectory() as directory:
            store_path = Path(directory) / "replied_items.json"
            replies: list[str] = []

            did_reply = reply_to_matched_item(
                item_id="abc123",
                username="Player",
                quotes=["Hello, [player name]."],
                replied_store_path=store_path,
                blocked_users=set(),
                reply=replies.append,
            )

            self.assertTrue(did_reply)
            self.assertEqual(replies, ["Hello, Player."])
            self.assertEqual(load_replied_ids(store_path), {"abc123"})

    def test_does_not_persist_when_reply_fails(self) -> None:
        with TemporaryDirectory() as directory:
            store_path = Path(directory) / "replied_items.json"

            def fail_reply(_: str) -> None:
                raise RuntimeError("reply failed")

            with self.assertRaises(RuntimeError):
                reply_to_matched_item(
                    item_id="abc123",
                    username="Player",
                    quotes=["Hello, [player name]."],
                    replied_store_path=store_path,
                    blocked_users=set(),
                    reply=fail_reply,
                )

            self.assertEqual(load_replied_ids(store_path), set())

    def test_does_not_reply_when_decision_skips(self) -> None:
        with TemporaryDirectory() as directory:
            store_path = Path(directory) / "replied_items.json"
            replies: list[str] = []

            did_reply = reply_to_matched_item(
                item_id="abc123",
                username="BlockedUser",
                quotes=["Hello, [player name]."],
                replied_store_path=store_path,
                blocked_users={"blockeduser"},
                reply=replies.append,
            )

            self.assertFalse(did_reply)
            self.assertEqual(replies, [])
            self.assertEqual(load_replied_ids(store_path), set())

    def test_does_not_reply_when_item_was_already_persisted(self) -> None:
        with TemporaryDirectory() as directory:
            store_path = Path(directory) / "replied_items.json"
            store_path.write_text('["abc123"]', encoding="utf-8")
            replies: list[str] = []

            did_reply = reply_to_matched_item(
                item_id="abc123",
                username="Player",
                quotes=["Hello, [player name]."],
                replied_store_path=store_path,
                blocked_users=set(),
                reply=replies.append,
            )

            self.assertFalse(did_reply)
            self.assertEqual(replies, [])
            self.assertEqual(load_replied_ids(store_path), {"abc123"})


if __name__ == "__main__":
    unittest.main()
