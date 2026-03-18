"""
utilities/sports.py

Handles ESPN API polling for live sports scores.
Runs a background thread (mirroring the Overhead pattern) that fetches
scoreboard data and exposes structured game info to the display layer.
"""

import logging
from threading import Thread, Lock
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None  # type: ignore

# ESPN scoreboard endpoint template
ESPN_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
)

# Poll intervals (seconds)
POLL_INTERVAL_LIVE = 60       # while a game is in progress
POLL_INTERVAL_IDLE = 5 * 60  # when no live game is detected

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Low-level API helpers
# ---------------------------------------------------------------------------

def _fetch_scoreboard(sport: str, league: str) -> dict:
    """Fetch raw ESPN scoreboard JSON for a single sport/league."""
    if requests is None:
        logger.error("requests library not available")
        return {}
    url = ESPN_SCOREBOARD_URL.format(sport=sport, league=league)
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("ESPN API request failed (%s %s): %s", sport, league, exc)
        return {}


def _parse_game(event: dict) -> dict:
    """
    Parse a single ESPN scoreboard event into a normalised game dict.

    Returned keys
    -------------
    home_abbr       str   e.g. "EDM"
    away_abbr       str   e.g. "OTT"
    home_score      int
    away_score      int
    period          int   current period / quarter / half (0 if not started)
    clock           str   time remaining in period, e.g. "14:23" or ""
    status          str   "pre" | "in" | "post"
    status_detail   str   human-readable status from ESPN
    game_id         str
    """
    comp = event.get("competitions", [{}])[0]
    status_block = event.get("status", {})
    status_type = status_block.get("type", {})

    raw_state = status_type.get("state", "pre")       # "pre" | "in" | "post"
    status_detail = status_type.get("shortDetail", "")

    period = status_block.get("period", 0)
    clock = status_block.get("displayClock", "")

    home_abbr = away_abbr = ""
    home_score = away_score = 0

    for competitor in comp.get("competitors", []):
        abbr = (
            competitor.get("team", {}).get("abbreviation", "")
            or competitor.get("team", {}).get("shortDisplayName", "")
        )
        try:
            score = int(competitor.get("score", 0))
        except (ValueError, TypeError):
            score = 0

        if competitor.get("homeAway") == "home":
            home_abbr = abbr
            home_score = score
        else:
            away_abbr = abbr
            away_score = score

    return {
        "home_abbr": home_abbr,
        "away_abbr": away_abbr,
        "home_score": home_score,
        "away_score": away_score,
        "period": period,
        "clock": clock,
        "status": raw_state,
        "status_detail": status_detail,
        "game_id": event.get("id", ""),
    }


def get_live_games(teams_config: list) -> list:
    """
    Fetch and return a list of currently live game dicts for all configured teams.

    Parameters
    ----------
    teams_config : list of dicts, each with keys:
        "name"         str  full team name (unused for API, kept for logging)
        "abbreviation" str  e.g. "EDM" — matched against ESPN abbreviations
        "sport"        str  e.g. "hockey"
        "league"       str  e.g. "nhl"

    Returns
    -------
    List of parsed game dicts (see _parse_game).  Only games whose status is
    "in" (i.e. currently live) and that involve a configured team are returned.
    """
    # Deduplicate sport+league pairs so we only hit each endpoint once
    endpoints_seen = set()
    # Map (sport, league) -> set of abbreviations we care about
    team_map: dict[tuple, set] = {}
    for team in teams_config:
        key = (team["sport"], team["league"])
        team_map.setdefault(key, set()).add(team["abbreviation"].upper())
        endpoints_seen.add(key)

    live_games = []

    for sport, league in endpoints_seen:
        data = _fetch_scoreboard(sport, league)
        events = data.get("events", [])
        wanted_abbrs = team_map[(sport, league)]

        for event in events:
            game = _parse_game(event)
            if game["status"] != "in":
                continue
            # Check whether any configured team is playing
            if (
                game["home_abbr"].upper() in wanted_abbrs
                or game["away_abbr"].upper() in wanted_abbrs
            ):
                game["sport"] = sport
                game["league"] = league
                live_games.append(game)

    return live_games


# ---------------------------------------------------------------------------
# Background poller (mirrors the Overhead class pattern)
# ---------------------------------------------------------------------------

class SportsPoller:
    """
    Polls ESPN in a background thread and exposes the latest live game data.

    Usage
    -----
        poller = SportsPoller(teams_config=SPORTS_TEAMS)
        poller.grab_data()          # kick off first fetch
        ...
        if poller.new_data:
            games = poller.data     # clears the new_data flag
        if poller.score_changed:
            ...                     # prioritise showing scores
    """

    def __init__(self, teams_config: list):
        self._teams_config = teams_config
        self._lock = Lock()
        self._data: list = []
        self._new_data: bool = False
        self._processing: bool = False
        self._score_changed: bool = False
        # Keyed by game_id -> (home_score, away_score) for change detection
        self._last_scores: dict = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def grab_data(self):
        """Spawn a background thread to fetch the latest scoreboard."""
        Thread(target=self._fetch, daemon=True).start()

    # ------------------------------------------------------------------
    # Properties (thread-safe)
    # ------------------------------------------------------------------

    @property
    def new_data(self) -> bool:
        with self._lock:
            return self._new_data

    @property
    def processing(self) -> bool:
        with self._lock:
            return self._processing

    @property
    def data(self) -> list:
        """Return latest game list and clear the new_data flag."""
        with self._lock:
            self._new_data = False
            return list(self._data)

    @property
    def data_is_empty(self) -> bool:
        with self._lock:
            return len(self._data) == 0

    @property
    def score_changed(self) -> bool:
        """True if a score change was detected since the last check."""
        with self._lock:
            changed = self._score_changed
            self._score_changed = False
            return changed

    @property
    def has_live_game(self) -> bool:
        with self._lock:
            return any(g["status"] == "in" for g in self._data)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fetch(self):
        with self._lock:
            self._new_data = False
            self._processing = True

        try:
            live_games = get_live_games(self._teams_config)
        except Exception as exc:
            logger.error("SportsPoller fetch error: %s", exc)
            live_games = []

        # Detect score changes
        score_changed = False
        current_scores = {}
        for game in live_games:
            gid = game["game_id"]
            current_scores[gid] = (game["home_score"], game["away_score"])
            if gid in self._last_scores:
                if self._last_scores[gid] != current_scores[gid]:
                    score_changed = True
            # A brand-new live game also counts as a "change"
            else:
                score_changed = True

        with self._lock:
            self._data = live_games
            self._new_data = True
            self._processing = False
            self._last_scores = current_scores
            if score_changed:
                self._score_changed = True
