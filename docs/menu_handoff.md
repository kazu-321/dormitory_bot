# Menu Handoff Guide

This document is the canonical reference for future chat sessions working on menu updates.

## Goal

- Keep menu storage structured
- Preserve the current notification format
- Make it easy to add menus in a new chat without rediscovering the workflow
- Keep the project behavior consistent across future changes
- Keep historical menu data available for browsing

## Current Menu Store Schema

`data/menu.json` uses `version: 2`.

Each entry has:

- `date`: `YYYY-MM-DD`
- `meal`: `breakfast`, `lunch`, or `dinner`
- `menu`: structured menu data
- `menu_summary`: compact label used in short listings
- `image_path`: optional reference to the source image
- `extracted_at`: timestamp when the entry was saved

`source` is no longer stored.

### Breakfast / Lunch

```json
{
  "kind": "list",
  "items": [
    "主菜",
    "副菜",
    "汁物"
  ]
}
```

### Dinner

```json
{
  "kind": "dinner",
  "a": "Aセットの主菜",
  "b": "Bセットの主菜",
  "common": [
    "共通メニュー1",
    "共通メニュー2"
  ]
}
```

## Menu Entry Workflow

### Manual add

Add or correct menu entries by parsing the attachment or provided text directly into structured data and updating `data/menu.json`.

If the structure is already known, store it as JSON-shaped `menu` data rather than a free-form blob.

### Automatic behavior

- The store keeps historical entries unless you explicitly delete them.
- If old data still exists, loading the store migrates it to the current structure.
- Saving a menu regenerates the static website at the repository root.
- When a future chat provides an attached image or PDF to add, parse it and upsert the structured result into `data/menu.json` without duplicate `date` + `meal` entries. See [docs/ingest_handoff.md](/home/kazu/dormitory/docs/ingest_handoff.md).

## Website Output

- Root page: `index.html`
- Calendar page: `calendar.html`
- Menu list page: `menu/index.html`
- The pages are static and GitHub Pages compatible.
- The menu list page shows current/future entries.
- The calendar page shows the full history and lets you pick a date to inspect.
- The pages are regenerated automatically whenever `data/menu.json` is saved.

## Notification Behavior

### Menu notifications

- `dormitory_bot.menu_notify` sends only the selected meal by default.
- The notification title is `メニュー`.
- The body uses the current meal only, formatted as:

  - `5/29 (金) お昼ご飯は`
  - followed by a code block containing the menu lines

- For breakfast only, if the previous day lunch included `コーヒー牛乳`, append ` (ｺｰﾋｰ牛乳)` to the end of the code block content.
- Dinner details format:
  - `(A) ...`
  - `(B) ...`
  - common items on separate lines

### Test sending rule

- After any change, send a test notification to test users.
- Do not send to non-test users unless explicitly instructed.
- Scheduled runs still notify all subscribed users.

## Development Policy

### General

- Prefer structured data over free-form blobs.
- Keep `menu.json` and the notification code in sync.
- Update the documentation whenever the menu schema or notification format changes.
- Use JST for menu date decisions.

### Editing

- Use `apply_patch` for manual file edits.
- Keep changes minimal and targeted.
- Do not revert unrelated user changes.

### Validation

- Run `python3 -m py_compile` for touched Python files when practical.
- Use `--dry-run` to inspect notification formatting before sending.
- For any menu change, test-send to the test user set.

## Useful Commands

Inspect the next menu notification locally:

```bash
python3 -m dormitory_bot.menu_notify --meal lunch --dry-run
```

Test-send to test users only:

```bash
./scripts/send_menu.sh --meal lunch --test-users-only
```

Inspect or migrate the store:

```bash
python3 - <<'PY'
from pathlib import Path
from dormitory_bot.store import load_store
print(load_store(Path("data/menu.json")))
PY
```

## Future Changes

When changing the menu flow in a future chat, read this file first and keep it as the source of truth for:

- schema
- notification format
- test-sending policy
- history retention
