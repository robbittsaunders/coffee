# Rob's Coffee

Personal daily briefing for a phone: Cape Town weather, TSLA/NVDA/MU, USD/ZAR, BTC, JSE + S&P, SpaceX, world headlines, Tesla/SpaceX/xAI news, and holdings.

Live: https://robbittsaunders.github.io/coffee/

Built as a single static HTML file. A GitHub Action refreshes the baked-in data three times a day (06:00, 16:00, 22:00 SAST) so you do not have to remember to run a script.

Weather, USD/ZAR, BTC, and holdings also fetch live in the browser when you open the page.

## Local refresh

```bash
python3 update_coffee.py
```

Then either open `robs-coffee.html` or deploy:

```bash
npm run deploy
```

CLI snapshot:

```bash
python3 coffee.py --refresh
```

## Optional calendar

The public GitHub Pages site should not carry meeting notes or medical detail.

If you want a **Coming up** strip (titles and times only, next 5 days):

1. In Google Calendar: Settings → your calendar → **Secret address in iCal format**
2. Add that URL as a GitHub Actions secret named `CALENDAR_ICS_URL`
3. For local runs: `export CALENDAR_ICS_URL='...'` before `python3 update_coffee.py`

Descriptions are discarded on purpose.

## Data sources

- Stocks, USD/ZAR, BTC, JSE, S&P: Yahoo Finance via `yfinance`
- Live USD/ZAR overlay: exchangerate-api.com
- Live BTC overlay: CoinGecko
- Weather: Open-Meteo
- Launches: The Space Devs Launch Library 2
- World events: BBC World RSS
- Company news: Teslarati, InsideEVs, NASASpaceflight, CleanTechnica, SpaceNews
- Holdings: published Google Sheet (client-side)

No API keys required for the default briefing.
