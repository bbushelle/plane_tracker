"""
setup/theme.py

Loads user-configurable display colours from web/user_config.json and
exports them as named constants.  Scenes import from here instead of
hardcoding colours from setup.colours.

Read once at import time — changes take effect after restarting the Pi.
"""

import json
import os

from rgbmatrix import graphics
from setup import colours

_USER_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "web", "user_config.json",
)


def _load(key: str, default):
    """Return a graphics.Color from a #RRGGBB entry in user_config, or default."""
    try:
        with open(_USER_CONFIG_PATH) as f:
            cfg = json.load(f)
        hex_val = cfg.get(key, "")
        if hex_val and len(hex_val) == 7 and hex_val.startswith("#"):
            r = int(hex_val[1:3], 16)
            g = int(hex_val[3:5], 16)
            b = int(hex_val[5:7], 16)
            return graphics.Color(r, g, b)
    except Exception:
        pass
    return default


# ---------------------------------------------------------------------------
# Clock
# ---------------------------------------------------------------------------
CLOCK_DAY   = _load("clock_day_colour",   colours.LIGHT_ORANGE)   # #fea727
CLOCK_NIGHT = _load("clock_night_colour", colours.LIGHT_BLUE)     # #28b7f6

# ---------------------------------------------------------------------------
# Flight details  (scrolling flight-number line)
# ---------------------------------------------------------------------------
FLIGHT_NUM_ALPHA   = _load("flight_num_alpha_colour",   colours.LIGHT_PURPLE)  # #aa46bc
FLIGHT_NUM_NUMERIC = _load("flight_num_numeric_colour", colours.LIGHT_ORANGE)  # #fea727

# ---------------------------------------------------------------------------
# Plane details  (plane-type + distance/direction row)
# ---------------------------------------------------------------------------
PLANE      = _load("plane_colour",          colours.LIGHT_MID_BLUE)  # #42a4f4
PLANE_DIST = _load("plane_distance_colour", colours.LIGHT_PINK)      # #ec417b

# ---------------------------------------------------------------------------
# Days forecast  (day name, low temp, high temp)
# ---------------------------------------------------------------------------
FORECAST_DAY   = _load("forecast_day_colour",      colours.LIGHT_PINK)         # #ec417b
FORECAST_MIN_T = _load("forecast_min_temp_colour", colours.LIGHT_MID_BLUE)     # #42a4f4
FORECAST_MAX_T = _load("forecast_max_temp_colour", colours.LIGHT_DARK_ORANGE)  # #ff7142

# ---------------------------------------------------------------------------
# Sports scores
# ---------------------------------------------------------------------------
SPORTS_HOME = _load("sports_home_colour", colours.LIGHT_ORANGE)  # #fea727
SPORTS_AWAY = _load("sports_away_colour", colours.LIGHT_BLUE)    # #28b7f6
