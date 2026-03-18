---
name: gog
description: Google Workspace CLI for Gmail, Calendar, Drive, Contacts, Sheets, and Docs.
homepage: https://gogcli.sh
metadata: {"clawdbot":{"emoji":"🎮","requires":{"bins":["gog"]},"install":[{"id":"brew","kind":"brew","formula":"steipete/tap/gogcli","bins":["gog"],"label":"Install gog (brew)"}]}}
---

# gog

Google Workspace CLI for Gmail, Calendar, Drive, Contacts, Sheets, and Docs.

**IMPORTANT — always pass `--no-input` to every `gog` command.** The agent runs
headless; interactive prompts will hang. `GOG_ACCOUNT`, `GOG_KEYRING_PASSWORD`,
and `GOG_KEYRING_BACKEND=file` are pre-set in the environment — never prompt the
user for them.

## Configuration

OAuth credentials and keyring are provisioned by Ansible. Manual setup (once on host):

```
gog auth keyring file
gog auth credentials set /path/to/client_secret.json --force
gog auth add you@gmail.com --services gmail,calendar,drive,contacts,sheets,docs --manual --force-consent
```

## Commands

All examples below include `--no-input`. Always use it.

- Gmail search: `gog gmail search 'newer_than:7d' --max 10 --no-input`
- Gmail send: `gog gmail send --to a@b.com --subject "Hi" --body "Hello" --no-input`
- Calendar: `gog calendar events <calendarId> --from <iso> --to <iso> --no-input`
- Drive search: `gog drive search "query" --max 10 --no-input`
- Contacts: `gog contacts list --max 20 --no-input`
- Sheets get: `gog sheets get <sheetId> "Tab!A1:D10" --json --no-input`
- Sheets update: `gog sheets update <sheetId> "Tab!A1:B2" --values-json '[["A","B"],["1","2"]]' --input USER_ENTERED --no-input`
- Sheets append: `gog sheets append <sheetId> "Tab!A:C" --values-json '[["x","y","z"]]' --insert INSERT_ROWS --no-input`
- Sheets clear: `gog sheets clear <sheetId> "Tab!A2:Z" --no-input`
- Sheets metadata: `gog sheets metadata <sheetId> --json --no-input`
- Docs export: `gog docs export <docId> --format txt --out /tmp/doc.txt --no-input`
- Docs cat: `gog docs cat <docId> --no-input`

## Notes

- `GOG_ACCOUNT` is set — no need for `--account`.
- Prefer `--json` for machine-readable output.
- Sheets values: use `--values-json` (recommended) or inline rows.
- Docs: export/cat/copy only. In-place edits need a Docs API client.
- Confirm with the user before sending mail or creating events.
