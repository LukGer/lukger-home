---
name: flight-watcher
description: "Daily flight scouting for Vienna → Tokyo (Haneda/Narita) via the RapidAPI Kiwi.com Cheap Flights round-trip search."
---

## Purpose

This skill tracks Vienna → Tokyo roundtrips (depart 10 Sep, return 1 Oct, up to 1 stop, layovers under 5 h, no major Chinese carriers) and pushes the top three itineraries into the Telegram group. It now talks to the RapidAPI “Kiwi.com Cheap Flights” round-trip endpoint instead of Tequila so we can keep the daily noon summary alive.

## Helper script

- `scripts/monitor_flights.py`:
  1. Reads `rapidapi_key` from `private_config.json` and targets the RapidAPI host `kiwi-com-cheap-flights.p.rapidapi.com`.
  2. Calls `https://kiwi-com-cheap-flights.p.rapidapi.com/round-trip` twice (Haneda and Narita) with the September 10 → October 1 roundtrip parameters + the filters/flags the previous Tequila version used.
  3. Parses each itinerary, rejects routes with excluded carriers (CA, MU, CZ, HU, ZH, FM, NX, KN, EY) or layovers longer than 5 h, and keeps the best offers for summary.
  4. Prints the best-price note (new vs. unchanged) and the top three itineraries (price, total max layover, outbound/inbound legs with times) just like before.
  5. Saves the latest best price in `~/.openclaw/workspace/.flight_watcher_state.json` so the output can still report “No change.”

If the RapidAPI call fails (e.g., due to a missing key), the script exits with an error message so the cron job can report it.

## Configuration

1. Add your RapidAPI key to `~/.openclaw/workspace/private_config.json` under `"rapidapi_key": "<your key>"`.
2. Confirm the key has access to the `kiwi-com-cheap-flights.p.rapidapi.com` API (the “Round trip” endpoint, `GET /round-trip`).

## Automation

(The cron payload below already targets the updated script.)

```
openclaw cron add \
  --schedule 'cron:0 12 * * *|tz=Europe/Vienna' \
  --sessionTarget isolated \
  --delivery '{"mode":"announce","channel":"telegram","to":"-5142684566"}' \
  --payload '{"kind":"agentTurn","message":"Run skills/flight-watcher/scripts/monitor_flights.py and post its stdout verbatim into the group so I get the latest top 3 itineraries and notes on whether the price changed.","model":"openai-codex/gpt-5.1-codex-mini"}'
```

The helper still prints the same structured summary, and the cron job delivers it directly into the Telegram group so you see the best options and whether the price moved.