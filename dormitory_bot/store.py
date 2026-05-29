from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .config import DEFAULT_STORE_PATH


@dataclass
class MenuEntry:
    date: str
    meal: str
    text: str
    menu_summary: str | None = None
    image_path: str | None = None
    source: str = "manual"
    extracted_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "date": self.date,
            "meal": self.meal,
            "text": self.text,
            "source": self.source,
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
        path.write_text(json.dumps({"version": 1, "entries": []}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_store(path: Path = DEFAULT_STORE_PATH) -> dict[str, Any]:
    path = ensure_store(path)
    return json.loads(path.read_text(encoding="utf-8"))


def save_store(data: dict[str, Any], path: Path = DEFAULT_STORE_PATH) -> None:
    ensure_store(path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def _strip_prefixes(text: str) -> str:
    value = text.strip()
    for prefix in ("Aセット:", "Aセット：", "Bセット:", "Bセット："):
        if value.startswith(prefix):
            return value.split(":", 1)[1].strip()
    return value


def summarize_menu_name(text: str) -> str:
    value = _strip_prefixes(text)
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


def summarize_menu_text(meal: str, text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""

    if meal == "dinner":
        a_main = ""
        b_main = ""
        for line in lines:
            if line.startswith("Aセット:") or line.startswith("Aセット："):
                a_main = summarize_menu_name(line.split(":", 1)[1].strip())
            elif line.startswith("Bセット:") or line.startswith("Bセット："):
                b_main = summarize_menu_name(line.split(":", 1)[1].strip())
        if a_main or b_main:
            parts = [part for part in (a_main, b_main) if part]
            return " / ".join(parts)

    return summarize_menu_name(lines[0])


def today_iso(now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now()
    return date.fromisoformat(now.date().isoformat()).isoformat()
