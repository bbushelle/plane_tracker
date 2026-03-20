# ---------------------------------------------------------------------------
# User config overrides — loaded first so all settings below can reference it.
# Managed via the web interface (/settings); saved to web/user_config.json.
# ---------------------------------------------------------------------------
import json as _json, os as _os
_USER_CONFIG_FILE = _os.path.join(_os.path.dirname(__file__), "web", "user_config.json")
try:
    with open(_USER_CONFIG_FILE, "r", encoding="utf-8") as _f:
        _user_cfg = _json.load(_f)
except Exception:
    _user_cfg = {}

# ---------------------------------------------------------------------------
# Location — auto-detected from WiFi SSID at startup.
# Falls back to the hardcoded defaults below if detection fails.
# ---------------------------------------------------------------------------
try:
    from utilities.location import get_location as _get_location, get_current_ssid as _get_current_ssid
    _detected_location, _detected_zone, _detected_airport = _get_location()
    _current_ssid = _get_current_ssid()
except Exception:
    _detected_location, _detected_zone, _detected_airport = None, None, None
    _current_ssid = None

if _detected_location and _detected_zone:
    LOCATION_HOME = _detected_location
    ZONE_HOME = _detected_zone
else:
    # Hardcoded fallback (milloosh / home network)
    ZONE_HOME = {
        "tl_y": 42.327251, # Top-Left Latitude  — 3-mile radius around LOCATION_HOME
        "tl_x": -88.028286, # Top-Left Longitude
        "br_y": 42.240251, # Bottom-Right Latitude
        "br_x": -87.910646  # Bottom-Right Longitude
    }
    LOCATION_HOME = [
        42.283751, # Latitude (deg)
        -87.969466 # Longitude (deg)
    ]

TEMPERATURE_LOCATION = f"{LOCATION_HOME[0]},{LOCATION_HOME[1]}"
TOMORROW_API_KEY = "wQblVAgqhtUHIBTltJgfK39zT9eR01Ep"
TEMPERATURE_UNITS = "imperial"
DISTANCE_UNITS = "imperial"
CLOCK_FORMAT = "12hr"

# Min altitude — per-SSID override from user_config.json, fallback to 2000 ft
_ssid_override = _user_cfg.get("ssid_overrides", {}).get(_current_ssid or "", {})
MIN_ALTITUDE = int(_ssid_override.get("min_altitude", 2000))

BRIGHTNESS = 100
BRIGHTNESS_NIGHT = 50
NIGHT_BRIGHTNESS = False
NIGHT_START = "22:00"
NIGHT_END = "06:00"
GPIO_SLOWDOWN = 2
JOURNEY_CODE_SELECTED = _detected_airport if _detected_airport else "ORD"
JOURNEY_BLANK_FILLER = " ? "
HAT_PWM_ENABLED = False
FORECAST_DAYS = 3
EMAIL = ""
MAX_FARTHEST = 3
MAX_CLOSEST = 3

# ---------------------------------------------------------------------------
# Sports Scores — overridden by web/user_config.json if present.
# ---------------------------------------------------------------------------
SPORTS_ENABLED = True
SPORTS_DISPLAY_INTERVAL = _user_cfg.get("sports_display_interval", 30)
SPORTS_SCORE_DELAY       = _user_cfg.get("sports_score_delay", 10)
SPORTS_TEAMS             = _user_cfg.get("sports_teams", [
    {"name": "Edmonton Oilers", "abbreviation": "EDM", "sport": "hockey", "league": "nhl"},
    {"name": "Green Bay Packers", "abbreviation": "GB", "sport": "football", "league": "nfl"},
    {"name": "St. Louis Blues", "abbreviation": "STL", "sport": "hockey", "league": "nhl"},
])

# ---------------------------------------------------------------------------
# Display brightness — overridden by web/user_config.json if present.
# ---------------------------------------------------------------------------
if "brightness" in _user_cfg:
    BRIGHTNESS = _user_cfg["brightness"]
if "brightness_night" in _user_cfg:
    BRIGHTNESS_NIGHT = _user_cfg["brightness_night"]
if "night_brightness" in _user_cfg:
    NIGHT_BRIGHTNESS = _user_cfg["night_brightness"]
if "night_start" in _user_cfg:
    NIGHT_START = _user_cfg["night_start"]
if "night_end" in _user_cfg:
    NIGHT_END = _user_cfg["night_end"]
