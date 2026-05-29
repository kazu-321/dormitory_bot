from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import DATA_DIR

DEFAULT_CLEANING_ROTATION_PATH = DATA_DIR / "cleaning_rotation.json"
DEFAULT_CLEANING_TURNS = ("東", "中", "西")


def _default_rotation_data() -> dict[str, Any]:
    return {
        "version": 1,
        "next_turn_index": 0,
    }


def _coerce_rotation_data(data: dict[str, Any]) -> dict[str, Any]:
    raw_index = data.get("next_turn_index", 0)
    try:
        next_turn_index = int(raw_index)
    except (TypeError, ValueError):
        next_turn_index = 0

    turn_count = len(DEFAULT_CLEANING_TURNS)
    if turn_count:
        next_turn_index %= turn_count

    return {
        "version": int(data.get("version", 1) or 1),
        "next_turn_index": next_turn_index,
    }


def ensure_rotation_store(path: Path = DEFAULT_CLEANING_ROTATION_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(_default_rotation_data(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_rotation_data(path: Path = DEFAULT_CLEANING_ROTATION_PATH) -> dict[str, Any]:
    path = ensure_rotation_store(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return _default_rotation_data()
    return _coerce_rotation_data(raw)


def save_rotation_data(data: dict[str, Any], path: Path = DEFAULT_CLEANING_ROTATION_PATH) -> dict[str, Any]:
    path = ensure_rotation_store(path)
    normalized = _coerce_rotation_data(data)
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return normalized


def get_current_and_next_turn(path: Path = DEFAULT_CLEANING_ROTATION_PATH) -> tuple[str, str, dict[str, Any]]:
    data = load_rotation_data(path)
    turns = list(DEFAULT_CLEANING_TURNS)
    if not turns:
        return "", "", data

    next_turn_index = int(data.get("next_turn_index", 0)) % len(turns)
    current_turn = turns[next_turn_index]
    next_turn = turns[(next_turn_index + 1) % len(turns)]
    return current_turn, next_turn, data


def advance_rotation(path: Path = DEFAULT_CLEANING_ROTATION_PATH) -> dict[str, Any]:
    data = load_rotation_data(path)
    turns = list(DEFAULT_CLEANING_TURNS)
    if not turns:
        return data

    next_turn_index = (int(data.get("next_turn_index", 0)) + 1) % len(turns)
    return save_rotation_data({"version": int(data.get("version", 1) or 1), "next_turn_index": next_turn_index}, path)
