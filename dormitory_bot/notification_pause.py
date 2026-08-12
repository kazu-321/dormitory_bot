from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .config import DATA_DIR, JST


DEFAULT_PAUSE_PATH = DATA_DIR / "notification_pause.json"


def load_pause(path: Path = DEFAULT_PAUSE_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}

    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("notification pause config must be an object")
    return payload


def paused_through(path: Path = DEFAULT_PAUSE_PATH) -> str | None:
    payload = load_pause(path)
    value = str(payload.get("paused_through", "")).strip()
    if not value:
        return None
    datetime.strptime(value, "%Y-%m-%d")
    return value


def is_paused(now: datetime | None = None, path: Path = DEFAULT_PAUSE_PATH) -> bool:
    through = paused_through(path)
    if through is None:
        return False

    current = now or datetime.now(ZoneInfo(JST))
    return current.date().isoformat() <= through


def pause_message(path: Path = DEFAULT_PAUSE_PATH) -> str:
    through = paused_through(path)
    if through is None:
        return "Notifications are not paused."
    return f"Notifications are paused through {through}."
