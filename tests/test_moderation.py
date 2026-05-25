import logging
import tempfile
import unittest
from pathlib import Path

from reddit_reply_bot.moderation import delete_low_karma_replies
from reddit_reply_bot.storage import load_reply_records, save_reply_records


class Comment:
    def __init__(self, score: int) -> None:
        self.score = score
        self.deleted = False

    def delete(self) -> None:
        self.deleted = True


class Reddit:
    def __init__(self, comments: dict[str, Comment]) -> None:
        self.comments = comments

    def comment(self, id: str) -> Comment:
        return self.comments[id]


class ModerationTests(unittest.TestCase):
    def test_deletes_active_reply_below_karma_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reply_audit.json"
            save_reply_records(
                path,
                [
                    {
                        "status": "active",
                        "bot_reply_id": "reply123",
                        "parent_item_id": "parent123",
                        "parent_kind": "comment",
                        "parent_subreddit": "test",
                        "parent_username": "Player",
                    }
                ],
            )
            comment = Comment(score=-6)

            results = delete_low_karma_replies(
                reddit=Reddit({"reply123": comment}),
                reply_records_path=path,
                karma_threshold=-5,
                logger=logging.getLogger("test-delete-low-karma"),
            )

            records = load_reply_records(path)

            self.assertTrue(comment.deleted)
            self.assertEqual(results["deleted"], 1)
            self.assertEqual(records[0]["status"], "deleted_low_karma")
            self.assertEqual(records[0]["deleted_score"], -6)

    def test_keeps_active_reply_at_or_above_karma_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reply_audit.json"
            save_reply_records(path, [{"status": "active", "bot_reply_id": "reply123"}])
            comment = Comment(score=-5)

            results = delete_low_karma_replies(
                reddit=Reddit({"reply123": comment}),
                reply_records_path=path,
                karma_threshold=-5,
                logger=logging.getLogger("test-keep-low-karma"),
            )

            records = load_reply_records(path)

            self.assertFalse(comment.deleted)
            self.assertEqual(results["kept"], 1)
            self.assertEqual(records[0]["status"], "active")
            self.assertEqual(records[0]["last_score"], -5)


if __name__ == "__main__":
    unittest.main()
