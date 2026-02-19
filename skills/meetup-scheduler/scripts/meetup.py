#!/usr/bin/env python3
"""Helper for the meetup-scheduler skill.

Usage examples:
  python skills/meetup-scheduler/scripts/meetup.py --destination "Irish Pub" --arrival "2026-02-19T19:00"
  python ... --mode driving --origin "work" --buffer 10 --json
"""

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CONFIG_ENV_VAR = "MEETUP_SCHEDULER_CONFIG"
DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "private_config.json"
DEFAULT_TIMEZONE = "Europe/Vienna"

API_URL = "https://maps.googleapis.com/maps/api/directions/json"


class MeetupSchedulerError(RuntimeError):
    pass


def load_config(path=None):
    config_path = Path(path or os.environ.get(CONFIG_ENV_VAR) or DEFAULT_CONFIG)
    if not config_path.exists():
        raise MeetupSchedulerError(f"config file not found at {config_path}")
    data = json.loads(config_path.read_text())
    if "google_maps_api_key" not in data or "home_address" not in data:
        raise MeetupSchedulerError("config needs google_maps_api_key and home_address keys")
    return data


def parse_arrival(raw: str, tz: ZoneInfo) -> datetime:
    text = raw.strip()
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%H:%M"):
        try:
            parsed = datetime.strptime(text, fmt)
            if fmt == "%H:%M":
                today = datetime.now(tz).date()
                parsed = datetime.combine(today, parsed.time())
            return parsed.replace(tzinfo=tz)
        except ValueError:
            continue
    raise MeetupSchedulerError(f"could not parse arrival time: {raw}")


def fetch_directions(origin, destination, mode, arrival_ts, api_key):
    params = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "language": "en",
        "key": api_key,
        # let the API choose the best transit routing for arrival time
    }
    if arrival_ts:
        params["arrival_time"] = str(arrival_ts)
    else:
        params["departure_time"] = str(int(time.time()))
    encoded = urllib.parse.urlencode(params, safe=":,/")
    url = f"{API_URL}?{encoded}"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            data = json.load(response)
    except urllib.error.URLError as exc:
        raise MeetupSchedulerError(f"could not reach Directions API: {exc}")
    if data.get("status") != "OK":
        raise MeetupSchedulerError(f"Directions API error: {data.get('status')} - {data.get('error_message')}")
    routes = data.get("routes", [])
    if not routes:
        raise MeetupSchedulerError("no routes returned by Directions API")
    return routes[0]


def summarize_leg(leg):
    duration = leg.get("duration", {}).get("value")
    steps = []
    for step in leg.get("steps", [])[:4]:
        instruction = step.get("html_instructions", "").replace("<div style=\"font-size:0.9em\">", " ").replace("</div>", "")
        # strip remaining tags
        stripped = "".join(ch for ch in instruction if ch != "<" and ch != ">")
        steps.append(stripped)
    departure = leg.get("departure_time", {}).get("text")
    arrival = leg.get("arrival_time", {}).get("text")
    return {
        "duration_seconds": duration,
        "distance_text": leg.get("distance", {}).get("text"),
        "departure_text": departure,
        "arrival_text": arrival,
        "instructions": steps,
        "summary": leg.get("summary"),
    }


def plan_trip(destination, arrival, origin=None, mode="transit", buffer_minutes=5, config=None):
    config = config or load_config()
    origin = origin or config["home_address"]
    tz = ZoneInfo(config.get("timezone", DEFAULT_TIMEZONE))
    arrival_dt = parse_arrival(arrival, tz)
    arrival_ts = int(arrival_dt.timestamp())
    route = fetch_directions(origin, destination, mode, arrival_ts, config["google_maps_api_key"])
    leg = route.get("legs", [])[0]
    summary = summarize_leg(leg)
    travel_seconds = summary["duration_seconds"] or 0
    leave_dt = arrival_dt - timedelta(seconds=travel_seconds + buffer_minutes * 60)
    payload = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "arrival_time": arrival_dt.isoformat(sep=" "),
        "arrival_time_local": arrival_dt.strftime("%H:%M"),
        "buffer_minutes": buffer_minutes,
        "travel_minutes": round(travel_seconds / 60) if travel_seconds else None,
        "departure_time": leave_dt.isoformat(sep=" "),
        "departure_time_utc": leave_dt.astimezone(timezone.utc).isoformat(),
        "departure_time_local": leave_dt.strftime("%H:%M"),
        "local_timezone": tz.key,
        "summary": summary,
    }
    return payload


def format_payload(payload):
    lines = [
        f"origin: {payload['origin']}",
        f"destination: {payload['destination']}",
        f"arrival: {payload['arrival_time']} ({payload['local_timezone']})",
        f"mode: {payload['mode']}",
        f"buffer: {payload['buffer_minutes']} min",
        f"travel: {payload['travel_minutes']} min",
        f"leave at: {payload['departure_time']}"
    ]
    summary = payload["summary"]
    if summary["summary"]:
        lines.append(f"route: {summary['summary']}")
    if summary["departure_text"]:
        lines.append(f"scheduled departure: {summary['departure_text']}")
    if summary["arrival_text"]:
        lines.append(f"expected arrival: {summary['arrival_text']}")
    if summary["instructions"]:
        lines.append("first legs:")
        lines.extend(f"  • {inst}" for inst in summary["instructions"])
    return "\n".join(lines)


def format_brief(payload):
    return (
        f"Leave at {payload['departure_time_local']} ({payload['local_timezone']}) "
        f"via {payload['mode']} to reach {payload['destination']} by {payload['arrival_time_local']} "
        f"(≈{payload['travel_minutes']} min)."
    )


def main():
    parser = argparse.ArgumentParser(description="Fetch travel data for meetups")
    parser.add_argument("--destination", required=True, help="Where Lukas wants to go")
    parser.add_argument("--arrival", required=True, help="Target arrival time (ISO or HH:MM)")
    parser.add_argument("--origin", help="Fallback origin (defaults to home in config)")
    parser.add_argument("--mode", choices=["transit", "driving", "walking", "bicycling"], default="transit")
    parser.add_argument("--buffer", type=int, default=5, help="Minutes of buffer before travel begins")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of human summary")
    parser.add_argument("--brief", action="store_true", help="Print a short human-friendly summary")
    args = parser.parse_args()

    try:
        payload = plan_trip(
            destination=args.destination,
            arrival=args.arrival,
            origin=args.origin,
            mode=args.mode,
            buffer_minutes=args.buffer,
        )
    except MeetupSchedulerError as exc:
        parser.error(str(exc))

    if args.json:
        print(json.dumps(payload, indent=2))
    elif args.brief:
        print(format_brief(payload))
    else:
        print(format_payload(payload))


if __name__ == "__main__":
    main()
