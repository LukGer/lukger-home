---
name: meetup-scheduler
description: "Plan real-world meetups by gathering destination/time/mode, using Google Directions to compute travel duration, determining when Lukas needs to leave, and scheduling a reminder shortly before departure."
---

## Purpose

Use this skill whenever Lukas asks for help organising a real-life meetup-"meet at a pub at 19:00", "grab drinks with friends downtown", "I want to be at the museum by 6"-especially when the request implies travel planning. The skill always: (1) clarifies missing basics (origin, destination, timing, transport preferences), (2) defaults to Lukas's home address and public transport when unspecified, (3) consults Google Directions, (4) derives the latest safe departure time (travel duration plus a buffer), and (5) schedules a reminder via cron so Lukas gets a heads-up before he needs to leave.

## Trigger cues

- "Help me plan a meetup at..."
- "I want to get to <place> by <time>."
- "Schedule a meetup / meet some friends / go to the pub / I need to be somewhere."
- Anything that references a real-world meeting, arrival time, or needing travel guidance.

## Workflow
1. **Gather the requirements.** Confirm or ask for:
   - Destination (validate it parses as an address; if it resolves to a landmark, keep user language for the reminder text).
   - Arrival time (target when Lukas wants to be there; parse into ISO or HH:MM for the current day).
   - Origin (default to home but ask if he meant somewhere else or is already "at" a place). For future flexibility, store his home address in memory.
   - Mode of transport (default to public transport unless he explicitly says drive/walk/bike).
   - Any safety buffer he wants (5 min default before the transit/drive start).

2. **Run the helper script.** Use `scripts/meetup.py` with the gathered inputs (destination, arrival time, origin, mode, buffer) to fetch the current route from the Google Directions API. The script returns:
   - Travel duration in minutes
   - The moment he should leave (arrival minus duration minus buffer)
   - Step-by-step instructions for the first leg(s)
   - Which line/stop the reminder references when public transit is in use

3. **Review the suggested plan with Lukas.** Share:
   - Calculated departure time and buffer
   - Expected total travel duration
   - First departure (tram/bus stop, driving directions) so he knows what to expect
   - Mention that the reminder will arrive ~5 minutes before he must leave (or whatever buffer he asked for)

4. **Schedule the reminder.** When Lukas approves the plan:
   - Use the `cron` tool (see documentation) to add a job firing at the computed leave time.
   - The reminder payload should mention: "Leave now for <destination> via <mode>; it takes ~<duration> and you should catch <next transit info>". Include the first action (e.g., "Walk to the tram stop at Linz Hauptplatz, catch tram 2 towards Leonding West").
   - Store the job ID or description in conversation memory if follow-up/cancellation might happen soon.

5. **Handle follow-ups.** Lukas might later ask "cancel that reminder", "I changed my mind to drive", or "update the meetup to 19:30". Re-run the script with the new parameters, cancel the old cron job if needed, and schedule a new reminder.

## Helper script

### `scripts/meetup.py`

The script lives inside this skill. It exposes a command-line interface so Codex can ask: `python skills/meetup-scheduler/scripts/meetup.py --destination "Irish Pub" --arrival "2026-02-20T19:00"`.

- **Inputs**: `--destination`, `--arrival` (ISO or HH:MM), optional `--origin`, `--mode` (`transit, driving, walking, bicycling`), `--buffer` (minutes before departure), `--json` (print machine-readable data).
- **Outputs**: JSON summarising travel duration, computed departure time, and first-leg instructions. The CLI also pretty-prints the details if `--json` is omitted.
- **Implementation notes**:
  - It reads `google_maps_api_key` and `home_address` from `private_config.json` (see Configuration). This keeps secrets outside the repo.
  - It defaults to transit/rides from home when the corresponding arguments aren't present.
  - It uses standard library `urllib` so no extra dependencies are needed.

## Configuration

1. Create (or update) a `private_config.json` in the repo root (not checked in). It must contain:
   ```json
   {
     "google_maps_api_key": "<your key>",
     "home_address": "<Lukas' home address>"
   }
   ```
2. If you keep your config elsewhere, point the script to it via `MEETUP_SCHEDULER_CONFIG=/path/to/private_config.json python ...`.
3. Keep the API key secret; only store it in private files or environment variables.

## Reminder Cadence

- Reminders go out once, a fixed buffer before the computed departure time.
- If Lukas needs multiple nudges (e.g., an earlier "start packing" message), add another cron job with a different `leave_in` window but reference the same itinerary.
- When plans change, cancel outdated cron jobs via the `cron` tool before adding new ones.

## After the reminder fires

Let Lukas know the reminder text and confirm he made it. If he enjoyed the experience, summarise the travel time and whether the transit plan matched reality-these insights will help refine future suggestions.
