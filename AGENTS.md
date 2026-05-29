# AGENTS.md

This is the primary Codex operating document for this repository.

If you are about to touch menu behavior, read [docs/menu_handoff.md](/home/kazu/dormitory/docs/menu_handoff.md) immediately after this file.

## Operating Principles

- Prefer structured data over free-form text.
- Make the smallest change that satisfies the request.
- Keep behavior explicit and documented.
- Preserve user edits unless the task directly requires changing them.
- Use `apply_patch` for manual file edits.
- Use non-interactive commands and avoid destructive git operations.
- Run `python3 -m py_compile` on touched Python files when practical.

## Repository Mental Model

- This project stores dormitory menu data locally and sends Discord DM notifications.
- In this project, "notification" means a DM to a Discord `user_id`.
- Menu state lives in `data/menu.json`.
- Static website output lives at the repository root (`index.html`, `calendar.html`, and `menu/index.html`).
- User notification preferences live in `data/user_data.json`.
- Scheduled behavior is cron-driven; the scripts in `scripts/` are what cron calls.

## Menu Rules

- `data/menu.json` is the source of truth for menu data.
- The current schema is documented in [docs/menu_handoff.md](/home/kazu/dormitory/docs/menu_handoff.md).
- `source` is no longer part of the menu schema.
- Store structured menu data in `menu`, not a raw free-form blob.
- Keep `menu_summary` short and stable.
- Keep historical menu entries unless the user explicitly asks to delete them.
- Keep menu dates JST-based.
- Regenerate `index.html`, `calendar.html`, and `menu/index.html` whenever the menu store is saved.
- `menu/index.html` is the current/future list, while `calendar.html` is the history browser.
- Keep the generated site GitHub Pages compatible from the repository root.

## Notification Rules

- After any menu-related change, send a test notification to test users.
- Do not send to non-test users unless the user explicitly asks for that.
- Scheduled notifications still go to all subscribed users.
- If a change affects notification output, verify it with `--dry-run` first when possible.
- For menu changes, test-send the actual notification after validation.

## File Guidance

- [README.md](/home/kazu/dormitory/README.md): short human-facing overview.
- [docs/menu_handoff.md](/home/kazu/dormitory/docs/menu_handoff.md): full menu schema and workflow.
- `dormitory_bot/store.py`: menu storage, migration, parsing, summary helpers.
- `dormitory_bot/menu_site.py`: static site generation for GitHub Pages.
- `dormitory_bot/ingest.py`: add or correct menu entries.
- `dormitory_bot/menu_notify.py`: build and send menu notifications.

## Change Workflow

1. Read this file.
2. Read [docs/menu_handoff.md](/home/kazu/dormitory/docs/menu_handoff.md) if the task touches menus.
3. Inspect the current code before editing.
4. Edit the smallest set of files needed.
5. Run syntax checks or dry-runs.
6. Send a test notification to test users for menu-related changes.
7. Summarize what changed and what was verified.

## Menu Additions

When adding or correcting a menu entry:

- Use `dormitory_bot.ingest`.
- Prefer structured `menu` data.
- Use `--menu-json` when the structure is already known.
- Use `--text` only as the source input to be parsed into structure.
- Let the tool compute `menu_summary` unless the user explicitly provides one.

## Escalation

- Ask the user only when the choice is genuinely ambiguous or has hidden tradeoffs.
- If the user requests a test send, do it.
- If the user requests a rule change, update both code and the handoff docs.

## Reference

- [docs/menu_handoff.md](/home/kazu/dormitory/docs/menu_handoff.md)
- [README.md](/home/kazu/dormitory/README.md)
