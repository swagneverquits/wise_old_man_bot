# reddit_reply_bot

Placeholder project for a Reddit reply bot.

## Environment

The preferred local environment is Conda:

```powershell
conda env create -f environment.yml
conda activate reddit-reply-bot
```

If the environment already exists, update it with:

```powershell
conda env update -f environment.yml --prune
```

Miniconda is installed for this user. If `conda` is not available in the current terminal, close and reopen PowerShell so the Conda initialization takes effect.

## Configuration

Create a local `.env` file from the example and fill in Reddit credentials:

```powershell
Copy-Item .env.example .env
```

The bot reads these files by default:

- `quotes.json`
- `blocked_users.json`
- `replied_items.json`

Keep `.env` local. It is ignored by Git.

## Tests

```powershell
conda run -n reddit-reply-bot python -m unittest discover -s tests
```

Current tests cover trigger matching, quote formatting, reply skip decisions, JSON persistence, config loading, data file validation, cooldowns, retries, and structured runtime logs.

## Runtime Helpers

The bot code includes small reliability helpers for:

- Deleted author metadata extraction
- Bot-user and blocked-user skip decisions
- Reply cooldown tracking
- Transient error retry with exponential backoff
- JSON structured reply event logging

## Dry Run

Keep `DRY_RUN=true` in `.env` while validating the bot. In dry-run mode, matched comments and submissions log the intended reply but do not call Reddit and do not write the item ID to `replied_items.json`.

Switch `DRY_RUN=false` only after confirming the logs show the replies you expect.

To validate against Reddit safely:

1. Set `REDDIT_SUBREDDITS=test` and `DRY_RUN=true` in `.env`.
2. Create a post or comment in `https://www.reddit.com/r/test/` that mentions `wise old man`.
3. Run a one-shot poll:

```powershell
conda run -n reddit-reply-bot python -m reddit_reply_bot --limit 25
```

4. Confirm the logs include `dry_run_reply`.
5. Set `DRY_RUN=false` only when ready to test one real reply.
