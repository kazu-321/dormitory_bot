from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .config import BASE_DIR, JST, MEAL_LABELS_JA, DEFAULT_STORE_PATH
from .store import load_store, menu_to_lines, normalize_entry, summarize_menu


DEFAULT_WEBSITE_DIR = BASE_DIR / "website"


def _date_label(entry_date: str) -> str:
    dt = datetime.fromisoformat(f"{entry_date}T00:00:00+09:00")
    weekdays = ("月", "火", "水", "木", "金", "土", "日")
    return f"{dt.month}/{dt.day} ({weekdays[dt.weekday()]})"


def _meal_label(meal: str) -> str:
    return MEAL_LABELS_JA.get(meal, meal)


def _escape(text: str) -> str:
    return html.escape(text, quote=True)


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

    badge_class = f"meal-{meal}" if meal in ("breakfast", "lunch", "dinner") else "meal-generic"

    return f"""
      <article class="menu-card {badge_class}">
        <div class="menu-card__header">
          <span class="menu-badge">{_escape(_meal_label(meal))}</span>
          <span class="menu-summary">{_escape(summary)}</span>
        </div>
        {detail_html}
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
                sorted(grouped[date_value], key=lambda item: ("breakfast", "lunch", "dinner").index(str(item.get("meal", "breakfast"))) if str(item.get("meal", "")) in ("breakfast", "lunch", "dinner") else 99),
            )
        )
    return ordered


def _build_menu_page(entries: list[dict[str, Any]]) -> str:
    if not entries:
        body = """
        <section class="empty-state">
          <h2>まだメニューはありません</h2>
          <p>新しいメニューが保存されると、このページが自動更新されます。</p>
        </section>
        """
    else:
        sections = []
        for entry_date, day_entries in _group_entries_by_date(entries):
            cards = "\n".join(_render_menu_card(entry) for entry in day_entries)
            sections.append(
                f"""
                <section class="date-section">
                  <h2>{_escape(_date_label(entry_date))}</h2>
                  <div class="menu-grid">
                    {cards}
                  </div>
                </section>
                """
            )
        body = "\n".join(sections)

    now_label = datetime.now(ZoneInfo(JST)).strftime("%Y-%m-%d %H:%M")

    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>今後のメニュー</title>
  <style>
    :root {{
      --bg: #f6f1e8;
      --panel: rgba(255, 255, 255, 0.88);
      --panel-strong: #ffffff;
      --text: #1f2937;
      --muted: #6b7280;
      --line: rgba(31, 41, 55, 0.12);
      --accent: #f28c28;
      --accent-soft: rgba(242, 140, 40, 0.12);
      --shadow: 0 18px 48px rgba(31, 41, 55, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Noto Sans JP", "Yu Gothic", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(242, 140, 40, 0.18), transparent 34%),
        radial-gradient(circle at top right, rgba(78, 121, 167, 0.16), transparent 28%),
        linear-gradient(180deg, #faf7f2 0%, var(--bg) 100%);
      min-height: 100vh;
    }}
    a {{ color: inherit; }}
    .shell {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 32px 20px 56px;
    }}
    .hero {{
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 24px;
      background: var(--panel);
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }}
    .eyebrow {{
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
    }}
    h1 {{
      margin: 14px 0 8px;
      font-size: clamp(2rem, 4vw, 3.6rem);
      line-height: 1.05;
    }}
    .lead {{
      margin: 0;
      color: var(--muted);
      line-height: 1.7;
    }}
    .hero-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 18px;
    }}
    .hero-links a {{
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
    }}
    .meta {{
      margin-top: 12px;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .date-section {{
      margin-top: 24px;
      padding-top: 8px;
    }}
    .date-section h2 {{
      margin: 0 0 12px;
      font-size: 1.35rem;
    }}
    .menu-grid {{
      display: grid;
      gap: 14px;
    }}
    .menu-card {{
      border: 1px solid var(--line);
      border-radius: 20px;
      background: var(--panel);
      box-shadow: 0 8px 24px rgba(31, 41, 55, 0.06);
      padding: 16px 18px;
    }}
    .menu-card__header {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 12px;
    }}
    .menu-badge {{
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
    }}
    .meal-breakfast .menu-badge {{ background: #f4c542; color: #3b2f0f; }}
    .meal-lunch .menu-badge {{ background: #f28c28; }}
    .meal-dinner .menu-badge {{ background: #4e79a7; }}
    .menu-summary {{
      font-size: 1.05rem;
      font-weight: 700;
    }}
    .menu-detail {{
      margin: 12px 0 0;
      padding-left: 20px;
      color: var(--text);
      line-height: 1.7;
    }}
    .menu-detail li + li {{
      margin-top: 4px;
    }}
    .empty-state {{
      margin-top: 24px;
      padding: 24px;
      border: 1px dashed var(--line);
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.72);
    }}
    .footer {{
      margin-top: 24px;
      color: var(--muted);
      font-size: 0.9rem;
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <span class="eyebrow">Dormitory Menu</span>
      <h1>今後のメニュー</h1>
      <p class="lead">保存された今後のメニューを一覧で見られるページです。メニューが更新されると HTML も自動で更新されます。</p>
      <div class="hero-links">
        <a href="../">トップへ</a>
        <a href="./">メニュー一覧</a>
      </div>
      <div class="meta">最終生成: {_escape(now_label)} JST</div>
    </section>
    {body}
    <div class="footer">GitHub Pages 向けの静的ページです。</div>
  </main>
</body>
</html>
"""


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
    (website_dir / "index.html").write_text(_build_root_page(), encoding="utf-8")

