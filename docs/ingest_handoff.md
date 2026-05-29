# Ingest Handoff Guide

This document records the project-wide workflow for turning attachments or chat-provided user data into the repository's structured JSON stores.

## Goal

- Convert attached menu images/PDFs into structured menu entries
- Convert Discord user details into structured user records
- Preserve the JSON stores as the source of truth
- Avoid duplicate entries when the same date/meal or user is updated later

## Menu Attachment Workflow

When a chat includes a menu image or PDF and asks to "add it", the expected behavior is:

1. Parse the attachment into structured menu data.
2. Save the result into `data/menu.json` using the existing menu ingest flow.
3. Keep `menu_summary` short and stable.
4. Use JST dates.
5. Do not create duplicate entries for the same `date` + `meal`; update the existing entry instead.
6. Regenerate the static site (`index.html`, `calendar.html`, `menu/index.html`) after saving.
7. If the source path is available locally, keep it in `image_path` for provenance.

Recommended command:

```bash
python3 scripts/ingest_menu.py --meal lunch --date 2026-05-29 --text "..." --image-path /path/to/source.pdf
```

If structured data is already known, prefer `--menu-json`.

## User Registry Workflow

When a chat provides a Discord user ID plus name/description and notification preferences, the expected behavior is:

1. Save the record into `data/user_data.json`.
2. Preserve the `user_id` as the unique key.
3. Store the person label in `description`, and optionally `username`, `display_name`, and `aliases`.
4. Store notification subscriptions in `notifications`.
5. Avoid duplicate user records; update the existing `user_id` entry if it already exists.
6. Keep `test_user` explicit when the record is for testing.

Recommended command:

```bash
python3 -m dormitory_bot.user_data --user-id 123456789012345678 --description "秋山さん" --display-name "Akiyama" --notification menu --notification cleaning
```

If the user is only for test sends, add `--test-user`.

## Source of Truth

- Menu data: `data/menu.json`
- User registry: `data/user_data.json`

Raw attachments are only supporting material. The structured JSON stores are the canonical data used by the site and notification code.
