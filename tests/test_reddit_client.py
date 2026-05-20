import unittest
from unittest.mock import patch

from reddit_reply_bot.config import RedditConfig
from reddit_reply_bot.reddit_client import create_reddit_client


class RedditClientTests(unittest.TestCase):
    def test_creates_authenticated_praw_client(self) -> None:
        config = RedditConfig(
            client_id="client-id",
            client_secret="client-secret",
            username="bot-user",
            password="password",
            user_agent="agent",
        )

        with patch("reddit_reply_bot.reddit_client.praw.Reddit") as reddit:
            create_reddit_client(config)

        reddit.assert_called_once_with(
            client_id="client-id",
            client_secret="client-secret",
            username="bot-user",
            password="password",
            user_agent="agent",
        )


if __name__ == "__main__":
    unittest.main()

