# Dormitory Bot

This project stores dormitory meal data locally and sends Discord bot DMs for the notifications each user has subscribed to.

In this project, "notification" means the Discord bot sending a DM to the target user's numeric `user_id`.

## Files

- `dormitory_bot/ingest.py`: save transcribed menu text into `data/menu.json`
- `dormitory_bot/user_data.py`: save users, descriptions, aliases, and notification subscriptions into `data/user_data.json`
- `dormitory_bot/menu_notify.py`: send meal notifications to every user subscribed to `menu`
- `dormitory_bot/cleaning_notify.py`: send the "掃除が始まります" reminder to every user subscribed to `cleaning`
- `dormitory_bot/cleaning_rotation_notify.py`: send the weekly cleaning turn reminder to every user subscribed to `cleaning_rotation`
- `dormitory_bot/cleaning_rotation.py`: keep the cleaning turn rotation in `data/cleaning_rotation.json`

## Schedule

Use these times with cron, Task Scheduler, or any external scheduler:

- Weekdays: breakfast `07:30`, lunch `12:10`, dinner `18:00`
- Weekends: breakfast `08:00`, lunch `12:00`, dinner `18:00`
- Cleaning start: every Thursday `20:00` for the `20:10` cleaning start
- Cleaning rotation: every Thursday `20:00` for the weekly turn reminder

## Save a menu

Images are interpreted in chat by the assistant, then the extracted text is saved locally.
If you want to add or correct an entry manually, use:

```bash
python3 -m dormitory_bot.ingest --meal lunch --text "ごはん\n味噌汁\n唐揚げ"
```

You can keep the original image path for reference:

```bash
python3 -m dormitory_bot.ingest --meal lunch --image-path /path/to/menu.jpg --text "..."
```

## User data

The user store lives in [`data/user_data.json`](/home/kazu/dormitory/data/user_data.json).
It keeps:

- `user_id`: the Discord user ID used for DM delivery
- `description`: a short note for identifying the person later
- `aliases`: nicknames or other names you want to remember
- `test_user`: whether the user should receive test-only notifications
- `notifications`: which notification keys the user should receive

The current user is already registered there, with the description set so we remember it is you.

If you want to add or update a user manually, use:

```bash
python3 -m dormitory_bot.user_data \
  --user-id 123456789012345678 \
  --description "あなた。現在このプロジェクトを使っているユーザー。" \
  --alias ぼく \
  --test-user \
  --notification menu \
  --notification cleaning \
  --notification cleaning_rotation
```

If you omit `--notification`, the command subscribes the user to the built-in notification set.

After saving, the command sends that user a Discord DM that summarizes:

- which notification types they will receive
- whether they are marked as a test user

This post-save notice is sent as an embed.

## Adding notifications

When you add a new notification type later, keep this checklist in mind:

1. Add a new notification key to the user records if needed.
1. Create a dedicated sender module named like `dormitory_bot/<name>_notify.py`.
1. Add the same notification key to each user who should receive it in `data/user_data.json`.
1. If the notification needs its own state, store it in `data/<name>_*.json` rather than hard-coding it.
1. Add or update a helper script in `scripts/` and a cron entry that calls it.
1. Send Discord DMs to the subscribed `user_id`s, because in this project "notification" means a DM from the bot.
1. For test runs, pass `--test-users-only` to the same shell script you use in cron so only users with `test_user: true` are notified.
1. For user registration or edits, let `dormitory_bot.user_data` send the post-save notice automatically.

## Discord

Set your bot token in `.env`:

```bash
export DISCORD_BOT_TOKEN="your-bot-token"
```

If you want to send to a specific Discord channel for a one-off test, that is outside the normal project flow.
Normally, both menu and cleaning notifications are DMed to the subscribed `user_id`s.

Send the latest menu notification manually:

```bash
python3 -m dormitory_bot.menu_notify --meal lunch
```

Send the cleaning reminder manually:

```bash
python3 -m dormitory_bot.cleaning_notify
```

Send the cleaning rotation reminder manually:

```bash
python3 -m dormitory_bot.cleaning_rotation_notify
```

To test either notification without changing cron, run the same shell script with `--test-users-only`:

```bash
/home/kazu/dormitory/scripts/send_cleaning.sh --test-users-only
/home/kazu/dormitory/scripts/send_cleaning_rotation.sh --test-users-only
```

Dry-run the cleaning reminder without sending:

```bash
python3 -m dormitory_bot.cleaning_notify --dry-run
```

The cleaning turn rotates through `東 → 中 → 西` and the state is stored in [`data/cleaning_rotation.json`](/home/kazu/dormitory/data/cleaning_rotation.json).

## Cron

The helper scripts load `.env` automatically.

Use them from cron like this:

```cron
30 7 * * 1-5 /home/kazu/dormitory/scripts/send_menu.sh --meal breakfast >> /home/kazu/dormitory/dormitory_bot.log 2>&1
10 12 * * 1-5 /home/kazu/dormitory/scripts/send_menu.sh --meal lunch >> /home/kazu/dormitory/dormitory_bot.log 2>&1
0 18 * * 1-5 /home/kazu/dormitory/scripts/send_menu.sh --meal dinner >> /home/kazu/dormitory/dormitory_bot.log 2>&1
0 8 * * 6,0 /home/kazu/dormitory/scripts/send_menu.sh --meal breakfast >> /home/kazu/dormitory/dormitory_bot.log 2>&1
0 12 * * 6,0 /home/kazu/dormitory/scripts/send_menu.sh --meal lunch >> /home/kazu/dormitory/dormitory_bot.log 2>&1
0 18 * * 6,0 /home/kazu/dormitory/scripts/send_menu.sh --meal dinner >> /home/kazu/dormitory/dormitory_bot.log 2>&1
0 20 * * 4 /home/kazu/dormitory/scripts/send_cleaning.sh >> /home/kazu/dormitory/dormitory_bot.log 2>&1
0 20 * * 4 /home/kazu/dormitory/scripts/send_cleaning_rotation.sh >> /home/kazu/dormitory/dormitory_bot.log 2>&1
```

## Example

Weekday lunch:

```cron
10 12 * * 1-5 cd /home/kazu/dormitory && DISCORD_BOT_TOKEN=... python3 -m dormitory_bot.menu_notify --meal lunch
```

Weekend lunch:

```cron
0 12 * * 6,0 cd /home/kazu/dormitory && DISCORD_BOT_TOKEN=... python3 -m dormitory_bot.menu_notify --meal lunch
```
