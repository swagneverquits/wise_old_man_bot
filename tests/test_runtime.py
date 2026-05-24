import logging
import unittest

from reddit_reply_bot.runtime import (
    Cooldown,
    RedditItemMetadata,
    extract_item_metadata,
    log_reply_event,
    retry_with_backoff,
)


class Author:
    def __init__(self, name: str) -> None:
        self.name = name


class Item:
    id = "abc123"
    subreddit = "test"

    def __init__(self, author: Author | None) -> None:
        self.author = author


class RuntimeTests(unittest.TestCase):
    def test_cooldown_starts_ready(self) -> None:
        cooldown = Cooldown(seconds=10, clock=lambda: 100)

        self.assertTrue(cooldown.ready())

    def test_cooldown_blocks_until_elapsed(self) -> None:
        now = 100
        cooldown = Cooldown(seconds=10, clock=lambda: now)

        cooldown.mark()

        self.assertFalse(cooldown.ready())

    def test_cooldown_allows_after_elapsed(self) -> None:
        times = [100]
        cooldown = Cooldown(seconds=10, clock=lambda: times[0])

        cooldown.mark()
        times[0] = 111

        self.assertTrue(cooldown.ready())

    def test_extracts_metadata_with_author(self) -> None:
        metadata = extract_item_metadata(Item(Author("Player")), "comment")

        self.assertEqual(metadata.item_id, "abc123")
        self.assertEqual(metadata.username, "Player")
        self.assertEqual(metadata.subreddit, "test")
        self.assertEqual(metadata.kind, "comment")

    def test_extracts_deleted_author_metadata(self) -> None:
        metadata = extract_item_metadata(Item(None), "submission")

        self.assertEqual(metadata.username, "[deleted]")

    def test_retry_with_backoff_retries_transient_error(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def operation() -> str:
            nonlocal calls
            calls += 1
            if calls < 3:
                raise TimeoutError("temporary")
            return "ok"

        result = retry_with_backoff(
            operation,
            retry_exceptions=(TimeoutError,),
            attempts=3,
            initial_delay_seconds=2,
            sleep=sleeps.append,
        )

        self.assertEqual(result, "ok")
        self.assertEqual(sleeps, [2, 4])

    def test_retry_with_backoff_raises_after_final_attempt(self) -> None:
        with self.assertRaises(TimeoutError):
            retry_with_backoff(
                lambda: (_ for _ in ()).throw(TimeoutError("temporary")),
                retry_exceptions=(TimeoutError,),
                attempts=2,
                initial_delay_seconds=1,
                sleep=lambda _: None,
            )

    def test_logs_reply_event_in_readable_format(self) -> None:
        logger = logging.getLogger("test-runtime-log")
        metadata = RedditItemMetadata(
            item_id="abc123",
            username="Player",
            subreddit="test",
            kind="comment",
        )

        with self.assertLogs(logger, level="INFO") as captured:
            log_reply_event(logger, "reply_attempt", metadata, "posted")

        message = captured.records[0].getMessage()

        self.assertEqual(
            message,
            "reply_attempt result=posted kind=comment item_id=abc123 subreddit=test username=Player",
        )


if __name__ == "__main__":
    unittest.main()
