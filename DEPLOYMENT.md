# Deployment Guide

This bot is best deployed as a small long-running process on a Linux VPS. It does not need much CPU or memory. The important parts are stable internet, persistent state, logs, and keeping `.env` off GitHub.

## Recommended Server

A small Ubuntu LTS VPS is enough:

- 1 vCPU
- 512 MB to 1 GB RAM
- 5 GB or more disk
- SSH access

## Production Command

The intended continuous command is:

```bash
conda run --no-capture-output -n reddit-reply-bot python -m reddit_reply_bot --loop --interval-seconds 300 --limit 50
```

That polls every 5 minutes, checks recent comments and submissions, skips duplicates using `replied_items.json`, and keeps running until stopped.

## Server Setup

Create a dedicated user:

```bash
sudo adduser --disabled-password --gecos "" redditbot
sudo su - redditbot
```

Install Miniconda for that user from Anaconda's official installer, then reopen the shell or source the Conda profile.

Clone the repo:

```bash
git clone https://github.com/limichael0/reddit_reply_bot.git /opt/reddit_reply_bot
cd /opt/reddit_reply_bot
```

If `/opt/reddit_reply_bot` is owned by root, give the bot user ownership:

```bash
sudo chown -R redditbot:redditbot /opt/reddit_reply_bot
```

Create the environment:

```bash
conda env create -f environment.yml
```

Create the local `.env` file manually on the server:

```bash
cp .env.example .env
nano .env
```

Keep `DRY_RUN=true` for the first server run.

## Dry-Run Validation

Run this manually before installing the service:

```bash
conda run --no-capture-output -n reddit-reply-bot python -m reddit_reply_bot --loop --interval-seconds 300 --limit 50
```

Watch the logs for:

- `starting_bot`
- `reply_skip`
- `dry_run_reply`

Stop it with `Ctrl+C`. Only switch `DRY_RUN=false` after dry-run logs look correct.

## systemd Service

Copy the example service:

```bash
sudo cp deploy/reddit-reply-bot.service.example /etc/systemd/system/reddit-reply-bot.service
```

Edit paths if your repo or Conda install is somewhere else:

```bash
sudo nano /etc/systemd/system/reddit-reply-bot.service
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable reddit-reply-bot
sudo systemctl start reddit-reply-bot
```

Check status:

```bash
sudo systemctl status reddit-reply-bot
```

Follow logs:

```bash
journalctl -u reddit-reply-bot -f
```

Stop the bot:

```bash
sudo systemctl stop reddit-reply-bot
```

## Updates

Pull code and restart:

```bash
cd /opt/reddit_reply_bot
git pull
conda env update -f environment.yml --prune
sudo systemctl restart reddit-reply-bot
```

## State And Secrets

Do not commit these:

- `.env`
- `replied_items.json`

The `.env` file contains Reddit credentials. The `replied_items.json` file is local runtime state that prevents duplicate replies across restarts.

