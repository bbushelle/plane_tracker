# Plane Tracker

## Overview
Based on [c0wsaysmoo/plane-tracker-rgb-pi](https://github.com/c0wsaysmoo/plane-tracker-rgb-pi) with significant modifications. Tracks overhead flights via FlightRadar24, displays live sports scores, and shows weather/forecast data on a 64×32 RGB LED matrix.

## Current Setup
- **Hardware:** Raspberry Pi 3 Model A+, hostname `autism-pi`, user `tyler`
- **Repo path on Pi:** `/home/tyler/plane-tracker/`
- **Entry point:** `/home/tyler/plane-tracker/its-a-plane-python/its-a-plane.py`
- **Config file:** `/home/tyler/plane-tracker/its-a-plane-python/config.py`
- **SSH credentials:** stored in Claude memory (not in this repo)
- **Web interface:** Flask on port 8080, started as a subprocess of `its-a-plane.py`

## What's Been Built

### Git Auto-Update (Nightly Pull)
- `scripts/update.sh` — fetches, compares SHAs, logs incoming commits, pulls, restarts app
- `scripts/install-cron.sh` — installs a 3 AM daily cron job; schedule is easily adjusted
- `scripts/setup-pi.sh` — idempotent one-time migration script for the Pi

### Location Detection
- `utilities/location.py` reads `SSID_LOCATIONS` from `.env` via python-dotenv
- Bounding box calculated automatically from lat/lon; default radius 3 miles
- `JOURNEY_CODE_SELECTED` (home airport) also set per SSID
- Three known SSIDs: milloosh → ORD, Komquat → GRB, boosh-5 → ATW
- Falls back to hardcoded defaults if SSID not found
- Per-SSID `min_altitude` and `radius_miles` overrides configurable via web UI (`/settings` → Location Settings), stored in `user_config.json["ssid_overrides"]`; takes effect after Restart App

### Sports Scores Display
- ESPN public scoreboard API, no key required
- `utilities/sports.py` — `SportsPoller` background thread, score-change detection
- `scenes/sportsscore.py` — 64×32 layout: rows 0-7 LIVE + period/clock header, rows 9-20 logos + score, rows 24-28 abbreviations, rows 29-31 league
- Team logos downloaded from ESPN CDN at startup, cached in `sports_logos/` (gitignored); cached in memory after first load per session
- Logos rendered via `matrix.SetImage` inside `_draw_game` (called from `sports_score`, before `sync`) — writes logos into the back buffer which sync then swaps to display, matching the pattern used by flight logos and weather icons
- When a live game is detected, logos for both teams (including unconfigured opponents) are downloaded in a background thread
- Configurable delay before showing a score change (default 10s, for TV broadcast lag)
- Planes take priority — sports only show after current scroll cycle completes
- Display interval: 30s of sports, then back to planes
- Sports pause: web UI button suppresses scores for 1 hour via `sports_pause.json`

### Weather Data Cache
- `utilities/temperature.py` caches tomorrow.io API responses to `.weather_cache.json`
- Cache is fresh for 4 hours; falls back to stale data on API failure

### Tailscale Remote Access
- Setup guide in `docs/tailscale-setup.md`

### Web Interface (port 8080)
- `web/app.py` — Flask, serves settings and flight log data
- **Dashboard** (`/`) — closest/farthest flight logs, nav cards, live clock
- **Settings** (`/settings`):
  - Sports Teams — add/remove teams, pause scores for 1 hour
  - Display Timing — score delay, display interval
  - Display Brightness — day/night brightness, night mode schedule
  - Display Theme — 11 colour pickers (clock, flight display, forecast, sports scores)
  - Test Display — trigger mock scenes without live data (see below)
  - Location Settings — per-SSID min altitude and scan radius overrides
  - System Controls — Restart App (~15s), Restart Pi (~60s), Shutdown Pi
  - Log Viewer — live tail of app.log and update.log
- **Maps** — closest and farthest flight maps (HTML/PNG)

### Test Display Suite
- Web UI buttons trigger specific test scenes without needing live flights or an active game
- Modes: `clock`, `forecast`, `flight` (mock UAL1234 ORD→LAX), `sports` (mock EDM 3–2 STL), `cycle` (rotates clock→flight→sports every 15s)
- Active mode shown in the UI; Reset button returns to normal operation
- Implemented via `test_scene.json` file-based IPC — Flask writes the mode, display process reads it every 5s in `check_test_mode` KeyFrame
- While a test mode is active, all real flight and sports polling is blocked so mock data is not overwritten
- `test_scene.json` is gitignored

### Display Theme
- `setup/theme.py` — reads `user_config.json` at startup, exports named colour constants
- Scenes import from `theme` instead of hardcoding colours from `setup/colours`
- Configurable: clock day/night, flight number letters/digits, plane type, distance, forecast day/min/max, sports home/away scores
- Changes take effect after restarting the Pi

### Flight Detail Logging
- `utilities/overhead.py` — detailed logging of every API call and extracted field
- Origin/destination prefer detail response (`d["airport"]["origin"]["code"]["iata"]`) over basic listing
- Retry logic with full traceback on failure

## File Structure
```
plane-tracker/
├── its-a-plane-python/
│   ├── its-a-plane.py          # Entry point
│   ├── config.py               # Configuration (reads user_config.json overrides)
│   ├── display/                # LED matrix display driver + sports/brightness logic
│   ├── scenes/                 # Display screens (clock, weather, flight, sports, etc.)
│   ├── setup/                  # colours.py, fonts.py, theme.py, frames.py, screen.py
│   ├── utilities/              # overhead, sports, temperature, location, animation
│   ├── web/                    # Flask app, templates, static files, user_config.json
│   ├── fonts/                  # BDF bitmap fonts
│   ├── logos/                  # Airline logo PNGs (ICAO filenames, committed)
│   ├── icons/                  # Weather icon PNGs (weatherCode filenames, committed)
│   └── sports_logos/           # Team logo PNGs (downloaded at runtime, gitignored)
├── scripts/
│   ├── setup-pi.sh             # One-time Pi migration script
│   ├── update.sh               # Nightly auto-update script
│   └── install-cron.sh         # Installs the nightly update cron job
├── docs/                       # Project documentation
├── .env                        # SSID mappings (gitignored, copy from .env.example)
├── .env.example                # Template for .env
├── CLAUDE.md                   # This file
└── README.md
```

## Runtime Files (gitignored)
| File | Purpose |
|------|---------|
| `.env` | SSID → lat/lon/airport mappings |
| `web/user_config.json` | Web UI config overrides (teams, brightness, colours) |
| `.weather_cache.json` | 4-hour weather API cache |
| `sports_logos/*.png` | Team logos downloaded from ESPN at startup |
| `sports_pause.json` | Transient sports-pause expiry timestamp |
| `test_scene.json` | Transient test scene mode written by web UI |
| `close.txt` | Top-N closest flights log |
| `farthest.txt` | Top-N farthest airports log |

## Documentation
All feature docs live in `/docs`. See [docs/pi-setup.md](docs/pi-setup.md) for initial setup.
