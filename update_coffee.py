#!/usr/bin/env python3
"""Refresh embedded data inside robs-coffee.html (and copy to index.html)."""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from coffee import (
    fetch_calendar,
    fetch_cape_town_forecast,
    fetch_key_numbers,
    fetch_news,
    fetch_spacex_launches,
    fetch_stocks,
    fetch_world_events,
    now_sast,
)

HTML_FILE = Path(__file__).parent / "robs-coffee.html"
INDEX_FILE = Path(__file__).parent / "index.html"
DATA_FILE = Path(__file__).parent / "data.json"


def update_html(payload: dict) -> bool:
    if not HTML_FILE.exists():
        print(f"HTML file not found: {HTML_FILE}")
        return False

    html = HTML_FILE.read_text(encoding="utf-8")
    marker_start = "const EMBEDDED_DATA = {"
    marker_end = "// === EMBEDDED_DATA_END ==="
    if marker_start not in html or marker_end not in html:
        print("Warning: Could not find EMBEDDED_DATA markers in HTML")
        return False

    block = (
        "const EMBEDDED_DATA = "
        + json.dumps(payload, indent=4, ensure_ascii=False)
        + ";\n        "
        + marker_end
    )
    start_idx = html.find(marker_start)
    end_idx = html.find(marker_end) + len(marker_end)
    HTML_FILE.write_text(html[:start_idx] + block + html[end_idx:], encoding="utf-8")
    shutil.copyfile(HTML_FILE, INDEX_FILE)
    DATA_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Updated robs-coffee.html, index.html, and data.json")
    return True


def main() -> int:
    print("Refreshing Rob's Coffee data...")
    stocks = fetch_stocks(use_cache=False)
    if not stocks:
        print("ERROR: stock fetch failed. Aborting so we do not bake empty prices.")
        return 1

    news = fetch_news(limit=6, use_cache=False)
    launches = fetch_spacex_launches(limit=5, use_cache=False)
    weather = fetch_cape_town_forecast(use_cache=False)
    key_numbers = fetch_key_numbers(use_cache=False)
    world_events = fetch_world_events(limit=5, use_cache=False)
    calendar_events = fetch_calendar()

    payload = {
        "updatedAt": now_sast().isoformat(timespec="minutes"),
        "stocks": stocks,
        "news": news,
        "tweets": [],
        "roasts": [],
        "weather": weather,
        "keyNumbers": key_numbers,
        "worldEvents": world_events,
        "launches": launches,
        "companyNews": news,
        "calendar": calendar_events,
    }

    print(f"   Stocks: {list(stocks.keys())}")
    print(f"   News: {len(news)}")
    print(f"   Launches: {len(launches)}")
    print(f"   World events: {len(world_events)}")
    print(f"   Calendar: {len(calendar_events)}")
    print(f"   Key numbers: {key_numbers}")

    if not update_html(payload):
        return 1

    print("All data refreshed. Open robs-coffee.html or run: npm run deploy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
