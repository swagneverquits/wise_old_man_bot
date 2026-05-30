import logging
import random
import tempfile
import unittest
from pathlib import Path

from reddit_reply_bot.bot import process_comment, process_submission
from reddit_reply_bot.runtime import Cooldown
from reddit_reply_bot.storage import load_match_records, load_replied_ids, save_replied_ids


class Author:
    def __init__(self, name: str) -> None:
        self.name = name


class ParentComment:
    subreddit = "test"

    def __init__(self, body: str) -> None:
        self.body = body


class Comment:
    id = "comment123"
    subreddit = "test"
    permalink = "/r/test/comments/post/comment123"

    def __init__(
        self,
        body: str,
        author: Author | None = None,
        parent_item: object | None = None,
    ) -> None:
        self.body = body
        self.author = author
        self._parent_item = parent_item

    def parent(self) -> object:
        if self._parent_item is None:
            return ParentComment("")
        return self._parent_item


class Submission:
    id = "submission123"
    subreddit = "test"
    permalink = "/r/test/comments/submission123"

    def __init__(
        self,
        title: str,
        author: Author | None = None,
        selftext: str = "",
    ) -> None:
        self.title = title
        self.author = author
        self.selftext = selftext


class Reply:
    def __init__(self, item_id: str) -> None:
        self.id = item_id


class BotProcessingTests(unittest.TestCase):
    def process_test_comment(
        self,
        store_path: Path,
        body: str = "hello wise old man",
        author: str = "Player",
        parent_item: object | None = None,
        reply=None,
        dry_run: bool = False,
        logger_name: str = "test-comment",
    ):
        return process_comment(
            comment=Comment(body, Author(author), parent_item=parent_item),
            quotes=["Hello, [player name]."],
            replied_store_path=store_path,
            blocked_users=set(),
            bot_username="wise-old-man-bot",
            allow_self_reply=False,
            reply=reply or (lambda _: None),
            dry_run=dry_run,
            logger=logging.getLogger(logger_name),
            chooser=random.Random(1),
        )

    def test_dry_run_comment_logs_intended_reply_without_posting_or_persisting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "bot_state.sqlite"
            replies: list[str] = []
            logger = logging.getLogger("test-dry-run-comment")

            with self.assertLogs(logger, level="INFO") as captured:
                result = process_comment(
                    comment=Comment("hello wise old man", Author("Player")),
                    quotes=["Hello, [player name]."],
                    replied_store_path=store_path,
                    blocked_users=set(),
                    bot_username="wise-old-man-bot",
                    allow_self_reply=False,
                    reply=replies.append,
                    dry_run=True,
                    logger=logger,
                    chooser=random.Random(1),
                )

            self.assertTrue(result.did_reply)
            self.assertEqual(result.result, "would_reply")
            self.assertEqual(replies, [])
            self.assertEqual(load_replied_ids(store_path), set())
            self.assertIn("dry_run_reply", "\n".join(captured.output))

    def test_live_comment_posts_and_persists_reply(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "bot_state.sqlite"
            replies: list[str] = []
            logger = logging.getLogger("test-live-comment")

            result = process_comment(
                comment=Comment("hello wise old man", Author("Player")),
                quotes=["Hello, [player name]."],
                replied_store_path=store_path,
                blocked_users=set(),
                bot_username="wise-old-man-bot",
                allow_self_reply=False,
                reply=replies.append,
                dry_run=False,
                logger=logger,
                chooser=random.Random(1),
            )

            self.assertTrue(result.did_reply)
            self.assertEqual(result.result, "posted")
            self.assertEqual(replies, ["Hello, Player."])
            self.assertEqual(load_replied_ids(store_path), {"comment123"})

    def test_live_comment_records_reply_metadata_in_match_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "bot_state.sqlite"
            logger = logging.getLogger("test-live-comment-audit")

            def reply(_: str) -> Reply:
                return Reply("botreply123")

            result = process_comment(
                comment=Comment("hello wise old man", Author("Player")),
                quotes=["Hello, [player name]."],
                replied_store_path=store_path,
                blocked_users=set(),
                bot_username="wise-old-man-bot",
                allow_self_reply=False,
                reply=reply,
                dry_run=False,
                logger=logger,
                chooser=random.Random(1),
            )

            records = load_match_records(store_path)

            self.assertEqual(result.result, "posted")
            self.assertEqual(records[0]["bot_reply_id"], "botreply123")
            self.assertEqual(records[0]["bot_reply_text"], "Hello, Player.")
            self.assertEqual(records[0]["reply_status"], "active")
            self.assertEqual(records[0]["item_id"], "comment123")
            self.assertEqual(records[0]["text"], "hello wise old man")
            self.assertEqual(records[0]["match_reason"], "matched")
            self.assertNotIn("match_current_context", records[0])
            self.assertNotIn("match_parent_context", records[0])

    def test_tracker_context_skip_records_match_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "bot_state.sqlite"
            replies: list[str] = []

            result = self.process_test_comment(
                store_path,
                "They probably didn't log their account on wise old man for a long time.",
                parent_item=ParentComment("What skill is it? 10m/hr xp rates."),
                reply=replies.append,
                logger_name="test-tracker-context-match-audit",
            )
            records = load_match_records(store_path)

            self.assertFalse(result.did_reply)
            self.assertEqual(result.result, "tracker_context")
            self.assertEqual(replies, [])
            self.assertEqual(records[0]["result"], "tracker_context")
            self.assertEqual(records[0]["match_reason"], "tracker_context")
            self.assertIn("current:account", records[0]["match_signals"])
            self.assertIn("parent:xp_rates", records[0]["match_signals"])
            self.assertNotIn("match_current_context", records[0])
            self.assertNotIn("match_parent_context", records[0])

    def test_submission_body_can_trigger_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "bot_state.sqlite"
            logger = logging.getLogger("test-dry-run-submission-body")

            result = process_submission(
                submission=Submission(
                    "A normal title",
                    Author("Player"),
                    selftext="The body says wise old man.",
                ),
                quotes=["Hello, [player name]."],
                replied_store_path=store_path,
                blocked_users=set(),
                bot_username="wise-old-man-bot",
                allow_self_reply=False,
                reply=lambda _: None,
                dry_run=True,
                logger=logger,
                chooser=random.Random(1),
            )

            self.assertTrue(result.did_reply)
            self.assertEqual(result.result, "would_reply")

    def test_cooldown_skip_does_not_post(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "bot_state.sqlite"
            replies: list[str] = []
            logger = logging.getLogger("test-cooldown")
            cooldown = Cooldown(seconds=10, clock=lambda: 100)
            cooldown.mark()

            result = process_comment(
                comment=Comment("hello wise old man", Author("Player")),
                quotes=["Hello, [player name]."],
                replied_store_path=store_path,
                blocked_users=set(),
                bot_username="wise-old-man-bot",
                allow_self_reply=False,
                reply=replies.append,
                dry_run=False,
                logger=logger,
                cooldown=cooldown,
            )

            self.assertFalse(result.did_reply)
            self.assertEqual(result.result, "cooldown")
            self.assertEqual(replies, [])

    def test_already_replied_match_is_quietly_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store_path = Path(directory) / "bot_state.sqlite"
            save_replied_ids(store_path, {"comment123"})
            replies: list[str] = []
            logger = logging.getLogger("test-already-replied")

            with self.assertNoLogs(logger, level="INFO"):
                result = process_comment(
                    comment=Comment("hello wise old man", Author("Player")),
                    quotes=["Hello, [player name]."],
                    replied_store_path=store_path,
                    blocked_users=set(),
                    bot_username="wise-old-man-bot",
                    allow_self_reply=False,
                    reply=replies.append,
                    dry_run=False,
                    logger=logger,
                )

            self.assertFalse(result.did_reply)
            self.assertEqual(result.result, "already_replied")
            self.assertEqual(replies, [])


if __name__ == "__main__":
    unittest.main()
