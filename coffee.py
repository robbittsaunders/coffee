#!/usr/bin/env python3
"""
Rob's Coffee (CLI)

Personal daily briefing: stocks, Cape Town weather, SpaceX, world events, Elon-ecosystem news.

Usage:
    python3 coffee.py
    python3 coffee.py --refresh
    python3 coffee.py --launches
"""

from __future__ import annotations

import calendar
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yfinance as yf
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

CACHE_DIR = Path.home() / ".robs-coffee"
CACHE_FILE = CACHE_DIR / "cache.json"
CACHE_TTL_MINUTES = 45

TICKERS = ["TSLA", "NVDA", "MU"]
NEWS_RSS_URLS = [
    ("https://www.teslarati.com/feed/", "Teslarati"),
    ("https://insideevs.com/feed/", "InsideEVs"),
    ("https://www.nasaspaceflight.com/feed/", "NASASpaceflight"),
    ("https://cleantechnica.com/feed/", "CleanTechnica"),
    ("https://spacenews.com/feed/", "SpaceNews"),
]
NEWS_KEYWORDS = (
    "tesla", "spacex", "starship", "starlink", "cybertruck", "optimus",
    "xai", "grok", "neuralink", "boring", "elon", "fsd", "robotaxi",
)
WORLD_RSS = "https://feeds.bbci.co.uk/news/world/rss.xml"
LL2_UPCOMING = "https://ll.thespacedevs.com/2.2.0/launch/upcoming/"
SPACEX_LSP_ID = 121  # SpaceX on The Space Devs

SAST = timezone(timedelta(hours=2))
console = Console()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_sast() -> datetime:
    return datetime.now(SAST)


# ------------------------------------------------------------------
# Caching
# ------------------------------------------------------------------
def load_cache() -> Dict[str, Any]:
    if not CACHE_FILE.exists():
        return {}
    try:
        data = json.loads(CACHE_FILE.read_text())
        ts = data.get("_timestamp", 0)
        if (datetime.now().timestamp() - ts) < (CACHE_TTL_MINUTES * 60):
            return data
    except Exception:
        pass
    return {}


def save_cache(data: Dict[str, Any]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data["_timestamp"] = datetime.now().timestamp()
    CACHE_FILE.write_text(json.dumps(data, indent=2, default=str))


def cache_get(key: str, use_cache: bool) -> Any:
    if not use_cache:
        return None
    return load_cache().get(key)


def cache_put(key: str, value: Any) -> None:
    cache = load_cache() or {}
    cache[key] = value
    save_cache(cache)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def hours_ago(pub_date: str) -> Optional[int]:
    if not pub_date:
        return None
    try:
        dt = parsedate_to_datetime(pub_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = now_utc() - dt.astimezone(timezone.utc)
        return max(0, int(delta.total_seconds() // 3600))
    except Exception:
        return None


def fmt_pct(value: float, digits: int = 1) -> str:
    return f"{value:+.{digits}f}%"


def pct_change(new: float, old: float) -> float:
    if not old:
        return 0.0
    return ((new - old) / old) * 100.0


def yf_closes(symbol: str, period: str = "3y"):
    hist = yf.Ticker(symbol).history(period=period, auto_adjust=True)
    if hist is None or hist.empty or "Close" not in hist:
        return None
    return hist["Close"].dropna()


def format_sast(utc_iso: str, fuzzy: bool = False) -> str:
    """UTC ISO -> 'Friday 20 June 14h00'. Midnight TBD dates drop the fake time."""
    if not utc_iso or "*" in utc_iso:
        return utc_iso or "TBD"
    try:
        if "T" in utc_iso:
            dt = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))
        else:
            dt = datetime.strptime(utc_iso[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        sast = dt.astimezone(SAST)
        weekday = calendar.day_name[sast.weekday()]
        month = calendar.month_name[sast.month]
        utc = dt.astimezone(timezone.utc)
        if fuzzy and utc.hour == 0 and utc.minute == 0:
            return f"{weekday} {sast.day} {month} (TBD)"
        return f"{weekday} {sast.day} {month} {sast.strftime('%Hh%M')}"
    except Exception:
        return utc_iso[:16]


# ------------------------------------------------------------------
# Data fetchers
# ------------------------------------------------------------------
def fetch_stocks(use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
    cached = cache_get("stocks", use_cache)
    if cached:
        return cached

    result: Dict[str, Dict[str, Any]] = {}
    try:
        tickers = yf.Tickers(" ".join(TICKERS))
        hist = tickers.history(period="3y", auto_adjust=True, progress=False)
        for symbol in TICKERS:
            try:
                closes = hist[("Close", symbol)].dropna()
                if len(closes) < 2:
                    continue
                latest = float(closes.iloc[-1])
                prev_close = float(closes.iloc[-2])
                idx_3d = min(3, len(closes) - 1)
                idx_1m = min(20, len(closes) - 1)
                idx_12m = min(252, len(closes) - 1)
                result[symbol] = {
                    "price": round(latest, 2),
                    "change_1d": round(pct_change(latest, prev_close), 2),
                    "change_3d": round(pct_change(latest, float(closes.iloc[-idx_3d])), 2),
                    "change_1m": round(pct_change(latest, float(closes.iloc[-idx_1m])), 2),
                    "change_12m": round(pct_change(latest, float(closes.iloc[-idx_12m])), 2),
                    "change_3y": round(pct_change(latest, float(closes.iloc[0])), 2),
                    "updated": datetime.now().isoformat(),
                }
            except Exception:
                continue
    except Exception as e:
        console.print(f"[red]Stock fetch error: {e}[/red]")

    if result:
        cache_put("stocks", result)
    return result


def fetch_cape_town_forecast(use_cache: bool = True) -> Dict[str, Any]:
    cached = cache_get("cape_town_forecast", use_cache)
    if cached:
        return cached

    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=-33.9249&longitude=18.4241"
            "&hourly=temperature_2m,weather_code,wind_speed_10m,wind_direction_10m,cloud_cover,precipitation"
            "&timezone=Africa/Johannesburg"
        )
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
        data = resp.json()

        def weather_desc(code: int) -> str:
            mapping = {
                0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Fog", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
            }
            return mapping.get(code, "Mixed")

        forecast = {}
        for hours in [1, 3, 6, 12, 24]:
            idx = hours
            forecast[f"+{hours}h"] = {
                "temp": round(data["hourly"]["temperature_2m"][idx], 1),
                "condition": weather_desc(data["hourly"]["weather_code"][idx]),
                "wind_speed": round(data["hourly"]["wind_speed_10m"][idx], 1),
                "wind_dir_deg": round(data["hourly"]["wind_direction_10m"][idx]),
                "cloud": data["hourly"]["cloud_cover"][idx],
                "rain": round(data["hourly"]["precipitation"][idx], 1),
            }
        cache_put("cape_town_forecast", forecast)
        return forecast
    except Exception as e:
        console.print(f"[yellow]Cape Town weather warning: {e}[/yellow]")
        return {}


def _index_move(symbol: str, period: str = "10d") -> Optional[Dict[str, float]]:
    closes = yf_closes(symbol, period=period)
    if closes is None or len(closes) < 2:
        return None
    latest = float(closes.iloc[-1])
    prev = float(closes.iloc[-2])
    week = float(closes.iloc[0])
    return {
        "price": latest,
        "change_1d": pct_change(latest, prev),
        "change_1w": pct_change(latest, week),
    }


def fetch_key_numbers(use_cache: bool = True) -> Dict[str, str]:
    cached = cache_get("key_numbers", use_cache)
    if cached:
        return cached

    out: Dict[str, str] = {}

    zar = _index_move("ZAR=X")
    if zar:
        out["usdZar"] = f"{zar['price']:.2f}"
        out["usdZarWeek"] = fmt_pct(zar["change_1w"])
        out["usdZarLabel"] = "rand weaker" if zar["change_1w"] > 0 else "rand stronger"

    btc = _index_move("BTC-USD")
    if btc:
        out["btc"] = f"{btc['price']:.0f}"
        out["btcWeek"] = fmt_pct(btc["change_1w"])

    jse = _index_move("^J203.JO")
    if jse:
        out["jse"] = fmt_pct(jse["change_1d"])

    sp = _index_move("^GSPC")
    if sp:
        out["sp500"] = fmt_pct(sp["change_1d"])

    try:
        cal = yf.Ticker("TSLA").calendar or {}
        dates = cal.get("Earnings Date") or []
        if dates:
            earn = dates[0]
            if hasattr(earn, "year"):
                earn_date = datetime(earn.year, earn.month, earn.day, tzinfo=SAST)
            else:
                earn_date = datetime.fromisoformat(str(earn)[:10]).replace(tzinfo=SAST)
            days = (earn_date.date() - now_sast().date()).days
            if 0 <= days <= 3:
                when = "today" if days == 0 else ("tomorrow" if days == 1 else f"in {days} days")
                out["keyEvent"] = f"TSLA earnings {when}"
    except Exception:
        pass

    if out:
        cache_put("key_numbers", out)
    return out


def fetch_spacex_launches(limit: int = 5, use_cache: bool = True) -> List[Dict[str, Any]]:
    cached = cache_get("launches", use_cache)
    if cached:
        return cached[:limit]

    launches: List[Dict[str, Any]] = []
    try:
        resp = requests.get(
            LL2_UPCOMING,
            params={"lsp__id": SPACEX_LSP_ID, "limit": 15, "mode": "list"},
            timeout=20,
            headers={"User-Agent": "robs-coffee/1.0"},
        )
        resp.raise_for_status()
        rows = resp.json().get("results") or []
        cutoff = now_utc() - timedelta(hours=2)

        def field_name(val) -> str:
            if isinstance(val, dict):
                return val.get("name") or ""
            return val or ""

        raw = []
        for item in rows:
            try:
                net = item.get("net") or ""
                net_dt = datetime.fromisoformat(net.replace("Z", "+00:00"))
                if net_dt < cutoff:
                    continue
                status_obj = item.get("status") or {}
                status = (status_obj.get("abbrev") if isinstance(status_obj, dict) else str(status_obj)).upper()
                if status in {"SUCCESS", "FAILURE", "PARTIAL FAILURE"}:
                    continue
                name = item.get("name") or "Unknown mission"
                pad = field_name(item.get("pad"))
                loc = field_name(item.get("location")) or field_name((item.get("pad") or {}).get("location") if isinstance(item.get("pad"), dict) else "")
                details = " - ".join(p for p in [pad, loc] if p)
                fuzzy = status in {"TBD", "TBC"} or (net_dt.hour == 0 and net_dt.minute == 0)
                info_urls = item.get("infoURLs") or []
                link = ""
                if info_urls and isinstance(info_urls[0], dict):
                    link = info_urls[0].get("url") or ""
                elif info_urls and isinstance(info_urls[0], str):
                    link = info_urls[0]
                slug = item.get("slug") or ""
                if not link:
                    link = f"https://spacelaunchnow.me/launch/{slug}" if slug else "https://nextspaceflight.com/"
                lower = name.lower()
                highlight = any(k in lower for k in ("starship", "crew", "hls", "dragon", "roman"))
                is_starlink = "starlink" in lower
                raw.append({
                    "name": name,
                    "date": format_sast(net, fuzzy=fuzzy),
                    "dateISO": net,
                    "details": details,
                    "highlight": highlight,
                    "link": link,
                    "starlink": is_starlink,
                    "net_dt": net_dt,
                })
            except Exception:
                continue

        def clean_row(row: Dict[str, Any]) -> Dict[str, Any]:
            return {k: v for k, v in row.items() if k not in {"starlink", "net_dt"}}

        starship = [r for r in raw if "starship" in r["name"].lower()]
        highlights = [r for r in raw if r["highlight"] and "starship" not in r["name"].lower()]
        starlinks = [r for r in raw if r["starlink"]]
        other = [r for r in raw if not r["starlink"] and not r["highlight"]]

        selected: List[Dict[str, Any]] = []
        seen = set()

        def take(rows: List[Dict[str, Any]], n: Optional[int] = None) -> None:
            added = 0
            for row in rows:
                if len(selected) >= limit:
                    break
                if n is not None and added >= n:
                    break
                if row["name"] in seen:
                    continue
                seen.add(row["name"])
                selected.append(row)
                added += 1

        take(starship, 1)
        take(highlights)
        take(starlinks, 2)
        take(other)
        selected.sort(key=lambda r: r["net_dt"])
        launches = [clean_row(r) for r in selected]
    except Exception as e:
        console.print(f"[yellow]Launch fetch warning: {e}[/yellow]")

    if launches:
        cache_put("launches", launches)
    return launches


def fetch_news(limit: int = 6, use_cache: bool = True) -> List[Dict[str, Any]]:
    cached = cache_get("news", use_cache)
    if cached:
        return cached[:limit]

    news: List[Dict[str, Any]] = []
    for rss_url, source in NEWS_RSS_URLS:
        try:
            resp = requests.get(rss_url, timeout=12, headers={"User-Agent": "robs-coffee/1.0"})
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:8]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = item.findtext("pubDate") or ""
                if not title:
                    continue
                if not any(kw in title.lower() for kw in NEWS_KEYWORDS):
                    continue
                news.append({
                    "title": title[:140],
                    "link": link,
                    "date": pub_date[:22] if pub_date else "",
                    "hoursAgo": hours_ago(pub_date),
                    "source": source,
                })
        except Exception as e:
            console.print(f"[yellow]News source warning ({source}): {e}[/yellow]")

    seen = set()
    deduped = []
    for item in news:
        key = item["title"].lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= limit:
            break

    if deduped:
        cache_put("news", deduped)
    return deduped[:limit]


def fetch_world_events(limit: int = 5, use_cache: bool = True) -> List[Dict[str, Any]]:
    cached = cache_get("world_events", use_cache)
    if cached:
        return cached[:limit]

    events: List[Dict[str, Any]] = []
    try:
        resp = requests.get(WORLD_RSS, timeout=12, headers={"User-Agent": "robs-coffee/1.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").split("?")[0]
            pub_date = item.findtext("pubDate") or ""
            ago = hours_ago(pub_date)
            if ago is None or ago > 36:
                continue
            if not title:
                continue
            events.append({
                "text": title,
                "hoursAgo": ago,
                "link": link,
            })
            if len(events) >= limit:
                break
    except Exception as e:
        console.print(f"[yellow]World events warning: {e}[/yellow]")

    if events:
        cache_put("world_events", events)
    return events


def fetch_calendar(limit: int = 8) -> List[Dict[str, Any]]:
    """Optional. Set CALENDAR_ICS_URL to a private Google Calendar ICS address.

    Only titles and times are stored. Descriptions are discarded so a public
    GitHub Pages deploy does not leak meeting notes or medical detail.
    """
    url = os.environ.get("CALENDAR_ICS_URL", "").strip()
    if not url:
        return []

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        text = resp.text
    except Exception as e:
        console.print(f"[yellow]Calendar warning: {e}[/yellow]")
        return []

    events: List[Dict[str, Any]] = []
    blocks = text.split("BEGIN:VEVENT")
    window_end = now_sast() + timedelta(days=5)
    today = now_sast().date()

    def unfold(raw: str) -> str:
        return raw.replace("\r\n ", "").replace("\n ", "")

    def ics_dt(value: str) -> Optional[datetime]:
        value = value.strip()
        try:
            if value.endswith("Z"):
                return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone(SAST)
            if "T" in value:
                return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=SAST)
            return datetime.strptime(value[:8], "%Y%m%d").replace(tzinfo=SAST)
        except Exception:
            return None

    for block in blocks[1:]:
        block = unfold(block)
        summary = ""
        start = None
        all_day = False
        for line in block.splitlines():
            if line.startswith("SUMMARY"):
                summary = line.split(":", 1)[-1].strip()
            elif line.startswith("DTSTART"):
                raw = line.split(":", 1)[-1]
                all_day = "VALUE=DATE" in line or ("T" not in raw)
                start = ics_dt(raw)
        if not summary or start is None:
            continue
        start_date = start.date()
        if start_date < today or start > window_end:
            continue
        if start_date == today:
            when = "today" if all_day or (start.hour == 0 and start.minute == 0) else start.strftime("%Hh%M")
        elif start_date == today + timedelta(days=1):
            when = "tomorrow" if all_day else f"tomorrow {start.strftime('%Hh%M')}"
        else:
            when = start.strftime("%a %d %b") if all_day else start.strftime("%a %d %b %Hh%M")
        events.append({
            "title": summary[:80],
            "when": when,
            "startISO": start.isoformat(),
        })

    events.sort(key=lambda e: e["startISO"])
    return events[:limit]


# ------------------------------------------------------------------
# Rendering (Rich)
# ------------------------------------------------------------------
def render_dashboard(stocks, launches, news, weather=None, key_numbers=None, world_events=None, calendar_events=None):
    console.rule("[bold amber]ROB'S COFFEE[/bold amber]", style="amber")
    console.print(f"[dim]{now_sast().strftime('%A, %B %d, %Y  %H:%M')} SAST[/dim]\n")

    if calendar_events:
        console.print(Panel.fit("[bold]Coming up[/bold]", border_style="blue"))
        for ev in calendar_events:
            console.print(f"  [bold]{ev['when']}[/bold]  {ev['title']}")
        console.print()

    if world_events:
        console.print(Panel.fit("[bold red]World events[/bold red]  last 24h", border_style="red"))
        for ev in world_events:
            console.print(f"  {ev['hoursAgo']}h • {ev['text']}")
        console.print()

    if key_numbers:
        bits = []
        if key_numbers.get("usdZar"):
            bits.append(f"R{key_numbers['usdZar']}/$ {key_numbers.get('usdZarWeek', '')} {key_numbers.get('usdZarLabel', '')}")
        if key_numbers.get("btc"):
            btc = float(key_numbers["btc"])
            bits.append(f"BTC ${btc/1000:.1f}k {key_numbers.get('btcWeek', '')}")
        if key_numbers.get("jse"):
            bits.append(f"JSE {key_numbers['jse']}")
        if key_numbers.get("sp500"):
            bits.append(f"S&P {key_numbers['sp500']}")
        if key_numbers.get("keyEvent"):
            bits.append(key_numbers["keyEvent"])
        if bits:
            console.print("[bold]Key numbers[/bold]  " + "   ".join(bits) + "\n")

    if stocks:
        table = Table(title="Market Snapshot (TSLA, NVDA, MU)", box=box.SIMPLE_HEAVY)
        table.add_column("Ticker", style="bold")
        table.add_column("Price", justify="right")
        table.add_column("1D", justify="right")
        table.add_column("3D", justify="right")
        table.add_column("1M", justify="right")
        table.add_column("12M", justify="right")
        table.add_column("3Y", justify="right")
        for sym, data in stocks.items():
            def fmt(key, d=data):
                val = d.get(key, 0)
                color = "green" if val >= 0 else "red"
                return f"[{color}]{val:+.1f}%[/]"
            table.add_row(sym, f"${data['price']}", fmt("change_1d"), fmt("change_3d"), fmt("change_1m"), fmt("change_12m"), fmt("change_3y"))
        console.print(table)
        console.print()

    if weather:
        console.print(Panel.fit("[bold cyan]Cape Town[/bold cyan]", border_style="cyan"))
        for label, w in weather.items():
            console.print(
                f"  [bold]{label}[/bold]  {w['temp']}°C  {w['condition']}  "
                f"Wind {w['wind_speed']} km/h  Cloud {w['cloud']}%  Rain {w['rain']}mm"
            )
        console.print()

    if launches:
        console.print(Panel.fit("[bold]SpaceX[/bold]", border_style="magenta"))
        for launch in launches:
            prefix = "★ " if launch.get("highlight") else "  "
            console.print(f"{prefix}[bold]{launch['name']}[/bold]  •  {launch['date']}")
            if launch.get("details"):
                console.print(f"   [dim]{launch['details']}[/dim]")
        console.print()

    if news:
        console.print(Panel.fit("[bold green]Tesla • SpaceX • xAI[/bold green]", border_style="green"))
        for item in news:
            ago = item.get("hoursAgo")
            prefix = f"{ago}h • " if ago is not None else ""
            console.print(f"  {prefix}{item['title']}")
        console.print()

    console.rule(style="dim")
    console.print("[dim]Data cached ~45min  •  open robs-coffee.html for the phone view[/dim]")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Rob's Coffee - daily briefing")
    parser.add_argument("--stocks", action="store_true")
    parser.add_argument("--launches", action="store_true")
    parser.add_argument("--news", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="Ignore cache")
    args = parser.parse_args()

    if args.refresh and CACHE_FILE.exists():
        CACHE_FILE.unlink()

    use_cache = not args.refresh
    stocks = fetch_stocks(use_cache=use_cache)
    launches = fetch_spacex_launches(use_cache=use_cache)
    news_items = fetch_news(use_cache=use_cache)

    if args.stocks:
        for sym, d in stocks.items():
            print(f"{sym}: ${d['price']}  | 1D {d.get('change_1d', 0):+.1f}%  3D {d.get('change_3d', 0):+.1f}%  1M {d.get('change_1m', 0):+.1f}%  12M {d.get('change_12m', 0):+.1f}%  3Y {d.get('change_3y', 0):+.1f}%")
        return
    if args.launches:
        for launch in launches:
            print(f"{launch['name']} | {launch['date']}")
        return
    if args.news:
        for n in news_items:
            print(f"- {n['title']}")
        return

    weather = fetch_cape_town_forecast(use_cache=use_cache)
    key_numbers = fetch_key_numbers(use_cache=use_cache)
    world_events = fetch_world_events(use_cache=use_cache)
    calendar_events = fetch_calendar()
    render_dashboard(stocks, launches, news_items, weather, key_numbers, world_events, calendar_events)


if __name__ == "__main__":
    main()
