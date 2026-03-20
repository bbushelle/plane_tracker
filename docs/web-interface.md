# Web Interface

The Flask web server runs on port 8080 and is accessible at `http://autism-pi:8080` from any device on the same network.

---

## Pages

### Dashboard (`/`)

The main page shows:
- **Live clock** — updates every 10 seconds
- **Closest Flights on Record** — top-N closest flights logged, with callsign, airline, aircraft type, route, distance/direction, and timestamp
- **Farthest Airports on Record** — ranked table of farthest origin/destination airports observed, with distance and airline
- **Maps & Logs** — navigation cards to map views and raw JSON endpoints
- **Admin** — link to Settings

### Closest Flight Map (`/closest`)

Visual map showing the closest flights on record plotted against your home location.

### Farthest Flights Map (`/farthest`)

Visual map showing the farthest origin/destination airports on record.

### Settings (`/settings`)

Configures all runtime settings. Changes are saved to `user_config.json` immediately. Most changes take effect after restarting the app or rebooting the Pi.

---

## Settings Page Sections

### Sports Teams

Add or remove teams tracked for live scores. Each team requires:
- Name (display only)
- Abbreviation (matched against ESPN API, e.g. `EDM`, `GB`)
- Sport (`hockey`, `football`, `basketball`, `baseball`)
- League (`nhl`, `nfl`, `nba`, `mlb`)

### Sports Score Delay & Display Interval

| Setting | Default | Description |
|---------|---------|-------------|
| Score delay | 10s | Seconds to wait after a score change before showing it |
| Display interval | 30s | Seconds to hold the sports scene before returning to planes |

### Pause Sports Scores

Suppresses sports score display for 1 hour. Useful when watching a game live. A live countdown shows remaining pause time. Use the **Resume** button to cancel early.

### Display Brightness

| Setting | Description |
|---------|-------------|
| Day brightness | LED brightness (0–100) during normal hours |
| Night brightness | LED brightness (0–100) during night hours |
| Night mode | Enable/disable reduced brightness at night |
| Night start / end | Time range for night mode (HH:MM) |

### Display Theme

Colour pickers for all scene elements. Changes take effect after reboot.

| Group | Controls |
|-------|---------|
| Clock | Day colour, night colour |
| Flight Display | Flight number alpha colour, numeric colour |
| Forecast | Day name colour, low temp colour, high temp colour |
| Sports Scores | Away score colour, home score colour |

### Location Settings

Per-SSID overrides for flight filtering. Each known SSID (from `.env`) gets its own row.

| Setting | Default | Description |
|---------|---------|-------------|
| Min Altitude | 2000 ft | Ignore flights below this altitude |
| Radius | 3.0 mi | Bounding box radius around the home location |

Changes take effect after **Restart App** (not a full reboot).

### Test Display

Triggers a specific test scene on the LED matrix without needing a live flight or active game. Useful for verifying the display is working after a config change or reboot.

| Button | Mode | What shows |
|--------|------|------------|
| Clock / Date | `clock` | Clock and date scene only (no flights, no sports) |
| Forecast | `forecast` | 3-day weather forecast scene |
| Mock Flight | `flight` | Simulated UAL1234 ORD→LAX flight scroll |
| Mock Sports | `sports` | Simulated EDM 3–2 STL live hockey score |
| Cycle All | `cycle` | Rotates through clock, flight, and sports every 15 seconds |
| Reset | _(clear)_ | Returns to normal operation |

The active test mode is shown in the UI. Test mode blocks all real flight and sports data from updating the display until Reset is pressed.

### System Controls

- **Restart App** — kills and relaunches `its-a-plane.py` without rebooting the Pi (~15s downtime). Use after changing location or altitude settings.
- **Restart Pi** — full hardware reboot (~60s downtime).
- **Shutdown Pi** — cleanly powers down the Pi.

### Logs

Live tail of `app.log` and `update.log`, fetched from the server. Useful for debugging without SSH.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/closest/json` | Full closest flights log as JSON |
| GET | `/farthest/json` | Full farthest airports log as JSON |
| GET | `/settings/config` | Current merged config (defaults + user overrides) |
| POST | `/settings/teams/add` | Add a sports team |
| POST | `/settings/teams/remove` | Remove a sports team |
| POST | `/settings/delays` | Update score delay and display interval |
| POST | `/settings/brightness` | Update brightness settings |
| POST | `/settings/theme` | Update display theme colours |
| GET | `/settings/sports/pause` | Get current pause status |
| POST | `/settings/sports/pause` | Pause sports scores (body: `{"hours": 1}`) |
| POST | `/settings/sports/resume` | Resume sports scores immediately |
| GET | `/test/scene` | Get current test mode (`{"mode": "flight"}` or `{"mode": null}`) |
| POST | `/test/scene` | Set test mode (body: `{"mode": "clock"\|"flight"\|"sports"\|"forecast"\|"cycle"\|null}`) |
| GET | `/settings/location` | Per-SSID min_altitude and radius_miles overrides |
| POST | `/settings/location` | Save per-SSID override (body: `{"ssid": "...", "min_altitude": 2000, "radius_miles": 3.0}`) |
| GET | `/logs/app` | Last 200 lines of app.log |
| GET | `/logs/update` | Last 200 lines of update.log |
| POST | `/system/app/restart` | Kill and relaunch `its-a-plane.py` without rebooting |
| POST | `/system/restart` | Reboot the Pi |
| POST | `/system/shutdown` | Shut down the Pi |

---

## Configuration persistence

All web-configurable settings are saved to `its-a-plane-python/web/user_config.json`. This file is gitignored. At startup, `config.py` and `setup/theme.py` read this file to override their hardcoded defaults, so settings survive reboots but are not tracked in git.

To reset all settings to defaults, delete the file and reboot:

```bash
rm /home/tyler/plane-tracker/its-a-plane-python/web/user_config.json
sudo reboot
```
