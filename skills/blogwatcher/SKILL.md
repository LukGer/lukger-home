---
name: blogwatcher
description: "Monitor xkcd (or other RSS/Atom feeds) with BlogWatcher and deliver daily updates (image + title) via cron."
---

## Purpose

This skill keeps track of RSS/Atom feeds using the `blogwatcher` CLI. It ships with a ready-made helper (`scripts/daily_xkcd.py`) that:

1. Runs `blogwatcher scan` against the subscribed feeds (xkcd in the default setup).
2. Reads the newest article recorded in `~/.blogwatcher/blogwatcher.db`.
3. Downloads the comic image from the article page and saves it under `skills/blogwatcher/tmp/xkcd_latest.png`.
4. Prints the `IMAGE_PATH` followed by a short summary (title, publication date, link) which cron jobs can forward verbatim.

Use this helper whenever you want to surface the latest comic image + metadata in chat.

## Setup

1. Install Go (1.24+ is required) and run:
   ```bash
   go install github.com/Hyaxia/blogwatcher/cmd/blogwatcher@latest
   ```
   That writes `blogwatcher` to `$GOPATH/bin` / `$HOME/go/bin`.
2. Register any feed you care about:
   ```bash
   ~/go/bin/blogwatcher add "xkcd" https://xkcd.com/rss.xml
   ~/go/bin/blogwatcher scan
   ```
3. Verify the DB (`~/.blogwatcher/blogwatcher.db`) now contains articles.

## Automation

Cron jobs should call `skills/blogwatcher/scripts/daily_xkcd.py`. The helper prints lines such as:

```
IMAGE_PATH: /home/.../skills/blogwatcher/tmp/xkcd_latest.png
xkcd daily update from xkcd: Title
Published: 2026-02-18T05:00:00Z
Link: https://xkcd.com/xxxx/
```

Let the cron target parse this output: upload the image located at `IMAGE_PATH` and post the summary text into the channel. When no new comics were found the helper still reports the latest entry, so you can decide if you want to suppress duplicates.

## Cron example

```
openclaw cron add \
  --schedule 'cron:0 8 * * *|tz=Europe/Vienna' \
  --sessionTarget isolated \
  --delivery '{"mode":"announce","channel":"telegram","to":"-5142684566"}' \
  --payload '{"kind":"agentTurn","message":"Run skills/blogwatcher/scripts/daily_xkcd.py, upload the IMAGE_PATH, and repaste the summary. Mention errors instead of the normal caption.","model":"openai-codex/gpt-5.1-codex-mini"}'
```

The delivery payload keeps the reminder in this chat directly without manual reposts.
