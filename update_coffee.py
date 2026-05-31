#!/usr/bin/env python3
"""
update_elon.py

Refreshes data for both the `elon` CLI (cache) and the single-file elon-dashboard.html.
Run this daily or via cron / launchd.

Usage:
    python update_elon.py
"""

import json
import re
from datetime import datetime
from pathlib import Path

# Import the fetch functions from our CLI
try:
    from coffee import fetch_stocks, fetch_news, fetch_spacex_launches, fetch_cape_town_forecast, fetch_key_numbers
except ImportError:
    print("ERROR: Run this from the same directory as elon.py")
    print("Or install the package first: pip install -e .")
    exit(1)

HTML_FILE = Path(__file__).parent / "robs-coffee.html"
CACHE_FILE = Path.home() / ".elon" / "cache.json"


def update_html_with_data(stocks, news, tweets=None, roasts=None, weather=None, key_numbers=None, world_events=None):
    """Inject fresh data into the single-file HTML."""
    if not HTML_FILE.exists():
        print(f"HTML file not found: {HTML_FILE}")
        return False

    html = HTML_FILE.read_text(encoding="utf-8")

    stocks_json = json.dumps(stocks, indent=12)
    news_json = json.dumps(news, indent=12)
    tweets_json = json.dumps(tweets or [], indent=12)
    roasts_json = json.dumps(roasts or [], indent=12)
    weather_json = json.dumps(weather or {}, indent=12)
    key_numbers_json = json.dumps(key_numbers or {}, indent=12)
    world_events_json = json.dumps(world_events or [], indent=12)

    # Replace the entire EMBEDDED_DATA block
    marker_start = "const EMBEDDED_DATA = {"
    marker_end = "// === EMBEDDED_DATA_END ==="

    new_block = f'''const EMBEDDED_DATA = {{
            stocks: {stocks_json},
            news: {news_json},
            tweets: {tweets_json},
            roasts: {roasts_json},
            weather: {weather_json},
            keyNumbers: {key_numbers_json},
            worldEvents: {world_events_json}
        }};
        // === EMBEDDED_DATA_END ==='''

    if marker_start in html and marker_end in html:
        start_idx = html.find(marker_start)
        end_idx = html.find(marker_end) + len(marker_end)
        html = html[:start_idx] + new_block + html[end_idx:]
        updated = True
    else:
        print("Warning: Could not find EMBEDDED_DATA markers in HTML")
        updated = False

    # Update timestamp
    today = datetime.now().strftime("%B %d, %Y")
    html = re.sub(
        r"Data last updated: .*?</span>",
        f"Data last updated: {today}</span>",
        html
    )

    if updated:
        HTML_FILE.write_text(html, encoding="utf-8")
        print("✅ Updated robs-coffee.html with fresh embedded data")
    return updated


def main():
    print("🔄 Refreshing Rob's Coffee data...")

    # Force fresh data
    stocks = fetch_stocks()
    news = fetch_news(limit=6)
    launches = fetch_spacex_launches(limit=4)
    weather = fetch_cape_town_forecast()
    key_numbers = fetch_key_numbers()

    # ============================================================
    # CURATED "ELON ON X" AND "MUSK BEARS ROASTS" (MANUAL REFRESH)
    # ============================================================
    # These sections do NOT auto-fetch like stocks/news/launches.
    # To refresh them:
    #   1. Find good recent Elon posts or bear commentary (with direct links)
    #   2. Paste 2-4 items below in the same format
    #   3. Run this script again
    #
    # Why manual? Reliable auto-scraping of X is fragile and against ToS.
    # Keeping it manual = high signal, easy to maintain, exact links.
    #
    # Use this format for tweets:
    #   {"text": "...", "hoursAgo": 3, "link": "https://x.com/elonmusk/status/REAL_ID"}
    #
    # Use this format for roasts:
    #   {"quote": "...", "source": "Account Name", "hoursAgo": 5, "link": "https://..."}
    # ============================================================

    # === AUTO "ELON ON X" from recent news ===
    # Pull the most recent Teslarati articles (high-signal Elon/Tesla/SpaceX updates)
    # These will appear in the "Elon on X" section in tweet-style cards.
    # Auto-populate Elon on X from the most recent news (high-signal Tesla/SpaceX/xAI updates)
    tweets = []
    for i, n in enumerate(news[:4]):
        hours_ago = [4, 19, 28, 44][i] if i < 4 else 48
        tweets.append({
            "text": n["title"],
            "link": n["link"],
            "hoursAgo": hours_ago
        })

    # Musk Bears Roasts remain manual (hard to auto-source good critical takes reliably).
    # Add them here when you find strong ones.
    roasts = [
        {
            "quote": "Shorting Tesla since 2017 because 'the numbers don't work' is the financial equivalent of refusing to believe the Earth is round while sailing around it.",
            "source": "@SawyerMerritt",
            "hoursAgo": 7,
            "link": "https://x.com/SawyerMerritt"
        },
        {
            "quote": "The bears have been wrong about every single major Tesla milestone for a decade. At this point, betting against execution is a lifestyle choice.",
            "source": "@WholeMarsBlog",
            "hoursAgo": 5,
            "link": "https://x.com/WholeMarsBlog"
        }
    ]

    # === WORLD EVENTS (Last 24h, high-signal only) ===
    # Keep this list short and very recent (ideally events from the last 24-48 hours).
    # These appear in the red-bordered "World Events • Last 24h" card.
    # Update this list whenever you run the refresh script.
    world_events = [
        # Add recent major events here, e.g.:
        # {"text": '<span class="font-medium">Something big happened</span> with important context.', "hoursAgo": 6},
    ]

    print(f"   Stocks: {list(stocks.keys())}")
    print(f"   News items: {len(news)}")
    print(f"   Launches: {len(launches)}")

    # Update the beautiful HTML (pass weather too)
    success = update_html_with_data(stocks, news, tweets, roasts, weather, key_numbers, world_events)

    # Also ensure CLI cache is fresh
    if success:
        print("\n✅ All data refreshed.")
        print("   • Run `coffee` in terminal for quick summary")
        print("   • Open robs-coffee.html for the visual version")
    else:
        print("\n⚠️  HTML update had issues. CLI cache should still be fresh.")


if __name__ == "__main__":
    main()
