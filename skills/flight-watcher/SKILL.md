---
name: flight-watcher
description: "Daily flight scouting for Vienna → Tokyo (Haneda/Narita) via Kiwi Tequila, filtering layovers and carriers."
---

## Purpose

This skill tracks Vienna → Tokyo roundtrips (depart 10 Sep, return 1 Oct, up to 1 stop, layovers under 5 h, no major Chinese carriers). It calls Kiwi’s Tequila flight search API and summarizes the top three itineraries plus whether the best price changed.

## Helper script

- `scripts/monitor_flights.py`:
  1. Reads `tequila_api_key` from `private_config.json` (you still keep all secrets out of git).
  2. Queries `https://tequila-api.kiwi.com/v2/search` for both Haneda and Narita.
  3. Filters results for `max_stopovers=1`, layovers <= 5 h, and excludes Chinese carriers (CA, MU, CZ, HU, ZH, FM, NX, KN, EY).
  4. Prints a note on the best price (new vs unchanged) plus the formatted top three itineraries (each lists price, airline legs, layovers).
  5. Stores the best price in `~/.openclaw/workspace/.flight_watcher_state.json` so the next run can mention “No change.”

If the Tequila API request fails (e.g., due to missing key), the script exits with an error message so the cron job can report it.

## Configuration

1. Grab a Kiwi Tequila API key at https://tequila.kiwi.com/portal/sign-up (if you can’t find the signup button, use the “Try Tequila for free” flow after logging in at kiwi.com). Store it in `~/.openclaw/workspace/private_config.json` as `"tequila_api_key": "<your key>"`.
2. The script uses your existing `rapidapi_key` (if you ever want to switch to the RapidAPI wrapper) but relies on `tequila_api_key` for now.

## Automation

Create a cron job to run the helper every day around noon (Europe/Vienna) and deliver the text directly into this Telegram chat:

```
openclaw cron add \
  --schedule 'cron:0 12 * * *|tz=Europe/Vienna' \
  --sessionTarget isolated \
  --delivery '{"mode":"announce","channel":"telegram","to":"-5142684566"}' \
  --payload '{"kind":"agentTurn","message":"Run skills/flight-watcher/scripts/monitor_flights.py and post its stdout verbatim into the group so I get the latest top 3 itineraries and notes on whether the price changed.","model":"openai-codex/gpt-5.1-codex-mini"}'
```

The helper prints a multi-line summary that is sent exactly as-is, so you see the best options and know if there’s a new record low. Adjust the script if you want to include more destinations or different dates.
