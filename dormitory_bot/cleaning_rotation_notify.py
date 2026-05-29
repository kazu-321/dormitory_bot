from __future__ import annotations

import argparse
import os
from pathlib import Path

from .cleaning_rotation import DEFAULT_CLEANING_ROTATION_PATH, advance_rotation, get_current_and_next_turn
from .discord_client import send_dm_message
from .user_data import DEFAULT_USER_DATA_PATH, filter_test_users, find_users_for_notification

CLEANING_ROTATION_EMBED_COLOR = 0x4E79A7


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send the dorm cleaning rotation reminder to Discord and exit.")
    parser.add_argument(
        "--token",
        default=os.getenv("DISCORD_BOT_TOKEN"),
        help="Discord bot token.",
    )
    parser.add_argument(
        "--user-store",
        default=str(DEFAULT_USER_DATA_PATH),
        help="Path to the user JSON file used for DM sending.",
    )
    parser.add_argument(
        "--rotation-store",
        default=str(DEFAULT_CLEANING_ROTATION_PATH),
        help="Path to the cleaning rotation JSON file.",
    )
    parser.add_argument(
        "--test-users-only",
        action="store_true",
        help="Send notifications only to users marked as test users.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the message instead of sending it.")
    return parser.parse_args()


def build_message(current_turn: str) -> str:
    return f"今週の掃除当番は（{current_turn}）です。"


def build_embed(current_turn: str) -> dict:
    return {
        "title": "掃除当番",
        "description": f"```text\n今週の掃除当番は（{current_turn}）です。\n```",
        "color": CLEANING_ROTATION_EMBED_COLOR,
        "footer": {
            "text": "dormitory_bot",
        },
    }


def main() -> int:
    args = parse_args()
    current_turn, _next_turn, _rotation_data = get_current_and_next_turn(Path(args.rotation_store))
    message = build_message(current_turn)
    embed = build_embed(current_turn)

    if args.dry_run:
        print(message)
        return 0

    if not args.token:
        raise SystemExit("DISCORD_BOT_TOKEN is required.")
    if args.token.isdigit() and len(args.token) == 18:
        raise SystemExit(
            "DISCORD_BOT_TOKEN looks like a Discord user ID, not a bot token. "
            "Please put the actual bot token into .env."
        )

    recipients = filter_test_users(
        find_users_for_notification("cleaning_rotation", Path(args.user_store)),
        args.test_users_only,
    )
    if not recipients:
        suffix = " and marked as test users" if args.test_users_only else ""
        raise SystemExit(
            f"No users subscribed to cleaning rotation notifications{suffix} in {args.user_store}"
        )

    sent_user_ids: set[str] = set()
    failures: list[str] = []
    for user in recipients:
        user_id = str(user.get("user_id", "")).strip()
        if not user_id or user_id in sent_user_ids:
            continue
        sent_user_ids.add(user_id)
        try:
            send_dm_message(args.token, user_id, embeds=[embed])
        except Exception as exc:  # pragma: no cover - network dependent
            failures.append(f"{user_id}: {exc}")

    if failures:
        raise SystemExit("Failed to send cleaning rotation notifications:\n" + "\n".join(failures))

    advance_rotation(Path(args.rotation_store))
    print(f"Sent cleaning rotation reminder to {len(sent_user_ids)} Discord user(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
