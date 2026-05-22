import os
import unittest
from pathlib import Path
from unittest.mock import patch

from reddit_reply_bot.config import load_config


class ConfigTests(unittest.TestCase):
    def test_loads_required_reddit_credentials(self) -> None:
        env = {
            "REDDIT_CLIENT_ID": "client-id",
            "REDDIT_CLIENT_SECRET": "client-secret",
            "REDDIT_USERNAME": "bot-user",
            "REDDIT_PASSWORD": "password",
            "REDDIT_USER_AGENT": "test-agent",
        }

        with patch.dict(os.environ, env, clear=True):
            config = load_config(load_default_dotenv=False)

        self.assertEqual(config.reddit.client_id, "client-id")
        self.assertEqual(config.reddit.client_secret, "client-secret")
        self.assertEqual(config.reddit.username, "bot-user")
        self.assertEqual(config.reddit.password, "password")
        self.assertEqual(config.reddit.user_agent, "test-agent")

    def test_uses_safe_defaults_for_optional_values(self) -> None:
        env = {
            "REDDIT_CLIENT_ID": "client-id",
            "REDDIT_CLIENT_SECRET": "client-secret",
            "REDDIT_USERNAME": "bot-user",
            "REDDIT_PASSWORD": "password",
            "REDDIT_USER_AGENT": "test-agent",
        }

        with patch.dict(os.environ, env, clear=True):
            config = load_config(load_default_dotenv=False)

        self.assertEqual(config.subreddits, "test")
        self.assertEqual(config.quotes_path, Path("config/quotes.json"))
        self.assertEqual(config.blocked_users_path, Path("config/blocked_users.json"))
        self.assertEqual(config.replied_items_path, Path("data/replied_items.json"))
        self.assertTrue(config.dry_run)
        self.assertFalse(config.allow_self_reply)

    def test_overrides_optional_values(self) -> None:
        env = {
            "REDDIT_CLIENT_ID": "client-id",
            "REDDIT_CLIENT_SECRET": "client-secret",
            "REDDIT_USERNAME": "bot-user",
            "REDDIT_PASSWORD": "password",
            "REDDIT_USER_AGENT": "test-agent",
            "REDDIT_SUBREDDITS": "2007scape+test",
            "QUOTES_PATH": "custom/quotes.json",
            "BLOCKED_USERS_PATH": "custom/blocked_users.json",
            "REPLIED_ITEMS_PATH": "data/replied_items.json",
            "DRY_RUN": "false",
            "ALLOW_SELF_REPLY": "true",
        }

        with patch.dict(os.environ, env, clear=True):
            config = load_config(load_default_dotenv=False)

        self.assertEqual(config.subreddits, "2007scape+test")
        self.assertEqual(config.quotes_path, Path("custom/quotes.json"))
        self.assertEqual(config.blocked_users_path, Path("custom/blocked_users.json"))
        self.assertEqual(config.replied_items_path, Path("data/replied_items.json"))
        self.assertFalse(config.dry_run)
        self.assertTrue(config.allow_self_reply)

    def test_rejects_missing_required_credentials(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "REDDIT_CLIENT_ID"):
                load_config(load_default_dotenv=False)


if __name__ == "__main__":
    unittest.main()
