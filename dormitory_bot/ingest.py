from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import DEFAULT_STORE_PATH, JST
from .store import MenuEntry, parse_menu_from_text, summarize_menu, upsert_entry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Store a meal menu into the local JSON database.")
    parser.add_argument("--meal", required=True, choices=["breakfast", "lunch", "dinner"])
    parser.add_argument("--date", help="Menu date in YYYY-MM-DD. Defaults to today in JST.")
    parser.add_argument("--text", required=True, help="Menu text that was transcribed from the image.")
    parser.add_argument(
        "--menu-summary",
        help="Optional short summary to store in menu.json. Defaults to an auto-generated summary.",
    )
    parser.add_argument(
        "--menu-json",
        help="Optional structured JSON menu. When omitted, --text is parsed into structured fields.",
    )
    parser.add_argument("--image-path", help="Optional original image path for reference.")
    parser.add_argument("--store", default=str(DEFAULT_STORE_PATH), help="Path to the JSON store.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tz = ZoneInfo(JST)
    today = datetime.now(tz).date().isoformat()
    target_date = args.date or today

    text = args.text.strip()

    if not text:
        raise SystemExit("No menu text was provided.")

    if args.menu_json:
        menu = json.loads(args.menu_json)
        if not isinstance(menu, dict):
            raise SystemExit("--menu-json must decode to an object.")
    else:
        menu = parse_menu_from_text(args.meal, text)

    menu_summary = args.menu_summary.strip() if args.menu_summary else summarize_menu(args.meal, menu)

    entry = MenuEntry(
        date=target_date,
        meal=args.meal,
        menu=menu,
        menu_summary=menu_summary or None,
        image_path=str(Path(args.image_path).resolve()) if args.image_path else None,
        extracted_at=datetime.now(tz).isoformat(),
    )
    upsert_entry(entry, Path(args.store))
    print(f"Saved {args.meal} menu for {target_date} to {args.store}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
