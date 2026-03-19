# Sports Scores Display

The sports scores feature polls the free ESPN public API and displays live game scores on the 64x32 LED matrix whenever a configured team is playing.

---

## How live detection works

1. `SportsPoller` (running in a background thread) calls the ESPN scoreboard endpoint for each unique sport/league combination found in `SPORTS_TEAMS`.
2. Each event in the response is checked for `status.type.state == "in"` (game currently in progress).
3. If a live event involves one of the configured team abbreviations, it is included in the result set.
4. The `Display` class checks for new poller data every 5 seconds (`check_sports_data` KeyFrame). When live games are present, `self._sports_data` is populated and `SportsScoreScene` starts rendering.
5. If a score change is detected (either a new live game or a changed score compared to the previous poll), `reset_scene()` is called immediately so the score appears on the matrix as soon as possible.

---

## Display interval

`SPORTS_DISPLAY_INTERVAL` (default `30` seconds) controls how long the sports scene holds the display before yielding back to the plane/clock scenes.

- The timer resets whenever fresh live game data arrives, so a long game stays visible as long as scores keep updating within each 30-second window.
- Once the interval expires, `self._sports_data` is cleared and the next `check_sports_data` cycle will repopulate it only if the poller has new live data.

---

## Poll rates

| Situation | Poll rate |
|-----------|-----------|
| Live game in progress | Every 60 seconds |
| No live game detected | Every 5 minutes |

These are controlled by `POLL_INTERVAL_LIVE` and `POLL_INTERVAL_IDLE` in `utilities/sports.py`, and the `poll_sports_data` KeyFrame in `display/__init__.py`.

---

## ESPN API endpoints used

```
GET https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard
```

Examples:
- NHL: `https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard`
- NFL: `https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard`

No API key is required. ESPN's public scoreboard API is unauthenticated.

Fields extracted per game:

| Field | Source in ESPN response |
|-------|------------------------|
| `home_abbr` / `away_abbr` | `competitions[0].competitors[].team.abbreviation` |
| `home_score` / `away_score` | `competitions[0].competitors[].score` |
| `period` | `status.period` |
| `clock` | `status.displayClock` |
| `status` | `status.type.state` (`"pre"` / `"in"` / `"post"`) |
| `status_detail` | `status.type.shortDetail` |

---

## Team logos

Team logos are downloaded from the ESPN CDN at startup and cached locally in `sports_logos/`. The URL pattern is:

```
https://a.espncdn.com/i/teamlogos/{league}/500/{abbr}.png
```

Logos are downloaded as RGBA images, composited onto a black background, and resized to 12×12 pixels. They are drawn into the canvas back buffer via `matrix.SetImage()` (the same technique used by flight logos and weather icons), then swapped to the display by `sync`. The away logo is at the left edge (x=0, y=9) and the home logo at the right edge (x=52, y=9).

Logos are cached in memory after first load so the Pi's SD card is not read every frame. The cache is cleared on scene reset.

When a live game is detected, logos for both teams (including the opponent, if not pre-configured) are downloaded in a background thread automatically.

If logos are unavailable (first boot before download completes, network failure), the scene falls back to a text-only layout.

---

## Adding or removing teams

Teams can be managed via the **Settings page** (`/settings`) in the web UI without editing any files.

To edit directly, update `SPORTS_TEAMS` in `its-a-plane-python/config.py`:

```python
SPORTS_TEAMS = [
    {"name": "Edmonton Oilers",   "abbreviation": "EDM", "sport": "hockey",   "league": "nhl"},
    {"name": "Green Bay Packers", "abbreviation": "GB",  "sport": "football", "league": "nfl"},
]
```

Each entry requires four keys:

| Key | Description | Example |
|-----|-------------|---------|
| `name` | Human-readable name (used for logging only) | `"Edmonton Oilers"` |
| `abbreviation` | Matched against ESPN's `team.abbreviation` field (case-insensitive) | `"EDM"` |
| `sport` | ESPN sport path segment | `"hockey"`, `"football"`, `"basketball"`, `"baseball"` |
| `league` | ESPN league path segment | `"nhl"`, `"nfl"`, `"nba"`, `"mlb"` |

Teams from the same league are batched into a single API call automatically, so adding multiple NHL teams costs only one HTTP request.

To disable the feature entirely without removing team entries, set:

```python
SPORTS_ENABLED = False
```

---

## Pausing sports scores

The Settings page includes a **Pause Sports** button that suppresses score display for 1 hour. This is useful when watching a game live and wanting to avoid spoilers on the matrix.

- Pause state is stored in `sports_pause.json` as a Unix timestamp expiry
- The display process checks this file every 5 seconds and clears `_sports_data` immediately if a pause is activated mid-display
- The pause expires automatically; no action needed to resume
- A **Resume** button is available to cancel the pause early

---

## Score colours

Home and away score colours are configurable via the **Display Theme** section of the Settings page. Defaults:

| Element | Default colour |
|---------|---------------|
| Away score | Blue (`#28b7f6`) |
| Home score | Orange (`#fea727`) |

---

## Matrix layout

```
Row  0-7  : "LIVE" (red, left) + period/clock e.g. "P2  14:23" (grey, right)
Row  9-20 : Away logo (left 12×12) | score centred | home logo (right 12×12)
Row 24-28 : Team abbreviations centred under each logo
Row 29-31 : League name centred (e.g. "NHL")
```

With logos present:
- Away logo at x=0, home logo at x=52 (12×12 px each, y=9)
- Score numbers centred in the 40px space between the logos, colour-coded per team
- Abbreviations centred under each logo

Without logos (fallback):
- Away abbreviation at left edge, home abbreviation at right edge
- Score centred using a smaller font

When multiple teams have simultaneous live games, the scene cycles through them every 15 seconds.
