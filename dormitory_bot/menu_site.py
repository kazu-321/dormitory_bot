from __future__ import annotations

import json
import html
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .config import BASE_DIR, JST, MEAL_LABELS_JA, DEFAULT_STORE_PATH
from .store import load_store, menu_to_lines, normalize_entry, normalize_nutrition, summarize_menu


DEFAULT_WEBSITE_DIR = BASE_DIR
MEAL_ORDER = {"breakfast": 0, "lunch": 1, "dinner": 2}


def _today_iso_jst() -> str:
    return datetime.now(ZoneInfo(JST)).date().isoformat()


def _date_label(entry_date: str) -> str:
    dt = datetime.fromisoformat(f"{entry_date}T00:00:00+09:00")
    weekdays = ("月", "火", "水", "木", "金", "土", "日")
    return f"{dt.month}/{dt.day} ({weekdays[dt.weekday()]})"


def _meal_label(meal: str) -> str:
    return MEAL_LABELS_JA.get(meal, meal)


def _meal_sort_key(meal: str) -> int:
    return MEAL_ORDER.get(meal, 99)


def _escape(text: str) -> str:
    return html.escape(text, quote=True)


def _json_script_data(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


NUTRITION_LABELS = {
    "energy_kcal": "エネルギー",
    "calories_kcal": "エネルギー",
    "kcal": "エネルギー",
    "protein_g": "たんぱく質",
    "fat_g": "脂質",
    "carbohydrate_g": "炭水化物",
    "carbs_g": "炭水化物",
    "salt_g": "食塩相当量",
    "sodium_g": "食塩相当量",
}

NUTRITION_UNITS = {
    "energy_kcal": "kcal",
    "calories_kcal": "kcal",
    "kcal": "kcal",
    "protein_g": "g",
    "fat_g": "g",
    "carbohydrate_g": "g",
    "carbs_g": "g",
    "salt_g": "g",
    "sodium_g": "g",
}

NUTRITION_ORDER = (
    "energy_kcal",
    "calories_kcal",
    "kcal",
    "protein_g",
    "fat_g",
    "carbohydrate_g",
    "carbs_g",
    "salt_g",
    "sodium_g",
)


def _nutrition_label(key: str) -> str:
    return NUTRITION_LABELS.get(key, key.replace("_", " "))


def _nutrition_value(key: str, value: Any) -> str:
    if isinstance(value, float):
        text = f"{value:g}"
    else:
        text = str(value).strip()
    unit = NUTRITION_UNITS.get(key)
    if unit and text and not text.lower().endswith(unit.lower()):
        return f"{text}{unit}"
    return text


def _nutrition_items(nutrition: dict[str, Any] | None) -> list[tuple[str, str]]:
    normalized = normalize_nutrition(nutrition)
    if not normalized:
        return []

    ordered_keys = [key for key in NUTRITION_ORDER if key in normalized]
    ordered_keys.extend(key for key in normalized if key not in ordered_keys)

    items: list[tuple[str, str]] = []
    for key in ordered_keys:
        value = _nutrition_value(key, normalized[key])
        if value:
            items.append((_nutrition_label(key), value))
    return items


def _render_nutrition_panel(nutrition: dict[str, Any] | None) -> str:
    items = _nutrition_items(nutrition)
    if not items:
        return ""

    rows = "".join(
        f"<div class=\"nutrition-item\"><dt>{_escape(label)}</dt><dd>{_escape(value)}</dd></div>"
        for label, value in items
    )
    return f"""
        <details class="nutrition-panel">
          <summary>栄養を見る</summary>
          <dl class="nutrition-list">{rows}</dl>
        </details>
    """


def _date_adjustment_js() -> str:
    return """
    function formatDateInTimeZone(date, timeZone) {
      const parts = new Intl.DateTimeFormat("en-CA", {
        timeZone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }).formatToParts(date);
      const mapped = {};
      for (const part of parts) {
        if (part.type !== "literal") {
          mapped[part.type] = part.value;
        }
      }
      return `${mapped.year}-${mapped.month}-${mapped.day}`;
    }

    function currentJstIsoDate() {
      return formatDateInTimeZone(new Date(), "Asia/Tokyo");
    }
    """


def _render_menu_card(entry: dict[str, Any]) -> str:
    meal = str(entry.get("meal", ""))
    menu = entry.get("menu")
    if not isinstance(menu, dict):
        return ""

    summary = str(entry.get("menu_summary") or "").strip()
    if not summary:
        summary = summarize_menu(meal, menu)

    lines = menu_to_lines(meal, menu)
    detail_items = "".join(f"<li>{_escape(line)}</li>" for line in lines)
    detail_html = f"<ul class=\"menu-detail\">{detail_items}</ul>" if detail_items else ""
    nutrition_html = _render_nutrition_panel(entry.get("nutrition"))

    badge_class = f"meal-{meal}" if meal in ("breakfast", "lunch", "dinner") else "meal-generic"

    return f"""
      <article class="menu-card {badge_class}">
        <div class="menu-card__header">
          <span class="menu-badge">{_escape(_meal_label(meal))}</span>
          <span class="menu-summary">{_escape(summary)}</span>
        </div>
        {detail_html}
        {nutrition_html}
      </article>
    """


def _group_entries_by_date(entries: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        date_value = str(entry.get("date", "")).strip()
        if not date_value:
            continue
        grouped.setdefault(date_value, []).append(entry)

    ordered: list[tuple[str, list[dict[str, Any]]]] = []
    for date_value in sorted(grouped):
        ordered.append(
            (
                date_value,
                sorted(grouped[date_value], key=lambda item: _meal_sort_key(str(item.get("meal", "")))),
            )
        )
    return ordered


def _day_detail_html(day_entries: list[dict[str, Any]]) -> str:
    if not day_entries:
        return """
          <section class="empty-state empty-state--calendar">
            <h3>この日付のメニューはありません</h3>
            <p>まだ保存されていない日付です。別の日を選んでください。</p>
          </section>
        """

    cards = "\n".join(_render_menu_card(entry) for entry in day_entries)
    return f"""
      <div class="calendar-day-cards">
        {cards}
      </div>
    """


def _build_menu_page(entries: list[dict[str, Any]]) -> str:
    menu_data_json = _json_script_data({"entries": entries})
    now_label = datetime.now(ZoneInfo(JST)).strftime("%Y-%m-%d %H:%M")
    return "".join(
        [
            """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>今後のメニュー</title>
  <style>
    :root {
      --bg: #f6f1e8;
      --panel: rgba(255, 255, 255, 0.88);
      --panel-strong: #ffffff;
      --text: #1f2937;
      --muted: #6b7280;
      --line: rgba(31, 41, 55, 0.12);
      --accent: #f28c28;
      --accent-soft: rgba(242, 140, 40, 0.12);
      --shadow: 0 18px 48px rgba(31, 41, 55, 0.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Noto Sans JP", "Yu Gothic", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(242, 140, 40, 0.18), transparent 34%),
        radial-gradient(circle at top right, rgba(78, 121, 167, 0.16), transparent 28%),
        linear-gradient(180deg, #faf7f2 0%, var(--bg) 100%);
      min-height: 100vh;
    }
    a { color: inherit; }
    .shell {
      max-width: 1080px;
      margin: 0 auto;
      padding: 32px 20px 56px;
    }
    .hero {
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 24px;
      background: var(--panel);
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }
    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 0.88rem;
      font-weight: 700;
      letter-spacing: 0.02em;
    }
    h1 {
      margin: 14px 0 8px;
      font-size: clamp(2rem, 4vw, 3.6rem);
      line-height: 1.05;
    }
    .lead {
      margin: 0;
      color: var(--muted);
      line-height: 1.7;
    }
    .hero-links {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 18px;
    }
    .hero-links a {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 44px;
      padding: 0 16px;
      border-radius: 999px;
      text-decoration: none;
      border: 1px solid var(--line);
      background: var(--panel-strong);
      font-weight: 700;
    }
    .meta {
      margin-top: 12px;
      color: var(--muted);
      font-size: 0.92rem;
    }
    .date-section {
      margin-top: 24px;
      padding-top: 8px;
    }
    .date-section h2 {
      margin: 0 0 12px;
      font-size: 1.35rem;
    }
    .menu-grid {
      display: grid;
      gap: 14px;
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    @media (max-width: 860px) {
      .menu-grid {
        grid-template-columns: 1fr;
      }
    }
    .menu-card {
      border: 1px solid var(--line);
      border-radius: 20px;
      background: var(--panel);
      box-shadow: 0 8px 24px rgba(31, 41, 55, 0.06);
      padding: 16px 18px;
    }
    .menu-card__header {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 12px;
    }
    .menu-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 54px;
      padding: 6px 12px;
      border-radius: 999px;
      color: white;
      font-weight: 800;
      letter-spacing: 0.04em;
      background: #6b7280;
    }
    .meal-breakfast .menu-badge { background: #f4c542; color: #3b2f0f; }
    .meal-lunch .menu-badge { background: #f28c28; }
    .meal-dinner .menu-badge { background: #4e79a7; }
    .menu-summary {
      font-size: 1.05rem;
      font-weight: 700;
    }
    .menu-detail {
      margin: 12px 0 0;
      padding-left: 20px;
      color: var(--text);
      line-height: 1.7;
    }
    .menu-detail li + li {
      margin-top: 4px;
    }
    .nutrition-panel {
      margin-top: 12px;
      border-top: 1px solid var(--line);
      padding-top: 12px;
    }
    .nutrition-panel summary {
      display: inline-flex;
      align-items: center;
      min-height: 38px;
      padding: 0 13px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--panel-strong);
      color: var(--text);
      cursor: pointer;
      font-weight: 800;
      list-style: none;
    }
    .nutrition-panel summary::-webkit-details-marker {
      display: none;
    }
    .nutrition-panel summary::after {
      content: "＋";
      margin-left: 8px;
      color: var(--muted);
    }
    .nutrition-panel[open] summary::after {
      content: "－";
    }
    .nutrition-list {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin: 12px 0 0;
    }
    .nutrition-item {
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.66);
    }
    .nutrition-item dt {
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 700;
    }
    .nutrition-item dd {
      margin: 3px 0 0;
      font-weight: 800;
    }
    .empty-state {
      margin-top: 24px;
      padding: 24px;
      border: 1px dashed var(--line);
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.72);
    }
    .footer {
      margin-top: 24px;
      color: var(--muted);
      font-size: 0.9rem;
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <span class="eyebrow">Dormitory Menu</span>
      <h1>今後のメニュー</h1>
      <p class="lead">保存された今後のメニューを一覧で見られるページです。表示基準日はブラウザ側の JST 日付で決まります。</p>
      <div class="hero-links">
        <a href="../">トップへ</a>
        <a href="./">メニュー一覧</a>
        <a href="../calendar.html">カレンダーで見る</a>
      </div>
      <div class="meta">最終生成: """,
            _escape(now_label),
            """ JST</div>
    </section>
    <section id="menu-results" aria-live="polite"></section>
    <div class="footer">GitHub Pages 向けの静的ページです。</div>
  </main>
  <script id="menu-data" type="application/json">""",
            menu_data_json,
            """</script>
  <script>
    const DATA = JSON.parse(document.getElementById("menu-data").textContent);
    const ENTRIES = DATA.entries || [];
    const MEAL_ORDER = {"breakfast": 0, "lunch": 1, "dinner": 2};
    const NUTRITION_LABELS = {
      energy_kcal: "エネルギー",
      calories_kcal: "エネルギー",
      kcal: "エネルギー",
      protein_g: "たんぱく質",
      fat_g: "脂質",
      carbohydrate_g: "炭水化物",
      carbs_g: "炭水化物",
      salt_g: "食塩相当量",
      sodium_g: "食塩相当量",
    };
    const NUTRITION_UNITS = {
      energy_kcal: "kcal",
      calories_kcal: "kcal",
      kcal: "kcal",
      protein_g: "g",
      fat_g: "g",
      carbohydrate_g: "g",
      carbs_g: "g",
      salt_g: "g",
      sodium_g: "g",
    };
    const NUTRITION_ORDER = [
      "energy_kcal",
      "calories_kcal",
      "kcal",
      "protein_g",
      "fat_g",
      "carbohydrate_g",
      "carbs_g",
      "salt_g",
      "sodium_g",
    ];
    const results = document.getElementById("menu-results");
""",
            _date_adjustment_js(),
            """
    function escapeHtml(text) {
      return String(text)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function mealSortKey(meal) {
      return MEAL_ORDER[meal] ?? 99;
    }

    function groupEntriesByDate(entries) {
      const grouped = new Map();
      for (const entry of entries) {
        const dateValue = String(entry.date || "").trim();
        if (!dateValue) continue;
        if (!grouped.has(dateValue)) {
          grouped.set(dateValue, []);
        }
        grouped.get(dateValue).push(entry);
      }
      return [...grouped.entries()]
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([dateValue, dayEntries]) => [
          dateValue,
          dayEntries.slice().sort((left, right) => mealSortKey(left.meal) - mealSortKey(right.meal)),
        ]);
    }

    function dateLabel(dateString) {
      const date = new Date(`${dateString}T00:00:00+09:00`);
      const label = new Intl.DateTimeFormat("ja-JP", {
        timeZone: "Asia/Tokyo",
        month: "numeric",
        day: "numeric",
        weekday: "short",
      }).format(date);
      return label.replace(/曜日$/, "");
    }

    function mealLabel(meal) {
      return meal === "breakfast" ? "朝ご飯" : meal === "lunch" ? "昼ご飯" : meal === "dinner" ? "夜ご飯" : meal;
    }

    function menuLines(entry) {
      const meal = String(entry.meal || "");
      const menu = entry.menu || {};
      if (meal === "dinner") {
        const lines = [];
        if (menu.a) lines.push(`(A) ${menu.a}`);
        if (menu.b) lines.push(`(B) ${menu.b}`);
        if (Array.isArray(menu.common)) {
          for (const item of menu.common) {
            const value = String(item || "").trim();
            if (value) lines.push(value);
          }
        }
        return lines;
      }
      if (Array.isArray(menu.items)) {
        return menu.items.map((item) => String(item || "").trim()).filter(Boolean);
      }
      return [];
    }

    function nutritionItems(entry) {
      const nutrition = entry.nutrition;
      if (!nutrition || typeof nutrition !== "object" || Array.isArray(nutrition)) return [];
      const keys = [
        ...NUTRITION_ORDER.filter((key) => Object.prototype.hasOwnProperty.call(nutrition, key)),
        ...Object.keys(nutrition).filter((key) => !NUTRITION_ORDER.includes(key)),
      ];
      return keys.flatMap((key) => {
        const rawValue = nutrition[key];
        if (rawValue === null || rawValue === undefined) return [];
        const text = String(rawValue).trim();
        if (!text) return [];
        const unit = NUTRITION_UNITS[key] || "";
        const value = unit && !text.toLowerCase().endsWith(unit.toLowerCase()) ? `${text}${unit}` : text;
        const label = NUTRITION_LABELS[key] || key.replaceAll("_", " ");
        return [[label, value]];
      });
    }

    function renderNutritionPanel(entry) {
      const items = nutritionItems(entry);
      if (!items.length) return "";
      return `
        <details class="nutrition-panel">
          <summary>栄養を見る</summary>
          <dl class="nutrition-list">
            ${items.map(([label, value]) => `
              <div class="nutrition-item">
                <dt>${escapeHtml(label)}</dt>
                <dd>${escapeHtml(value)}</dd>
              </div>
            `).join("")}
          </dl>
        </details>
      `;
    }

    function renderCard(entry) {
      const lines = menuLines(entry);
      const meal = String(entry.meal || "");
      const summary = String(entry.menu_summary || "").trim() || (lines[0] || "");
      const detailHtml = lines.length
        ? `<ul class="menu-detail">${lines.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>`
        : "";
      return `
        <article class="menu-card meal-${escapeHtml(meal)}">
          <div class="menu-card__header">
            <span class="menu-badge">${escapeHtml(mealLabel(meal))}</span>
            <span class="menu-summary">${escapeHtml(summary)}</span>
          </div>
          ${detailHtml}
          ${renderNutritionPanel(entry)}
        </article>
      `;
    }

    function render() {
      const baseDate = currentJstIsoDate();
      const visibleEntries = ENTRIES
        .filter((entry) => String(entry.date || "") >= baseDate)
        .slice()
        .sort((left, right) => {
          const dateCompare = String(left.date || "").localeCompare(String(right.date || ""));
          if (dateCompare !== 0) return dateCompare;
          return mealSortKey(left.meal) - mealSortKey(right.meal);
        });

      if (!visibleEntries.length) {
        results.innerHTML = `
          <section class="empty-state">
            <h2>まだメニューはありません</h2>
            <p>基準日以降のメニューがありません。日付を前に戻すと、保存済みのメニューを見られます。</p>
          </section>
        `;
        return;
      }

      const sections = groupEntriesByDate(visibleEntries).map(([dateValue, dayEntries]) => `
        <section class="date-section">
          <h2>${escapeHtml(dateLabel(dateValue))}</h2>
          <div class="menu-grid">
            ${dayEntries.map((entry) => renderCard(entry)).join("")}
          </div>
        </section>
      `);

      results.innerHTML = sections.join("");
    }

    render();
  </script>
</body>
</html>
        """
        ]
    )


def _build_calendar_page(entries: list[dict[str, Any]]) -> str:
    grouped = _group_entries_by_date(entries)
    day_payload: dict[str, dict[str, Any]] = {}
    for entry_date, day_entries in grouped:
        day_payload[entry_date] = {
            "label": _date_label(entry_date),
            "count": len(day_entries),
            "cards_html": "".join(_render_menu_card(entry) for entry in day_entries),
        }

    calendar_data = {
        "days": day_payload,
    }
    calendar_data_json = _json_script_data(calendar_data)

    now_label = datetime.now(ZoneInfo(JST)).strftime("%Y-%m-%d %H:%M")

    return "".join(
        [
            """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>メニューカレンダー</title>
  <style>
    :root {
      --bg: #f6f1e8;
      --panel: rgba(255, 255, 255, 0.88);
      --panel-strong: #ffffff;
      --text: #1f2937;
      --muted: #6b7280;
      --line: rgba(31, 41, 55, 0.12);
      --accent: #4e79a7;
      --accent-soft: rgba(78, 121, 167, 0.12);
      --shadow: 0 18px 48px rgba(31, 41, 55, 0.12);
      --today: #f28c28;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Noto Sans JP", "Yu Gothic", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(78, 121, 167, 0.18), transparent 34%),
        radial-gradient(circle at top right, rgba(242, 140, 40, 0.16), transparent 28%),
        linear-gradient(180deg, #faf7f2 0%, var(--bg) 100%);
      min-height: 100vh;
    }
    a { color: inherit; }
    button { font: inherit; }
    .shell {
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 20px 56px;
    }
    .hero {
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 24px;
      background: var(--panel);
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }
    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 0.88rem;
      font-weight: 700;
      letter-spacing: 0.02em;
    }
    h1 {
      margin: 14px 0 8px;
      font-size: clamp(2rem, 4vw, 3.6rem);
      line-height: 1.05;
    }
    .lead {
      margin: 0;
      color: var(--muted);
      line-height: 1.7;
    }
    .hero-links {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 18px;
    }
    .hero-links a {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 44px;
      padding: 0 16px;
      border-radius: 999px;
      text-decoration: none;
      border: 1px solid var(--line);
      background: var(--panel-strong);
      font-weight: 700;
    }
    .meta {
      margin-top: 12px;
      color: var(--muted);
      font-size: 0.92rem;
    }
    .calendar-layout {
      display: grid;
      grid-template-columns: minmax(0, 1.05fr) minmax(320px, 0.95fr);
      gap: 18px;
      margin-top: 24px;
      align-items: start;
    }
    @media (max-width: 980px) {
      .calendar-layout {
        grid-template-columns: 1fr;
      }
    }
    @media (max-width: 640px) {
      .calendar-panel,
      .detail-panel {
        padding: 16px;
      }
      .weekday-row,
      .calendar-grid {
        gap: 6px;
      }
      .calendar-cell {
        min-height: 68px;
        padding: 8px;
      }
    }
    .calendar-panel,
    .detail-panel {
      border: 1px solid var(--line);
      border-radius: 24px;
      background: var(--panel);
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
      overflow: hidden;
    }
    .calendar-panel {
      padding: 20px;
    }
    .detail-panel {
      padding: 20px;
    }
    .calendar-toolbar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }
    .calendar-toolbar__group {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .calendar-toolbar button {
      min-height: 42px;
      padding: 0 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: var(--panel-strong);
      color: var(--text);
      cursor: pointer;
      font-weight: 700;
    }
    .month-label {
      font-weight: 800;
      font-size: 1.1rem;
    }
    @media (max-width: 640px) {
      .calendar-toolbar {
        flex-direction: column;
        align-items: stretch;
      }
      .calendar-toolbar__group {
        width: 100%;
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }
      .calendar-toolbar button {
        width: 100%;
        padding: 0 10px;
      }
      .month-label {
        text-align: left;
      }
    }
    .weekday-row,
    .calendar-grid {
      display: grid;
      grid-template-columns: repeat(7, minmax(0, 1fr));
      gap: 8px;
    }
    .weekday-row {
      margin-bottom: 8px;
      color: var(--muted);
      font-weight: 700;
      font-size: 0.88rem;
    }
    .weekday-row div {
      text-align: center;
      padding: 6px 0;
    }
    .calendar-grid {
      align-items: stretch;
    }
    .calendar-cell {
      min-height: 76px;
      border: 1px solid rgba(31, 41, 55, 0.08);
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.82);
      padding: 10px;
      text-align: left;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease;
    }
    .calendar-cell:hover {
      transform: translateY(-1px);
      box-shadow: 0 8px 18px rgba(31, 41, 55, 0.08);
    }
    .calendar-cell.is-empty {
      cursor: default;
      background: transparent;
      border-style: dashed;
      border-color: transparent;
      box-shadow: none;
    }
    .calendar-cell__day {
      font-size: 0.96rem;
      font-weight: 800;
    }
    .calendar-cell__dot {
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: transparent;
    }
    .calendar-cell.has-data .calendar-cell__dot {
      background: var(--accent);
    }
    .calendar-cell.is-today {
      border-color: rgba(242, 140, 40, 0.65);
    }
    .calendar-cell.is-selected {
      border-color: var(--today);
      box-shadow: 0 0 0 2px rgba(242, 140, 40, 0.14) inset;
    }
    .selected-date {
      margin: 0 0 4px;
      font-size: 1.4rem;
    }
    .selected-meta {
      margin: 0 0 14px;
      color: var(--muted);
      line-height: 1.6;
    }
    .calendar-day-cards {
      display: grid;
      gap: 12px;
    }
    .menu-card {
      border: 1px solid var(--line);
      border-radius: 20px;
      background: var(--panel-strong);
      box-shadow: 0 8px 24px rgba(31, 41, 55, 0.06);
      padding: 16px 18px;
    }
    .menu-card__header {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 12px;
      margin-bottom: 10px;
    }
    .menu-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 54px;
      padding: 6px 12px;
      border-radius: 999px;
      color: white;
      font-weight: 800;
      letter-spacing: 0.04em;
      background: #6b7280;
    }
    .meal-breakfast .menu-badge { background: #f4c542; color: #3b2f0f; }
    .meal-lunch .menu-badge { background: #f28c28; }
    .meal-dinner .menu-badge { background: #4e79a7; }
    .menu-summary {
      font-size: 1.04rem;
      font-weight: 700;
    }
    .menu-detail {
      margin: 0;
      padding-left: 20px;
      line-height: 1.7;
    }
    .menu-detail li + li {
      margin-top: 4px;
    }
    .nutrition-panel {
      margin-top: 12px;
      border-top: 1px solid var(--line);
      padding-top: 12px;
    }
    .nutrition-panel summary {
      display: inline-flex;
      align-items: center;
      min-height: 38px;
      padding: 0 13px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--panel-strong);
      color: var(--text);
      cursor: pointer;
      font-weight: 800;
      list-style: none;
    }
    .nutrition-panel summary::-webkit-details-marker {
      display: none;
    }
    .nutrition-panel summary::after {
      content: "＋";
      margin-left: 8px;
      color: var(--muted);
    }
    .nutrition-panel[open] summary::after {
      content: "－";
    }
    .nutrition-list {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin: 12px 0 0;
    }
    .nutrition-item {
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.66);
    }
    .nutrition-item dt {
      color: var(--muted);
      font-size: 0.82rem;
      font-weight: 700;
    }
    .nutrition-item dd {
      margin: 3px 0 0;
      font-weight: 800;
    }
    .empty-state {
      margin-top: 10px;
      padding: 18px;
      border: 1px dashed var(--line);
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.72);
    }
    .empty-state h3 {
      margin: 0 0 8px;
    }
    .empty-state p {
      margin: 0;
      color: var(--muted);
      line-height: 1.7;
    }
    .footer {
      margin-top: 24px;
      color: var(--muted);
      font-size: 0.9rem;
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <span class="eyebrow">Dormitory Menu</span>
      <h1>カレンダーで見る</h1>
      <p class="lead">日付を選ぶと、その日の朝・昼・夜ごはんを下に表示します。基準日はブラウザの JST 日付で決まります。</p>
      <div class="hero-links">
        <a href="./menu/">メニュー一覧</a>
        <a href="./">トップへ</a>
      </div>
      <div class="meta">最終生成: """,
            _escape(now_label),
            """ JST</div>
    </section>

    <section class="calendar-layout" aria-label="メニューカレンダー">
      <section class="calendar-panel">
        <div class="calendar-toolbar">
          <div class="calendar-toolbar__group">
            <button type="button" id="prev-month" aria-label="前の月">＜</button>
            <button type="button" id="go-today" aria-label="今日">今日</button>
            <button type="button" id="next-month" aria-label="次の月">＞</button>
          </div>
          <div class="month-label" id="month-label"></div>
        </div>
        <div class="weekday-row" aria-hidden="true">
          <div>月</div>
          <div>火</div>
          <div>水</div>
          <div>木</div>
          <div>金</div>
          <div>土</div>
          <div>日</div>
        </div>
        <div class="calendar-grid" id="calendar-grid"></div>
      </section>

      <section class="detail-panel" aria-live="polite">
        <h2 class="selected-date" id="selected-date-label"></h2>
        <p class="selected-meta" id="selected-date-meta"></p>
        <div id="selected-day-content"></div>
      </section>
    </section>

    <div class="footer">GitHub Pages 向けの静的ページです。</div>
  </main>

  <script id="calendar-data" type="application/json">""",
            calendar_data_json,
            """</script>
  <script>
    const WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"];
    const DATA = JSON.parse(document.getElementById("calendar-data").textContent);
    const DAYS = DATA.days || {};

    const monthLabel = document.getElementById("month-label");
    const calendarGrid = document.getElementById("calendar-grid");
    const selectedDateLabel = document.getElementById("selected-date-label");
    const selectedDateMeta = document.getElementById("selected-date-meta");
    const selectedDayContent = document.getElementById("selected-day-content");

""",
            _date_adjustment_js(),
            """
    let currentBaseDate = currentJstIsoDate();
    let currentMonth = startOfMonth(currentBaseDate);
    let selectedDate = currentBaseDate;

    function parseDate(dateString) {
      const [year, month, day] = dateString.split("-").map(Number);
      return new Date(Date.UTC(year, month - 1, day));
    }

    function isoDate(date) {
      return date.toISOString().slice(0, 10);
    }

    function startOfMonth(dateString) {
      const date = parseDate(dateString);
      return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), 1));
    }

    function formatDateLabel(dateString) {
      const date = parseDate(dateString);
      const weekday = WEEKDAYS[(date.getUTCDay() + 6) % 7];
      return `${date.getUTCMonth() + 1}/${date.getUTCDate()} (${weekday})`;
    }

    function formatMonthLabel(date) {
      return new Intl.DateTimeFormat("ja-JP", {
        year: "numeric",
        month: "long",
        timeZone: "UTC",
      }).format(date);
    }

    function shiftMonth(date, amount) {
      return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + amount, 1));
    }

    function renderCalendar() {
      monthLabel.textContent = formatMonthLabel(currentMonth);
      calendarGrid.innerHTML = "";

      const firstWeekday = (currentMonth.getUTCDay() + 6) % 7;
      const daysInMonth = new Date(Date.UTC(currentMonth.getUTCFullYear(), currentMonth.getUTCMonth() + 1, 0)).getUTCDate();

      for (let index = 0; index < firstWeekday; index += 1) {
        const empty = document.createElement("div");
        empty.className = "calendar-cell is-empty";
        calendarGrid.appendChild(empty);
      }

      for (let day = 1; day <= daysInMonth; day += 1) {
        const cellDate = new Date(Date.UTC(currentMonth.getUTCFullYear(), currentMonth.getUTCMonth(), day));
        const dateString = isoDate(cellDate);
        const cell = document.createElement("button");
        cell.type = "button";
        cell.className = "calendar-cell";
        cell.innerHTML = `
          <div class="calendar-cell__day">${day}</div>
          <div class="calendar-cell__dot"></div>
        `;

        if (dateString === currentBaseDate) {
          cell.classList.add("is-today");
        }
        if (dateString === selectedDate) {
          cell.classList.add("is-selected");
        }
        if (DAYS[dateString]) {
          cell.classList.add("has-data");
        }

        cell.addEventListener("click", () => {
          selectedDate = dateString;
          currentMonth = startOfMonth(dateString);
          renderAll();
        });

        calendarGrid.appendChild(cell);
      }
    }

    function renderSelectedDay() {
      const day = DAYS[selectedDate];
      selectedDateLabel.textContent = formatDateLabel(selectedDate);
      selectedDateMeta.textContent = day
        ? `${day.count} 件のメニューがあります。`
        : "この日付にはまだメニューがありません。";

      if (!day) {
        selectedDayContent.innerHTML = `
          <section class="empty-state">
            <h3>メニューがありません</h3>
            <p>別の日付を選ぶと、その日のメニューを表示できます。</p>
          </section>
        `;
        return;
      }

      selectedDayContent.innerHTML = `
        <div class="calendar-day-cards">
          ${day.cards_html}
        </div>
      `;
    }

    function renderAll() {
      renderCalendar();
      renderSelectedDay();
    }

    document.getElementById("prev-month").addEventListener("click", () => {
      currentMonth = shiftMonth(currentMonth, -1);
      renderCalendar();
    });
    document.getElementById("next-month").addEventListener("click", () => {
      currentMonth = shiftMonth(currentMonth, 1);
      renderCalendar();
    });
    document.getElementById("go-today").addEventListener("click", () => {
      currentBaseDate = currentJstIsoDate();
      selectedDate = currentBaseDate;
      currentMonth = startOfMonth(currentBaseDate);
      renderAll();
    });

    renderAll();
  </script>
</body>
</html>
        """
        ]
    )


def _build_root_page() -> str:
    return """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dormitory Bot</title>
  <meta http-equiv="refresh" content="0; url=./menu/">
  <style>
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Noto Sans JP", "Yu Gothic", sans-serif;
      background: #f6f1e8;
      color: #1f2937;
    }
    a {
      color: #f28c28;
      font-weight: 700;
    }
  </style>
</head>
<body>
  <p>メニュー一覧へ移動しています。<a href="./menu/">移動しない場合はこちら</a></p>
</body>
</html>
"""


def write_menu_site(store_path: Path = DEFAULT_STORE_PATH, website_dir: Path = DEFAULT_WEBSITE_DIR) -> None:
    data = load_store(store_path)
    entries = [normalize_entry(entry) for entry in data.get("entries", []) if isinstance(entry, dict)]

    menu_dir = website_dir / "menu"
    menu_dir.mkdir(parents=True, exist_ok=True)
    website_dir.mkdir(parents=True, exist_ok=True)

    menu_html = _build_menu_page(entries)
    (menu_dir / "index.html").write_text(menu_html, encoding="utf-8")
    (website_dir / "calendar.html").write_text(_build_calendar_page(entries), encoding="utf-8")
    (website_dir / "index.html").write_text(_build_root_page(), encoding="utf-8")
