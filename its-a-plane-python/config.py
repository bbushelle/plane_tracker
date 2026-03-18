# ---------------------------------------------------------------------------
# Location — auto-detected from WiFi SSID at startup.
# Falls back to the hardcoded defaults below if detection fails.
# To add a new SSID, edit its-a-plane-python/utilities/location.py.
# ---------------------------------------------------------------------------
try:
    from utilities.location import get_location as _get_location
    _detected_location, _detected_zone, _detected_airport = _get_location()
except Exception:
    _detected_location, _detected_zone, _detected_airport = None, None, None

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

TEMPERATURE_LOCATION = f"{LOCATION_HOME[0]},{LOCATION_HOME[1]}" #same as location home
TOMORROW_API_KEY = "wQblVAgqhtUHIBTltJgfK39zT9eR01Ep" # Get an API key from https://tomorrow.io they only allows 25 pulls an hour, if you reach the limit you'll need to wait until the next hour 
TEMPERATURE_UNITS = "imperial" #can use "metric" if you want, same for distance 
DISTANCE_UNITS = "imperial"
CLOCK_FORMAT = "12hr" #use 12hr or 24hr
MIN_ALTITUDE = 2000 #feet above sea level. If you live at 1000ft then you'd want to make yours ~3000 etc. I use 2000 to weed out some of the smaller general aviation traffic. 
BRIGHTNESS = 100
BRIGHTNESS_NIGHT = 50
NIGHT_BRIGHTNESS = False #True for on False for off
NIGHT_START = "22:00" #dims screen between these hours
NIGHT_END = "06:00"
GPIO_SLOWDOWN = 2 #depends what Pi you have I use 2 for Pi 3 and 1 for Pi Zero
JOURNEY_CODE_SELECTED = _detected_airport if _detected_airport else "ORD" #your home airport code ALL CAPS ie ORD
JOURNEY_BLANK_FILLER = " ? " #what to display if theres no airport code
HAT_PWM_ENABLED = False #only if you haven't soldered the PWM bridge use True if you did
FORECAST_DAYS = 3 #today plus the next two days
EMAIL = "" #insert your email address between the " ie "example@example.com" to recieve emails when there is a new top 3 flight. Leave "" to recieve no emails. It will log/local webpage regardless
MAX_FARTHEST = 3 #the amount of furthest flights you want in your log
MAX_CLOSEST = 3 #the amount of closest flights to your house you want in your log

# ---------------------------------------------------------------------------
# Sports Scores — defaults below are overridden by web/user_config.json if present.
# Use the web interface (/settings) to change teams and timing without editing this file.
# ---------------------------------------------------------------------------
import json as _json, os as _os
_USER_CONFIG_FILE = _os.path.join(_os.path.dirname(__file__), "web", "user_config.json")
try:
    with open(_USER_CONFIG_FILE, "r", encoding="utf-8") as _f:
        _user_cfg = _json.load(_f)
except Exception:
    _user_cfg = {}

SPORTS_ENABLED = True
SPORTS_DISPLAY_INTERVAL = _user_cfg.get("sports_display_interval", 30)
SPORTS_SCORE_DELAY       = _user_cfg.get("sports_score_delay", 10)
SPORTS_TEAMS             = _user_cfg.get("sports_teams", [
    {"name": "Edmonton Oilers", "abbreviation": "EDM", "sport": "hockey", "league": "nhl"},
    {"name": "Green Bay Packers", "abbreviation": "GB", "sport": "football", "league": "nfl"},
])

