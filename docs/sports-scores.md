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

Logos are downloaded as RGBA images, composited onto a black background, and resized to 12×12 pixels. They are rendered on the LED matrix using `matrix.SetImage()` with the away logo at the left edge (x=0) and the home logo at the right edge (x=52).

If logos are unavailable (first boot, network failure), the scene falls back to a text-only layout.

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

The 64×32 display is divided into three horizontal bands:

```
Row  0-9  : "LIVE" (red, left) + league tag (grey, right)
Row 10-20 : Score — away logo (left), score numbers (centre), home logo (right)
Row 21-31 : Period and clock — e.g. "P2  14:23"
```

With logos present:
- Away logo at x=0, home logo at x=52 (12×12 px each)
- Score numbers centred in the 40px middle column, colour-coded

Without logos (fallback):
- Text-only layout: `AWY X - X HOM`, all centred

When multiple teams have simultaneous live games, the scene cycles through them every 15 seconds.
