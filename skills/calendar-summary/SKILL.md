---
name: calendar-summary
description: "Summarize upcoming calendar events using the gog CLI (all calendars). Use when asked to provide daily/weekly calendar summaries or to run the calendar summary script."
---

# Calendar Summary

Use the bundled script to generate a plain-language summary of tomorrow’s events.

## Run the summary

```bash
python3 scripts/tomorrow_events.py
```

The script:
- Queries all calendars via `gog calendar events --all`.
- Outputs a human summary without locations, timezones, or meeting links.
- Skips week-number calendars.
