import logging
import random
import tempfile
import unittest
from pathlib import Path

from reddit_reply_bot.bot import process_comment, process_submission
from reddit_reply_bot.runtime import Cooldown
from reddit_reply_bot.storage import load_replied_ids


class Author:
    def __init__(self, name: str) -> None:
        self.name = name


class Comment:
    id = "comment123"
    subreddit = "test"

    def __init__(self, body: str, author: Author | None = None) -> None:
        self.body = body
        self.author = author


class Submission:
    id = "submission123"
    subreddit = "test"

    def __init__(self, title: str, author: Author | None = None) -> None:
        self.title = title
        self.author = author


class BotProcessingTests(unittest.TestCase):
    def test_dry_run_comment_logs_intended_reply_without_posting_or_persisting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "replied_items.json"
            replies: list[str] = []
            logger = logging.getLogger("test-dry-run-comment")

            with self.assertLogs(logger, level="INFO") as captured:
                did_process = process_comment(
                    comment=Comment("hello wise old man", Author("Player")),
                    quotes=["Hello, [player name]."],
                    replied_store_path=store_path,
                    blocked_users=set(),
                    bot_username="wise-old-man-bot",
                    reply=replies.append,
                    dry_run=True,
                    logger=logger,
                    chooser=random.Random(1),
                )

            self.assertTrue(did_process)
            self.assertEqual(replies, [])
            self.assertEqual(load_replied_ids(store_path), set())
            self.assertIn("dry_run_reply", "\n".join(captured.output))

    def test_live_comment_posts_and_persists_reply(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "replied_items.json"
            replies: list[str] = []
            logger = logging.getLogger("test-live-comment")

            did_process = process_comment(
                comment=Comment("hello wiseoldman", Author("Player")),
                quotes=["Hello, [player name]."],
                replied_store_path=store_path,
                blocked_users=set(),
                bot_username="wise-old-man-bot",
                reply=replies.append,
                dry_run=False,
                logger=logger,
                chooser=random.Random(1),
            )

            self.assertTrue(did_process)
            self.assertEqual(replies, ["Hello, Player."])
            self.assertEqual(load_replied_ids(store_path), {"comment123"})

    def test_submission_title_can_trigger_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "replied_items.json"
            logger = logging.getLogger("test-dry-run-submission")

            did_process = process_submission(
                submission=Submission("Wise Old Man question", Author("Player")),
                quotes=["Hello, [player name]."],
                replied_store_path=store_path,
                blocked_users=set(),
                bot_username="wise-old-man-bot",
                reply=lambda _: None,
                dry_run=True,
                logger=logger,
                chooser=random.Random(1),
            )

            self.assertTrue(did_process)

    def test_non_matching_comment_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "replied_items.json"
            replies: list[str] = []
            logger = logging.getLogger("test-no-match")

            did_process = process_comment(
                comment=Comment("hello there", Author("Player")),
                quotes=["Hello, [player name]."],
                replied_store_path=store_path,
                blocked_users=set(),
                bot_username="wise-old-man-bot",
                reply=replies.append,
                dry_run=False,
                logger=logger,
            )

            self.assertFalse(did_process)
            self.assertEqual(replies, [])
            self.assertEqual(load_replied_ids(store_path), set())

    def test_cooldown_skip_does_not_post(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "replied_items.json"
            replies: list[str] = []
            logger = logging.getLogger("test-cooldown")
            cooldown = Cooldown(seconds=10, clock=lambda: 100)
            cooldown.mark()

            did_process = process_comment(
                comment=Comment("hello wise old man", Author("Player")),
                quotes=["Hello, [player name]."],
                replied_store_path=store_path,
                blocked_users=set(),
                bot_username="wise-old-man-bot",
                reply=replies.append,
                dry_run=False,
                logger=logger,
                cooldown=cooldown,
            )

            self.assertFalse(did_process)
            self.assertEqual(replies, [])


if __name__ == "__main__":
    unittest.main()

