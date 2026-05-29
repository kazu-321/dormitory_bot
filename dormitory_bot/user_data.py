from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from .config import DATA_DIR, JST
from .discord_client import send_dm_message

DEFAULT_USER_DATA_PATH = DATA_DIR / "user_data.json"
DEFAULT_NOTIFICATION_KEYS = ("menu", "cleaning", "cleaning_rotation")

NOTIFICATION_LABELS_JA = {
    "menu": "メニュー通知",
    "cleaning": "掃除開始通知",
    "cleaning_rotation": "掃除当番通知",
}


@dataclass
class UserRecord:
    user_id: str
    description: str
    notifications: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    test_user: bool = False
    username: str | None = None
    display_name: str | None = None
    source: str = "manual"
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "user_id": self.user_id,
            "description": self.description,
            "notifications": _unique_preserve_order(self.notifications),
            "aliases": _unique_preserve_order(self.aliases),
            "test_user": self.test_user,
            "source": self.source,
        }
        if self.username is not None:
            data["username"] = self.username
        if self.display_name is not None:
            data["display_name"] = self.display_name
        if self.updated_at is not None:
            data["updated_at"] = self.updated_at
        return data


def _unique_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = str(item).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _default_user_data() -> dict[str, Any]:
    return {"version": 1, "users": []}


def _coerce_legacy_user_data(data: dict[str, Any]) -> dict[str, Any]:
    if "users" in data:
        users = data.get("users")
        if isinstance(users, list):
            return {"version": int(data.get("version", 1) or 1), "users": users}
        return _default_user_data()

    recipient = data.get("recipient")
    if isinstance(recipient, dict):
        user: dict[str, Any] = {
            "user_id": str(recipient.get("user_id", "")).strip(),
            "description": recipient.get(
                "description",
                "あなた。現在このプロジェクトを使っているユーザー。",
            ),
            "notifications": list(DEFAULT_NOTIFICATION_KEYS),
            "aliases": [],
            "test_user": bool(recipient.get("test_user", False)),
            "source": recipient.get("source", "manual"),
        }
        if recipient.get("username") is not None:
            user["username"] = recipient["username"]
        if recipient.get("display_name") is not None:
            user["display_name"] = recipient["display_name"]
        if recipient.get("updated_at") is not None:
            user["updated_at"] = recipient["updated_at"]
        if user["user_id"]:
            return {"version": int(data.get("version", 1) or 1), "users": [user]}

    return _default_user_data()


def ensure_user_data_store(path: Path = DEFAULT_USER_DATA_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(_default_user_data(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_user_data(path: Path = DEFAULT_USER_DATA_PATH) -> dict[str, Any]:
    path = ensure_user_data_store(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return _default_user_data()
    return _coerce_legacy_user_data(raw)


def save_user_data(data: dict[str, Any], path: Path = DEFAULT_USER_DATA_PATH) -> dict[str, Any]:
    path = ensure_user_data_store(path)
    normalized = _coerce_legacy_user_data(data)
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return normalized


def load_users(path: Path = DEFAULT_USER_DATA_PATH) -> list[dict[str, Any]]:
    data = load_user_data(path)
    users = data.get("users", [])
    return [user for user in users if isinstance(user, dict)]


def find_users_for_notification(notification_key: str, path: Path = DEFAULT_USER_DATA_PATH) -> list[dict[str, Any]]:
    normalized_key = str(notification_key).strip()
    if not normalized_key:
        return []

    result: list[dict[str, Any]] = []
    for user in load_users(path):
        notifications = user.get("notifications", [])
        if not isinstance(notifications, list):
            continue
        normalized_notifications = {str(item).strip() for item in notifications if str(item).strip()}
        if normalized_key in normalized_notifications and user.get("user_id"):
            result.append(user)
    return result


def filter_test_users(users: list[dict[str, Any]], test_users_only: bool) -> list[dict[str, Any]]:
    if not test_users_only:
        return users
    result: list[dict[str, Any]] = []
    for user in users:
        if bool(user.get("test_user", False)):
            result.append(user)
    return result


def _format_notification_lines(notifications: Iterable[str]) -> list[str]:
    lines: list[str] = []
    for notification in _unique_preserve_order(notifications):
        label = NOTIFICATION_LABELS_JA.get(notification, notification)
        lines.append(f"- {label} (`{notification}`)")
    return lines


def build_user_update_embed(user: dict[str, Any]) -> dict[str, Any]:
    notification_lines = _format_notification_lines(user.get("notifications", []))
    notification_text = "\n".join(notification_lines) if notification_lines else "- なし"
    test_user_text = "はい" if bool(user.get("test_user", False)) else "いいえ"

    return {
        "title": "有朋寮通知BOTに追加されました",
        "description": "あなたには以下の情報が通知されます",
        "fields": [
            {"name": "通知", "value": notification_text, "inline": False},
            {"name": "テストユーザー", "value": test_user_text, "inline": True},
        ],
        "color": 0x4E79A7,
        "footer": {"text": "dormitory_bot"},
    }


def notify_user_update(token: str, user: dict[str, Any]) -> None:
    user_id = str(user.get("user_id", "")).strip()
    if not user_id:
        raise ValueError("User record does not contain user_id.")
    embed = build_user_update_embed(user)
    send_dm_message(token, user_id, embeds=[embed])


def upsert_user(user: UserRecord, path: Path = DEFAULT_USER_DATA_PATH) -> dict[str, Any]:
    data = load_user_data(path)
    users = [item for item in data.get("users", []) if isinstance(item, dict)]

    normalized_user = user.to_dict()
    replaced = False
    for index, existing in enumerate(users):
        if str(existing.get("user_id", "")).strip() == normalized_user["user_id"]:
            users[index] = normalized_user
            replaced = True
            break

    if not replaced:
        users.append(normalized_user)

    return save_user_data({"version": int(data.get("version", 1) or 1), "users": users}, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Save a Discord user record and notification subscriptions to local JSON.")
    parser.add_argument("--user-id", required=True, help="Discord user ID used for DM sending.")
    parser.add_argument(
        "--description",
        default="あなた。現在このプロジェクトを使っているユーザー。",
        help="Short description for identifying the person later.",
    )
    parser.add_argument("--username", help="Optional Discord username or handle for reference.")
    parser.add_argument("--display-name", help="Optional display name for reference.")
    parser.add_argument(
        "--alias",
        action="append",
        default=[],
        help="Optional nickname or alias. Repeatable.",
    )
    parser.add_argument(
        "--test-user",
        action="store_true",
        help="Mark this user as a test user.",
    )
    parser.add_argument(
        "--notification",
        action="append",
        default=[],
        help="Notification key to subscribe the user to. Repeatable. Defaults to all known notifications.",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("DISCORD_BOT_TOKEN"),
        help="Discord bot token used to notify the user after save.",
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Save the user without sending the post-save notification.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the post-save notification instead of sending it.")
    parser.add_argument("--store", default=str(DEFAULT_USER_DATA_PATH), help="Path to the user JSON file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tz = ZoneInfo(JST)
    notifications = args.notification or list(DEFAULT_NOTIFICATION_KEYS)
    record = UserRecord(
        user_id=str(args.user_id).strip(),
        description=args.description.strip(),
        notifications=_unique_preserve_order(notifications),
        aliases=_unique_preserve_order(args.alias),
        test_user=bool(args.test_user),
        username=args.username.strip() if args.username else None,
        display_name=args.display_name.strip() if args.display_name else None,
        updated_at=datetime.now(tz).isoformat(),
    )
    saved = upsert_user(record, Path(args.store))
    saved_user = next(
        (item for item in saved.get("users", []) if isinstance(item, dict) and str(item.get("user_id", "")).strip() == record.user_id),
        None,
    )
    if saved_user is None:
        raise SystemExit("Saved user could not be found after update.")

    if args.no_notify:
        print(f"Saved Discord user data to {args.store}")
        return 0

    if args.dry_run:
        print(build_user_update_embed(saved_user))
        return 0

    if not args.token:
        print(f"Saved Discord user data to {args.store} but DISCORD_BOT_TOKEN is missing, so no notification was sent.")
        return 0

    notify_user_update(args.token, saved_user)
    print(f"Saved Discord user data to {args.store}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
