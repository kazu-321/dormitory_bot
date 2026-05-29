from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .config import DEFAULT_STORE_PATH, JST


@dataclass
class MenuEntry:
    date: str
    meal: str
    menu: dict[str, Any]
    menu_summary: str | None = None
    image_path: str | None = None
    extracted_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "date": self.date,
            "meal": self.meal,
            "menu": self.menu,
        }
        if self.menu_summary is not None:
            data["menu_summary"] = self.menu_summary
        if self.image_path is not None:
            data["image_path"] = self.image_path
        if self.extracted_at is not None:
            data["extracted_at"] = self.extracted_at
        return data


def ensure_store(path: Path = DEFAULT_STORE_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps({"version": 2, "entries": []}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_store(path: Path = DEFAULT_STORE_PATH) -> dict[str, Any]:
    path = ensure_store(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 2 or any("menu" not in entry for entry in data.get("entries", []) if isinstance(entry, dict)):
        return migrate_store_data(data)
    return data


def save_store(data: dict[str, Any], path: Path = DEFAULT_STORE_PATH) -> None:
    ensure_store(path)
    data = migrate_store_data(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    from .menu_site import write_menu_site

    write_menu_site(path)


def upsert_entry(entry: MenuEntry, path: Path = DEFAULT_STORE_PATH) -> dict[str, Any]:
    data = load_store(path)
    entries = list(data.get("entries", []))
    updated = False
    for idx, existing in enumerate(entries):
        if existing.get("date") == entry.date and existing.get("meal") == entry.meal:
            entries[idx] = entry.to_dict()
            updated = True
            break
    if not updated:
        entries.append(entry.to_dict())
    entries.sort(key=lambda item: (item.get("date", ""), item.get("meal", "")))
    data["entries"] = entries
    save_store(data, path)
    return data


def find_entry(target_date: str, meal: str, path: Path = DEFAULT_STORE_PATH) -> dict[str, Any] | None:
    data = load_store(path)
    for entry in data.get("entries", []):
        if entry.get("date") == target_date and entry.get("meal") == meal:
            return entry
    return None


def latest_entry_for_meal(meal: str, path: Path = DEFAULT_STORE_PATH) -> dict[str, Any] | None:
    data = load_store(path)
    matches = [entry for entry in data.get("entries", []) if entry.get("meal") == meal]
    if not matches:
        return None
    return sorted(matches, key=lambda item: item.get("date", ""))[-1]


def _today_iso() -> str:
    return datetime.now(ZoneInfo(JST)).date().isoformat()


def _clean_piece(value: str) -> str:
    return value.strip().replace("\u3000", " ")


def _split_common_items(text: str) -> list[str]:
    items: list[str] = []
    for part in text.replace("／", "/").split("/"):
        cleaned = _clean_piece(part)
        if cleaned:
            items.append(cleaned)
    return items


def parse_menu_from_text(meal: str, text: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if meal == "dinner":
        a_main = ""
        b_main = ""
        common: list[str] = []
        for line in lines:
            if line.startswith("Aセット:") or line.startswith("Aセット："):
                a_main = _clean_piece(line.split(":", 1)[1])
            elif line.startswith("Bセット:") or line.startswith("Bセット："):
                b_main = _clean_piece(line.split(":", 1)[1])
            elif line.startswith("A/B共通メニュー:") or line.startswith("共通:"):
                common.extend(_split_common_items(line.split(":", 1)[1]))
            else:
                common.extend(_split_common_items(line))
        return {
            "kind": "dinner",
            "a": a_main,
            "b": b_main,
            "common": common,
        }

    return {
        "kind": "list",
        "items": lines,
    }


def _get_menu_value(menu: dict[str, Any] | None, key: str) -> str:
    if not menu:
        return ""
    value = menu.get(key, "")
    return _clean_piece(str(value)) if value is not None else ""


def summarize_menu_name(text: str) -> str:
    value = _clean_piece(text)
    if not value:
        return value

    candidate = value.split("の")[-1].strip() if "の" in value else value
    keywords = [
        "スクランブルエッグ",
        "ハンバーグ",
        "チキンカツ",
        "チキンソテー",
        "オムレツ",
        "肉団子",
        "ハヤシライス",
        "カレーライス",
        "冷やし中華",
        "焼きそば",
        "うどん",
        "そば",
        "ラーメン",
        "パスタ",
        "スパゲッティ",
        "チャプチェ",
        "焼売",
        "餃子",
        "春巻",
        "コロッケ",
        "唐揚げ",
        "から揚げ",
        "フライ",
        "天ぷら",
        "焼肉",
        "うま煮",
        "マリネ",
        "ナムル",
        "カレーマヨ焼き",
        "マヨ焼き",
        "生姜焼き",
        "豚キムチ",
        "カレー",
    ]
    for keyword in keywords:
        if keyword in candidate:
            return keyword
        if keyword in value:
            return keyword

    if 1 < len(candidate) <= 14:
        return candidate

    for separator in ("／", "/", "・", "、"):
        if separator in candidate:
            return candidate.split(separator, 1)[0].strip()

    if " " in candidate:
        return candidate.split()[-1]

    return candidate or value


def summarize_menu(meal: str, menu: dict[str, Any]) -> str:
    if meal == "dinner":
        parts = []
        a_main = summarize_menu_name(_get_menu_value(menu, "a"))
        b_main = summarize_menu_name(_get_menu_value(menu, "b"))
        if a_main:
            parts.append(a_main)
        if b_main:
            parts.append(b_main)
        if parts:
            return " / ".join(parts)
        return summarize_menu_name(_get_menu_value(menu, "common"))

    items = menu.get("items", []) if isinstance(menu, dict) else []
    if isinstance(items, list) and items:
        return summarize_menu_name(str(items[0]))
    return ""


def menu_to_lines(meal: str, menu: dict[str, Any]) -> list[str]:
    if meal == "dinner":
        lines: list[str] = []
        a_main = _get_menu_value(menu, "a")
        b_main = _get_menu_value(menu, "b")
        if a_main:
            lines.append(f"(A) {a_main}")
        if b_main:
            lines.append(f"(B) {b_main}")
        common = menu.get("common", [])
        if isinstance(common, list):
            for item in common:
                cleaned = _clean_piece(str(item))
                if cleaned:
                    lines.append(cleaned)
        return lines

    items = menu.get("items", [])
    if isinstance(items, list):
        return [_clean_piece(str(item)) for item in items if _clean_piece(str(item))]
    return []


def normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    meal = str(entry.get("meal", "")).strip()
    menu = entry.get("menu")
    if not isinstance(menu, dict):
        text = str(entry.get("text", ""))
        menu = parse_menu_from_text(meal, text)
    normalized: dict[str, Any] = {
        "date": str(entry.get("date", "")).strip(),
        "meal": meal,
        "menu": menu,
    }
    menu_summary = str(entry.get("menu_summary") or "").strip()
    if not menu_summary:
        menu_summary = summarize_menu(meal, menu)
    if menu_summary:
        normalized["menu_summary"] = menu_summary
    image_path = entry.get("image_path")
    if image_path:
        normalized["image_path"] = image_path
    extracted_at = entry.get("extracted_at")
    if extracted_at:
        normalized["extracted_at"] = extracted_at
    return normalized


def migrate_store_data(data: dict[str, Any]) -> dict[str, Any]:
    entries = [normalize_entry(entry) for entry in data.get("entries", []) if isinstance(entry, dict)]
    entries.sort(key=lambda item: (item.get("date", ""), item.get("meal", "")))
    return {"version": 2, "entries": entries}


def today_iso(now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now()
    return date.fromisoformat(now.date().isoformat()).isoformat()
