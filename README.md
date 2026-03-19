# plane_tracker

A 64×32 RGB LED matrix plane tracker running on a Raspberry Pi 3 Model A+. Based on [c0wsaysmoo/plane-tracker-rgb-pi](https://github.com/c0wsaysmoo/plane-tracker-rgb-pi) with significant additions.

## What it does

- Tracks aircraft overhead using the OpenSky Network API and displays flight info on the LED matrix
- Shows a 3-day weather forecast with icons
- Displays live sports scores during active games (NHL, NFL, and any ESPN-supported sport)
- Includes a dark-themed web dashboard accessible on the local network for viewing flight logs, maps, and adjusting settings

## Hardware

- Raspberry Pi 3 Model A+ (`autism-pi`)
- 64×32 RGB LED matrix panel
- rpi-rgb-led-matrix library

## Web Interface

The Flask web server runs on port 8080 and is accessible at `http://autism-pi:8080`.

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/` | Closest and farthest flights on record, navigation |
| Closest flight map | `/closest` | Visual map of the top closest flights |
| Farthest flights map | `/farthest` | Visual map of the top farthest flights |
| Raw closest data | `/closest/json` | JSON log of closest flights |
| Raw farthest data | `/farthest/json` | JSON log of farthest airports |
| Settings | `/settings` | Configure teams, brightness, theme colours, sports pause |

## Configuration

Settings are split between `config.py` (code-level defaults) and `user_config.json` (web-editable overrides):

- **Sports teams** — add/remove via the Settings page or `config.py`
- **Brightness** — day/night brightness and schedule via Settings page
- **Display theme** — all scene colours (clock, flight details, forecast, sports scores) configurable via colour pickers in Settings
- **Location** — determined automatically by WiFi SSID; mappings stored in `.env`

See the [`docs/`](docs/) directory for full documentation.

## Key features added to the original project

- **Git auto-update** — nightly cron pull with restart if changes detected
- **SSID-based location detection** — Pi moves between 3 locations, config updates automatically
- **Live sports scores** — ESPN API, team logos from ESPN CDN, configurable teams
- **Sports score pause** — pause display for 1 hour via web UI (useful when watching a game live)
- **Weather data cache** — 4-hour cache survives restarts and avoids rate limiting
- **Display theme** — all colours configurable via web UI, no code changes needed
- **Tailscale** — remote SSH access setup
- **Web dashboard** — dark terminal-themed flight log viewer and settings panel

## Documentation

- [Pi Setup](docs/pi-setup.md)
- [Repo Structure](docs/repo-structure.md)
- [Auto-Update](docs/auto-update.md)
- [Location Detection](docs/location-detection.md)
- [Sports Scores](docs/sports-scores.md)
- [Weather Cache](docs/weather-cache.md)
- [Web Interface](docs/web-interface.md)
- [Tailscale Setup](docs/tailscale-setup.md)
