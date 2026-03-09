#!/usr/bin/env python3
import json
import os
import subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TIMEZONE = "Europe/Vienna"


def run_gog(from_dt: datetime, to_dt: datetime) -> list[dict]:
    gog_bin = os.environ.get("GOG_BIN", "gog")
    cmd = [
        gog_bin,
        "calendar",
        "events",
        "--all",
        "--account",
        os.environ.get("GOG_ACCOUNT", "lukger1999@gmail.com"),
        "--from",
        from_dt.isoformat(),
        "--to",
        to_dt.isoformat(),
        "--max",
        "200",
        "--json",
    ]
    env = os.environ.copy()
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "gog calendar events failed")
    payload = json.loads(result.stdout)
    return payload.get("events", [])


def is_week_number_event(event: dict) -> bool:
    summary = (event.get("summary") or "").lower()
    organizer = (event.get("organizer", {}) or {}).get("email", "").lower()
    return "week" in summary or "kalenderwoche" in summary or "weeknum" in organizer


def format_event(event: dict, tz: ZoneInfo) -> str:
    summary = event.get("summary", "(no title)")
    start = event.get("start", {})
    end = event.get("end", {})
    if "date" in start:
        return f"All day — {summary}"
    start_dt = datetime.fromisoformat(start.get("dateTime"))
    end_dt = datetime.fromisoformat(end.get("dateTime"))
    start_local = start_dt.astimezone(tz)
    end_local = end_dt.astimezone(tz)
    return f"{start_local:%H:%M}–{end_local:%H:%M} — {summary}"


def main() -> int:
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    tomorrow = (now + timedelta(days=1)).date()
    start = datetime.combine(tomorrow, datetime.min.time(), tzinfo=tz)
    end = start + timedelta(days=1)
    try:
        events = run_gog(start, end)
    except Exception as exc:
        print(f"Failed to fetch events: {exc}")
        return 1
    filtered = [e for e in events if not is_week_number_event(e)]
    if not filtered:
        print(f"No events tomorrow ({tomorrow:%a, %b %d}).")
        return 0
    lines = [f"Tomorrow ({tomorrow:%a, %b %d}):"]
    for event in sorted(filtered, key=lambda e: e.get("start", {}).get("dateTime") or e.get("start", {}).get("date", "")):
        lines.append(f"- {format_event(event, tz)}")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
