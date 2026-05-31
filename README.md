# Rob's Coffee

Your personal daily briefing — stocks, Cape Town weather, Starship launches, Elon updates, and sharp commentary.

## Quick Start (Web Dashboard)

Open `robs-coffee.html` locally, or deploy it.

### One-command Deploy (Recommended)

After the one-time setup below, just run:

```bash
npm run deploy
```

This will:
- Copy the latest `robs-coffee.html` → `index.html`
- Deploy to Netlify (production)

### One-time Setup (Netlify CLI)

```bash
# 1. Install Netlify CLI globally
npm install -g netlify-cli

# 2. Login to Netlify
netlify login

# 3. Link this project to your existing Netlify site
netlify link
# → Choose "Existing site" → select "vocal-babka-033f26" (or your site name)

# 4. (Optional but recommended) Install local deps
npm install
```

After this, you can always just run `npm run deploy` from the project folder.

## Local Development

```bash
# View locally
open robs-coffee.html
```

## Updating the Dashboard

1. Edit `robs-coffee.html` (or run `python3 update_coffee.py` if you have data scripts)
2. Run `npm run deploy`
3. Done.

## Notes

- The site is fully static and free on Netlify.
- All sensitive sections (like holdings) are password protected in the browser.

## TODO

- [ ] Pull upcoming events from Google Calendar (user requested)

## Visual Dashboard

Simply double-click `elon-dashboard.html`.

It includes:
- Live stock prices + performance for TSLA + NVDA (xAI synergy)
- Interactive price trend chart
- Upcoming SpaceX launches (fetched live from public API)
- Curated positive highlights from the Tesla / SpaceX / xAI world

## Keeping Data Fresh

```bash
python update_elon.py
```

This command:
- Refreshes the CLI cache
- Updates the embedded data inside the single-file HTML

Recommended: Run daily via cron, launchd, or a simple shell alias.

## Making It Available Online at a Memorable URL

Because it's a **single self-contained HTML file**, hosting is trivial:

### Option 1: GitHub Pages (Recommended)
1. Create a new GitHub repository called `elon-dashboard`
2. Upload `elon-dashboard.html` and rename it to `index.html`
3. Go to **Settings → Pages**
4. Choose "Deploy from a branch" → main
5. Your dashboard is now live at:
   `https://yourusername.github.io/elon-dashboard`

### Option 2: Instant Hosting (Netlify Drop)
1. Go to https://app.netlify.com/drop
2. Drag and drop the `elon-dashboard.html` file
3. You instantly get a random memorable URL (you can customize it)

### Option 3: Simple Static Hosting
Any static host works (Vercel, Cloudflare Pages, etc.).

## Data Sources (Free & Public)

- **Stocks**: Yahoo Finance via `yfinance`
- **Launches**: Official SpaceX public API
- **News**: Teslarati RSS feed (consistently positive coverage of the ecosystem)

## Philosophy

- Keep it **simple** and **fast**
- Focus on **positive, high-signal** information
- Designed for daily ritual use
- No accounts, no API keys, no bullshit

---

Built following the spirit of shipping useful tools quickly.
