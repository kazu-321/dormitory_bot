from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_STORE_PATH = DATA_DIR / "menu.json"

JST = "Asia/Tokyo"


@dataclass(frozen=True)
class MealSchedule:
    weekday: dict[str, time]
    weekend: dict[str, time]


DEFAULT_SCHEDULE = MealSchedule(
    weekday={
        "breakfast": time(7, 30),
        "lunch": time(12, 10),
        "dinner": time(18, 0),
    },
    weekend={
        "breakfast": time(8, 0),
        "lunch": time(12, 0),
        "dinner": time(18, 0),
    },
)


MEAL_LABELS_JA = {
    "breakfast": "朝",
    "lunch": "昼",
    "dinner": "夜",
}


MEAL_COLORS = {
    "breakfast": 0xF4C542,
    "lunch": 0xF28C28,
    "dinner": 0x4E79A7,
}
