from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import DEFAULT_STORE_PATH, JST, MEAL_COLORS, MEAL_LABELS_JA
from .discord_client import send_dm_message
from .user_data import DEFAULT_USER_DATA_PATH, filter_test_users, find_users_for_notification
from .store import find_entry, latest_entry_for_meal, menu_to_lines, parse_menu_from_text


MEAL_ORDER = {
    "breakfast": 0,
    "lunch": 1,
    "dinner": 2,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a meal menu to Discord and exit.")
    parser.add_argument("--meal", required=True, choices=["breakfast", "lunch", "dinner"])
    parser.add_argument("--date", help="Menu date in YYYY-MM-DD. Defaults to today in JST.")
    parser.add_argument("--store", default=str(DEFAULT_STORE_PATH), help="Path to the JSON store.")
    parser.add_argument("--token", default=os.getenv("DISCORD_BOT_TOKEN"), help="Discord bot token.")
    parser.add_argument(
        "--user-store",
        default=str(DEFAULT_USER_DATA_PATH),
        help="Path to the user JSON file.",
    )
    parser.add_argument(
        "--test-users-only",
        action="store_true",
        help="Send notifications only to users marked as test users.",
    )
    parser.add_argument("--allow-latest", action="store_true", help="Fallback to the latest entry for that meal if today is missing.")
    parser.add_argument("--dry-run", action="store_true", help="Print the message instead of sending it.")
    return parser.parse_args()


def _non_empty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _extract_lunch_main(text: str) -> str | None:
    lines = _non_empty_lines(text)
    return lines[0] if lines else None


def _extract_dinner_mains(text: str) -> tuple[str | None, str | None]:
    a_main: str | None = None
    b_main: str | None = None
    for line in _non_empty_lines(text):
        if line.startswith("Aセット:") or line.startswith("Aセット："):
            a_main = line.split(":", 1)[1].strip() or None
        elif line.startswith("Bセット:") or line.startswith("Bセット："):
            b_main = line.split(":", 1)[1].strip() or None
    return a_main, b_main


def _weekday_ja(entry_date: str) -> str:
    weekdays = ("月", "火", "水", "木", "金", "土", "日")
    return weekdays[date.fromisoformat(entry_date).weekday()]


def _format_date_label(entry_date: str) -> str:
    parsed = date.fromisoformat(entry_date)
    return f"{parsed.month}/{parsed.day} ({_weekday_ja(entry_date)})"


def _format_full_meal(entry: dict) -> str:
    meal = str(entry.get("meal", ""))
    text = str(entry.get("text", ""))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if meal == "dinner":
        a_main, b_main = _extract_dinner_mains(text)
        parts: list[str] = []
        if a_main:
            parts.append(f"A {a_main}")
        if b_main:
            parts.append(f"B {b_main}")
        if parts:
            return " / ".join(parts)
    return " / ".join(lines[:3]) if lines else ""


def _format_meal_label(meal: str) -> str:
    return {
        "breakfast": "朝",
        "lunch": "昼",
        "dinner": "夜",
    }.get(meal, meal)


def _meal_detail_title(meal: str) -> str:
    return {
        "breakfast": "朝ご飯は",
        "lunch": "お昼ご飯は",
        "dinner": "夜ご飯は",
    }.get(meal, "ご飯は")


def _contains_coffee_milk(entry: dict | None) -> bool:
    if not entry:
        return False
    return "コーヒー牛乳" in str(entry.get("text", ""))


def _previous_day_iso(entry_date: str) -> str:
    return (date.fromisoformat(entry_date) - timedelta(days=1)).isoformat()


def _coffee_milk_note_for_breakfast(store_path: Path, entry_date: str) -> str:
    previous_day = _previous_day_iso(entry_date)
    if _contains_coffee_milk(find_entry(previous_day, "lunch", store_path)):
        return " (ｺｰﾋｰ牛乳)"
    return ""


def build_message_body(store_path: Path, current_entry: dict, current_date: str, current_meal: str) -> str:
    menu = current_entry.get("menu")
    if not isinstance(menu, dict):
        menu = parse_menu_from_text(current_meal, str(current_entry.get("text", "")))

    lines = menu_to_lines(current_meal, menu)
    if current_meal == "breakfast":
        coffee_milk_note = _coffee_milk_note_for_breakfast(store_path, current_date)
        if coffee_milk_note:
            lines.append(coffee_milk_note)
    detail_block = (
        f"{_format_date_label(current_date)} {_meal_detail_title(current_meal)}\n"
        f"```text\n" + "\n".join(lines) + "\n```"
    )
    return detail_block


def build_embed(title: str, body: str, meal: str) -> dict:
    return {
        "title": title,
        "description": body,
        "color": MEAL_COLORS.get(meal, 0x7A7A7A),
        "footer": {
            "text": "dormitory_bot",
        },
    }


def main() -> int:
    args = parse_args()
    tz = ZoneInfo(JST)
    today = datetime.now(tz).date().isoformat()
    target_date = args.date or today
    store_path = Path(args.store)

    entry = find_entry(target_date, args.meal, store_path)
    if entry is None and args.allow_latest:
        entry = latest_entry_for_meal(args.meal, store_path)
    if entry is None:
        raise SystemExit(f"No menu entry found for meal={args.meal}")

    body = build_message_body(store_path, entry, entry["date"], entry["meal"])
    embed = build_embed("メニュー", body, entry["meal"])
    if args.dry_run:
        print("メニュー")
        print(body)
        return 0

    if not args.token:
        raise SystemExit("DISCORD_BOT_TOKEN is required.")
    if args.token.isdigit() and len(args.token) == 18:
        raise SystemExit(
            "DISCORD_BOT_TOKEN looks like a Discord user ID, not a bot token. "
            "Please put the actual bot token into .env."
        )

    recipients = filter_test_users(find_users_for_notification("menu", Path(args.user_store)), args.test_users_only)
    if not recipients:
        suffix = " and marked as test users" if args.test_users_only else ""
        raise SystemExit(f"No users subscribed to menu notifications{suffix} in {args.user_store}")

    sent_user_ids: set[str] = set()
    failures: list[str] = []
    for user in recipients:
        user_id = str(user.get("user_id", "")).strip()
        if not user_id or user_id in sent_user_ids:
            continue
        sent_user_ids.add(user_id)
        try:
            send_dm_message(args.token, user_id, content=None, embeds=[embed])
        except Exception as exc:  # pragma: no cover - network dependent
            failures.append(f"{user_id}: {exc}")

    if failures:
        raise SystemExit("Failed to send menu notifications:\n" + "\n".join(failures))

    print(f"Sent {entry['meal']} menu for {entry['date']} to {len(sent_user_ids)} Discord user(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
