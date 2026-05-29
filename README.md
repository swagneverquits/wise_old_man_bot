# Wise Old Man Bot

A Reddit reply bot for Old School RuneScape communities.

The bot polls recent comments and submissions, looks for mentions of `wise old man`, and replies with a random quote from the Wise Old Man NPC. It intentionally ignores compact mentions like `WiseOldMan`, since that often refers to the stats-tracking website rather than the NPC.

## Behavior

- Polls `REDDIT_SUBREDDITS`, currently intended for `2007scape`.
- Checks comment bodies, submission titles, and submission bodies.
- Matches spaced mentions like `wise old man`, case-insensitively.
- Ignores compact forms like `WiseOldMan`, `wiseoldman`, `wise oldman`, and `wiseold man`.
- Picks a random quote from `config/quotes.json`.
- Replaces `[player name]` in quotes with the Reddit author's username.
- Records replied parent item IDs in `data/replied_items.json` so it does not reply twice to the same comment/post.
- Records every matched `wise old man` trigger in `data/match_audit.json`, including skipped tracker-site context and posted-reply metadata.
- Deletes bot replies below the configured low-karma threshold during periodic moderation checks.

## Configuration

Create a local `.env` file from the example:

```powershell
Copy-Item .env.example .env
```

Fill in the Reddit credentials and runtime values:

```env
REDDIT_CLIENT_ID=your-client-id
REDDIT_CLIENT_SECRET=your-client-secret
REDDIT_USERNAME=wise-old-man-bot
REDDIT_PASSWORD=your-reddit-password
REDDIT_USER_AGENT=wise-old-man-bot by u/wise-old-man-bot
REDDIT_SUBREDDITS=2007scape
QUOTES_PATH=config/quotes.json
BLOCKED_USERS_PATH=config/blocked_users.json
REPLIED_ITEMS_PATH=data/replied_items.json
DRY_RUN=true
ALLOW_SELF_REPLY=false
```

Keep `.env` local. It is ignored by Git.

Recommended split:

- Local laptop: `DRY_RUN=true`
- Cloud VM: `DRY_RUN=false`

## State Files

The bot writes runtime state under `data/`.

| File | Purpose |
| --- | --- |
| `data/replied_items.json` | Parent comment/submission IDs the bot has already handled. |
| `data/match_audit.json` | Every current-text trigger and final result, including skipped matches, posted reply IDs/text, and reply karma moderation state. |

These files are ignored by Git. In Docker, `./data` is mounted into the container so state survives rebuilds.

## Local Environment

The local development environment uses Conda:

```powershell
conda env create -f environment.yml
conda activate reddit-reply-bot
```

If the environment already exists:

```powershell
conda env update -f environment.yml --prune
```

Run tests:

```powershell
conda run -n reddit-reply-bot python -m unittest discover -s tests
```

## Dry-Run Testing

Keep `DRY_RUN=true` when testing locally.

Run a one-shot poll:

```powershell
conda run -n reddit-reply-bot python -m reddit_reply_bot --limit 25
```

In dry-run mode, the bot logs intended replies but does not post to Reddit and does not write the parent item ID to `data/replied_items.json`.

## Continuous Mode

Run continuously with 2-minute polling, 10-minute summary logs, and hourly low-karma moderation:

```powershell
conda run -n reddit-reply-bot python -m reddit_reply_bot --loop --interval-seconds 120 --limit 200 --startup-limit 1000 --summary-interval-seconds 600 --moderation-interval-seconds 3600 --low-karma-threshold -3
```

Loop mode does one larger startup scan, then settles into normal polling.

Defaults used in production:

| Option | Value | Meaning |
| --- | --- | --- |
| `--interval-seconds` | `120` | Poll every 2 minutes. |
| `--limit` | `200` | Check 200 recent comments and 200 recent submissions per normal poll. |
| `--startup-limit` | `1000` | Check a larger window on startup. |
| `--summary-interval-seconds` | `600` | Print routine summaries every 10 minutes. |
| `--moderation-interval-seconds` | `3600` | Check bot reply karma once per hour. |
| `--low-karma-threshold` | `-3` | Delete bot replies below this score. |

Summary logs look like:

```text
poll_summary
  polls: 5
  new comments: 4
  new submissions: 1
  replies: 0
```

Interesting events, like actual replies or deleted low-karma replies, are logged immediately.

## Docker

Build and run:

```powershell
docker compose up -d --build
```

Follow logs:

```powershell
docker compose logs -f
```

Check status:

```powershell
docker compose ps
```

Stop:

```powershell
docker compose down
```

The Compose service uses:

```yaml
restart: unless-stopped
```

So Docker restarts the bot after crashes or VM reboots unless it was manually stopped.

## Cloud Update Flow

On the Oracle VM, after pushing local code changes:

```bash
cd ~/reddit_reply_bot
./deploy/restart.sh
```

The helper script pulls the latest code, stops the current container, rebuilds/restarts it, shows container status, and prints recent logs.
