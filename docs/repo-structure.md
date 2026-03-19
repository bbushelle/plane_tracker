# Repo Structure

## Overview

The original c0wsaysmoo project required moving files out of the cloned repo into the home directory as part of setup. This repo eliminates that requirement — everything lives here and the Pi clones to a fixed path.

## Directory Layout

```
plane-tracker/
├── its-a-plane-python/         # Main application (original project, modified)
│   ├── its-a-plane.py          # Entry point
│   ├── config.py               # Configuration (location, API keys, display settings)
│   ├── display/                # LED matrix display driver
│   ├── scenes/                 # Individual display screens (clock, weather, flight, sports, etc.)
│   ├── setup/                  # Initialization helpers (colours, fonts, frames, theme)
│   │   └── theme.py            # Runtime colour constants loaded from user_config.json
│   ├── utilities/              # Core logic (plane tracking, weather, sports, animation)
│   ├── web/                    # Flask web UI (port 8080)
│   │   ├── app.py              # Flask routes and settings API
│   │   ├── templates/          # Jinja2 HTML templates
│   │   ├── static/             # Static assets (maps, CSS)
│   │   └── user_config.json    # Web-editable settings overrides (gitignored)
│   ├── fonts/                  # BDF bitmap fonts for LED matrix
│   ├── logos/                  # Airline logo PNGs (ICAO code filenames)
│   ├── icons/                  # Weather icon PNGs (weatherCode filenames)
│   └── sports_logos/           # Team logo PNGs downloaded from ESPN CDN (gitignored)
├── scripts/                    # Pi maintenance scripts
│   ├── update.sh               # Nightly git pull + restart
│   └── install-cron.sh         # Installs the nightly update cron entry
├── docs/                       # Project documentation
├── .env                        # SSID→location mappings (gitignored, copied to Pi manually)
├── .gitignore
├── CLAUDE.md                   # Project goals and specs for AI assistant
└── README.md
```

## Runtime files (gitignored)

| File | Description |
|------|-------------|
| `its-a-plane-python/web/user_config.json` | Web-editable overrides for teams, brightness, theme colours |
| `its-a-plane-python/close.txt` | JSON log of closest flights observed |
| `its-a-plane-python/farthest.txt` | JSON log of farthest airports observed |
| `its-a-plane-python/.weather_cache.json` | Cached weather API response (4-hour TTL) |
| `its-a-plane-python/sports_pause.json` | Transient sports pause expiry timestamp |
| `its-a-plane-python/sports_logos/` | Team logos downloaded at startup from ESPN CDN |
| `.env` | SSID names and lat/lon mappings |

## What Changed from the Original

The original setup instructed users to run:
```bash
mv ~/plane-tracker-rgb-pi/* ~/
mkdir -p ~/logos
mv ~/logo/* ~/logos/
mv ~/logo2/* ~/logos/
```

This scattered files outside the repo, making git-managed updates impossible.

**Changes made:**
1. `logos/` and `icons/` are now inside `its-a-plane-python/` (part of the repo)
2. `scenes/flightlogo.py` — updated `Image.open()` to use an absolute path resolved from `__file__` instead of a cwd-relative path
3. `scenes/daysforecast.py` — same fix for icon loading

All other path references in the original code already used `os.path.dirname(__file__)` and required no changes.

## Pi Deployment Path

The repo should be cloned to:
```
/home/tyler/plane-tracker/
```

The entry point cron job references:
```
/home/tyler/plane-tracker/its-a-plane-python/its-a-plane.py
```
