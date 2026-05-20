import logging
import tempfile
import unittest
from pathlib import Path

from reddit_reply_bot.runner import poll_subreddit, run_loop
from reddit_reply_bot.runtime import Cooldown
from reddit_reply_bot.storage import load_replied_ids


class Author:
    def __init__(self, name: str) -> None:
        self.name = name


class Comment:
    id = "comment123"
    subreddit = "test"

    def __init__(self) -> None:
        self.author = Author("Player")
        self.body = "wise old man"
        self.replies: list[str] = []

    def reply(self, text: str) -> None:
        self.replies.append(text)


class Submission:
    id = "submission123"
    subreddit = "test"

    def __init__(self) -> None:
        self.author = Author("OtherPlayer")
        self.title = "ordinary title"
        self.selftext = "wise old man in the body"
        self.replies: list[str] = []

    def reply(self, text: str) -> None:
        self.replies.append(text)


class Subreddit:
    def __init__(self, comments: list[Comment], submissions: list[Submission]) -> None:
        self._comments = comments
        self._submissions = submissions

    def comments(self, limit: int):
        return self._comments[:limit]

    def new(self, limit: int):
        return self._submissions[:limit]


class RunnerTests(unittest.TestCase):
    def test_poll_subreddit_processes_comments_and_submissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            comment = Comment()
            submission = Submission()
            store_path = Path(directory) / "replied_items.json"

            poll_subreddit(
                subreddit=Subreddit([comment], [submission]),
                limit=50,
                quotes=["Hello, [player name]."],
                replied_store_path=store_path,
                blocked_users=set(),
                bot_username="wise-old-man-bot",
                allow_self_reply=False,
                dry_run=False,
                cooldown=Cooldown(seconds=0),
                logger=logging.getLogger("test-runner-poll"),
            )

            self.assertEqual(comment.replies, ["Hello, Player."])
            self.assertEqual(submission.replies, ["Hello, OtherPlayer."])
            self.assertEqual(load_replied_ids(store_path), {"comment123", "submission123"})

    def test_loop_stops_on_keyboard_interrupt(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def poll_once() -> None:
            nonlocal calls
            calls += 1

        def sleep(_: float) -> None:
            sleeps.append(_)
            raise KeyboardInterrupt

        run_loop(
            poll_once,
            interval_seconds=300,
            logger=logging.getLogger("test-runner-loop"),
            sleep=sleep,
        )

        self.assertEqual(calls, 1)
        self.assertEqual(sleeps, [300])

    def test_loop_rejects_non_positive_interval(self) -> None:
        with self.assertRaises(ValueError):
            run_loop(
                lambda: None,
                interval_seconds=0,
                logger=logging.getLogger("test-runner-loop"),
            )


if __name__ == "__main__":
    unittest.main()

