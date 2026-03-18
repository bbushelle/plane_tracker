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
│   ├── scenes/                 # Individual display screens (clock, weather, flight, etc.)
│   ├── setup/                  # Initialization helpers (colours, fonts, frames)
│   ├── utilities/              # Core logic (plane tracking, weather, animation)
│   ├── web/                    # Flask web UI for viewing flight logs
│   ├── fonts/                  # BDF bitmap fonts for LED matrix
│   ├── logos/                  # Airline logo PNGs (ICAO code filenames)
│   └── icons/                  # Weather icon PNGs (weatherCode filenames)
├── docs/                       # Project documentation
├── .gitignore
├── CLAUDE.md                   # Project goals and specs
└── README.md
```

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

The entry point cron job should reference:
```
/home/tyler/plane-tracker/its-a-plane-python/its-a-plane.py
```
