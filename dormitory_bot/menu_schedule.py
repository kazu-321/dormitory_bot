from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import DATA_DIR, JST


DEFAULT_OVERRIDE_PATH = DATA_DIR / "notification_overrides.json"
VALID_MEALS = {"breakfast", "lunch", "dinner"}


def load_overrides(path: Path = DEFAULT_OVERRIDE_PATH) -> dict[tuple[str, str], str]:
    if not path.exists():
        return {}

    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    entries = payload.get("overrides", [])
    if not isinstance(entries, list):
        raise ValueError("notification overrides must contain an overrides list")

    overrides: dict[tuple[str, str], str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("each notification override must be an object")
        date_value = str(entry.get("date", "")).strip()
        meal = str(entry.get("meal", "")).strip()
        time_value = str(entry.get("time", "")).strip()
        datetime.strptime(date_value, "%Y-%m-%d")
        datetime.strptime(time_value, "%H:%M")
        if meal not in VALID_MEALS:
            raise ValueError(f"unsupported meal in notification override: {meal}")
        key = (date_value, meal)
        if key in overrides:
            raise ValueError(f"duplicate notification override: {date_value} {meal}")
        overrides[key] = time_value
    return overrides


def should_run_base(
    meal: str,
    now: datetime,
    base_time: str,
    path: Path = DEFAULT_OVERRIDE_PATH,
) -> bool:
    """Run the normal cron job only when that date/meal has no override."""
    datetime.strptime(base_time, "%H:%M")
    return (now.date().isoformat(), meal) not in load_overrides(path)


def due_override_meals(
    now: datetime | None = None,
    path: Path = DEFAULT_OVERRIDE_PATH,
) -> list[str]:
    now = now or datetime.now(ZoneInfo(JST))
    date_value = now.date().isoformat()
    time_value = now.strftime("%H:%M")
    overrides = load_overrides(path)
    return sorted(
        meal
        for (override_date, meal), override_time in overrides.items()
        if override_date == date_value and override_time == time_value
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check scheduled menu notification overrides.")
    parser.add_argument("--mode", choices=["base", "due"], required=True)
    parser.add_argument("--meal", choices=sorted(VALID_MEALS))
    parser.add_argument("--base-time")
    parser.add_argument("--overrides", default=str(DEFAULT_OVERRIDE_PATH))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = Path(args.overrides)
    now = datetime.now(ZoneInfo(JST))
    if args.mode == "due":
        for meal in due_override_meals(now, path):
            print(meal)
        return 0

    if not args.meal or not args.base_time:
        raise SystemExit("--meal and --base-time are required in base mode")
    if should_run_base(args.meal, now, args.base_time, path):
        return 0
    print(f"Skipped base schedule for overridden {now.date()} {args.meal}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
