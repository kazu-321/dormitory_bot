#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


DATE_RE = re.compile(r"(\d+)月(\d+)日")
NOISE_RE = re.compile(
    r"^(?:[0-9,\. \tＥＰＦＣＳkcalgＡＢA/B／]+|"
    r"アレルゲン|小麦|卵|乳|そば|落花生|えび|かに|くるみ|"
    r"Aセット|Bセット|Ａセット|Ｂセット|Ａ／Ｂ共通メニュー|A/B共通メニュー)$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract menu data from dormitory menu PDFs and print JSON.")
    parser.add_argument("pdfs", nargs="+", help="One or more PDF files to parse.")
    return parser.parse_args()


def _layout_lines(pdf_path: Path) -> list[str]:
    return subprocess.check_output(["pdftotext", "-layout", str(pdf_path), "-"], text=True).splitlines()


def _date_info(lines: list[str]) -> tuple[list[str], list[int]]:
    matches = list(DATE_RE.finditer(lines[0]))
    dates = [f"2026-{int(m.group(1)):02d}-{int(m.group(2)):02d}" for m in matches]
    starts = [m.start() for m in matches]
    bounds = [0]
    for i in range(len(starts) - 1):
        bounds.append((starts[i] + starts[i + 1]) // 2)
    return dates, bounds


def _slice_cells(line: str, bounds: list[int]) -> list[str]:
    return [line[bounds[i] : bounds[i + 1] if i < 6 else len(line)].strip() for i in range(7)]


def _clean(cell: str) -> str:
    return re.sub(r"^(?:朝|昼|夕|食)\s*", "", cell).strip()


def _normalize(cell: str) -> str:
    return re.sub(r"\s+", " ", cell).strip().replace("Ａ／Ｂ", "A/B").replace("Ａ", "A").replace("Ｂ", "B")


def _is_item(cell: str) -> bool:
    if not cell:
        return False
    if NOISE_RE.match(cell):
        return False
    if re.fullmatch(r"[0-9,\.]+", cell):
        return False
    if cell.startswith("kcal") or cell.startswith("g "):
        return False
    return True


def _first_idx(lines: list[str], pred, start: int = 0) -> int | None:
    for i in range(start, len(lines)):
        if pred(lines[i]):
            return i
    return None


def _prev_nonempty(lines: list[str], idx: int | None) -> int | None:
    if idx is None:
        return None
    for i in range(idx - 1, -1, -1):
        if lines[i].strip():
            return i
    return None


def _next_nonempty(lines: list[str], idx: int | None) -> int | None:
    if idx is None:
        return None
    for i in range(idx + 1, len(lines)):
        if lines[i].strip():
            return i
    return None


def _parse_pdf(pdf_path: Path) -> dict[str, Any]:
    lines = _layout_lines(pdf_path)
    dates, bounds = _date_info(lines)

    breakfast_main_idx = _first_idx(lines, lambda l: l.strip().startswith("朝"))
    breakfast_side_idx = _next_nonempty(lines, breakfast_main_idx)
    breakfast_food_idx = _first_idx(lines, lambda l: l.strip() == "食", breakfast_side_idx)

    lunch_dessert_idx = _first_idx(lines, lambda l: l.strip().startswith("昼"))
    lunch_side_idx = _prev_nonempty(lines, lunch_dessert_idx)
    lunch_main_idx = _prev_nonempty(lines, lunch_side_idx)
    lunch_staple_idx = _next_nonempty(lines, lunch_dessert_idx)
    lunch_food_idx = _first_idx(lines, lambda l: l.strip() == "食", lunch_staple_idx)
    lunch_drink_idx = _next_nonempty(lines, lunch_food_idx)

    dinner_a_label = _first_idx(lines, lambda l: "Aセット" in l or "Ａセット" in l, lunch_drink_idx)
    dinner_b_label = _first_idx(lines, lambda l: "Bセット" in l or "Ｂセット" in l, dinner_a_label)
    common_label = _first_idx(lines, lambda l: "A/B共通メニュー" in l or "Ａ／Ｂ共通メニュー" in l, dinner_b_label)
    dinner_end = _first_idx(lines, lambda l: l.lstrip().startswith("Ｅ") or l.lstrip().startswith("E"), common_label)

    breakfast_rows = [breakfast_main_idx, breakfast_side_idx, breakfast_food_idx + 1, breakfast_food_idx + 2, breakfast_food_idx + 3]
    lunch_rows = [lunch_main_idx, lunch_side_idx, lunch_dessert_idx, lunch_staple_idx, lunch_drink_idx]
    a_rows = [i for i in range(dinner_a_label + 1, dinner_b_label) if lines[i].strip() and not NOISE_RE.match(lines[i].strip())]
    b_rows = [i for i in range(dinner_b_label + 1, common_label) if lines[i].strip() and not NOISE_RE.match(lines[i].strip())]
    common_rows = [i for i in range(common_label + 1, dinner_end) if lines[i].strip() and not NOISE_RE.match(lines[i].strip())]

    entries: list[dict[str, Any]] = []
    for idx, date_value in enumerate(dates):
        breakfast_items: list[str] = []
        for row_idx in breakfast_rows:
            cell = _normalize(_clean(_slice_cells(lines[row_idx], bounds)[idx]))
            if _is_item(cell):
                breakfast_items.append(cell)

        lunch_items: list[str] = []
        for row_idx in lunch_rows:
            cell = _normalize(_clean(_slice_cells(lines[row_idx], bounds)[idx]))
            if _is_item(cell):
                lunch_items.append(cell)

        a_parts: list[str] = []
        for row_idx in a_rows:
            cell = _normalize(_clean(_slice_cells(lines[row_idx], bounds)[idx]))
            if _is_item(cell):
                a_parts.append(cell)

        b_parts: list[str] = []
        for row_idx in b_rows:
            cell = _normalize(_clean(_slice_cells(lines[row_idx], bounds)[idx]))
            if _is_item(cell):
                b_parts.append(cell)

        common_items: list[str] = []
        for row_idx in common_rows:
            cell = _normalize(_clean(_slice_cells(lines[row_idx], bounds)[idx]))
            if _is_item(cell):
                common_items.append(cell)

        entries.append(
            {
                "date": date_value,
                "meal": "breakfast",
                "menu": {"kind": "list", "items": breakfast_items},
            }
        )
        entries.append(
            {
                "date": date_value,
                "meal": "lunch",
                "menu": {"kind": "list", "items": lunch_items},
            }
        )
        entries.append(
            {
                "date": date_value,
                "meal": "dinner",
                "menu": {
                    "kind": "dinner",
                    "a": " ".join(a_parts),
                    "b": " ".join(b_parts),
                    "common": common_items,
                },
            }
        )

    return {"pdf": pdf_path.name, "entries": entries}


def main() -> int:
    args = parse_args()
    parsed = [_parse_pdf(Path(pdf)) for pdf in args.pdfs]
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
