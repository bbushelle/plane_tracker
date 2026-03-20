#!/usr/bin/python3
from flask import Flask, render_template, jsonify, send_from_directory, request
import json
import logging
import os
import subprocess
import sys
import time

log = logging.getLogger(__name__)

# /web is the folder that this file lives in
WEB_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.abspath(os.path.join(WEB_DIR, ".."))

# SSID location map from .env — used to enumerate known SSIDs in /settings/location
sys.path.insert(0, BASE_DIR)
try:
    from utilities.location import SSID_LOCATIONS
except Exception:
    SSID_LOCATIONS = {}

app = Flask(
    __name__,
    template_folder=os.path.join(WEB_DIR, "templates"),
    static_folder=os.path.join(WEB_DIR, "static")
)

# JSON flight logs (stored outside /web)
CLOSEST_FILE = os.path.join(BASE_DIR, "close.txt")
FARTHEST_FILE = os.path.join(BASE_DIR, "farthest.txt")

# User-editable config overrides (gitignored)
USER_CONFIG_FILE = os.path.join(WEB_DIR, "user_config.json")

# Defaults pulled from config.py — used as fallback when user_config.json is missing keys
CONFIG_DEFAULTS = {
    "sports_teams": [
        {"name": "Edmonton Oilers", "abbreviation": "EDM", "sport": "hockey", "league": "nhl"},
        {"name": "Green Bay Packers", "abbreviation": "GB", "sport": "football", "league": "nfl"},
        {"name": "St. Louis Blues", "abbreviation": "STL", "sport": "hockey", "league": "nhl"},
    ],
    "sports_score_delay": 10,
    "sports_display_interval": 30,
    # Display brightness
    "brightness": 100,
    "brightness_night": 50,
    "night_brightness": False,
    "night_start": "22:00",
    "night_end": "06:00",
    # Display theme colours — all #RRGGBB hex strings
    # Clock
    "clock_day_colour":          "#fea727",  # colours.LIGHT_ORANGE
    "clock_night_colour":        "#28b7f6",  # colours.LIGHT_BLUE
    # Flight details (scrolling flight number)
    "flight_num_alpha_colour":   "#aa46bc",  # colours.LIGHT_PURPLE
    "flight_num_numeric_colour": "#fea727",  # colours.LIGHT_ORANGE
    # Plane details (plane type + distance row)
    "plane_colour":              "#42a4f4",  # colours.LIGHT_MID_BLUE
    "plane_distance_colour":     "#ec417b",  # colours.LIGHT_PINK
    # Forecast (day name, low/high temps)
    "forecast_day_colour":       "#ec417b",  # colours.LIGHT_PINK
    "forecast_min_temp_colour":  "#42a4f4",  # colours.LIGHT_MID_BLUE
    "forecast_max_temp_colour":  "#ff7142",  # colours.LIGHT_DARK_ORANGE
    # Sports scores
    "sports_home_colour":        "#fea727",  # colours.LIGHT_ORANGE
    "sports_away_colour":        "#28b7f6",  # colours.LIGHT_BLUE
    # Per-SSID location overrides — keyed by SSID name
    "ssid_overrides": {},
}

# Transient sports-pause file — written here, read by the display process
SPORTS_PAUSE_FILE = os.path.join(BASE_DIR, "sports_pause.json")

# Transient test-scene file — written here, read by the display process
TEST_SCENE_FILE = os.path.join(BASE_DIR, "test_scene.json")
_VALID_TEST_MODES = {"clock", "flight", "sports", "forecast", "cycle"}


def load_user_config():
    try:
        with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_user_config(data):
    with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_merged_config():
    user = load_user_config()
    merged = dict(CONFIG_DEFAULTS)
    merged.update(user)
    return merged


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Could not load {path}: {e}")
        return default


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/closest/json")
def closest_json():
    return jsonify(load_json(CLOSEST_FILE, {}))


@app.get("/farthest/json")
def farthest_json():
    return jsonify(load_json(FARTHEST_FILE, []))


@app.get("/closest")
def closest_page():
    return render_template("closest_map.html")


@app.get("/farthest")
def farthest_page():
    return render_template("farthest_map.html")


# Serve PNG map snapshots from /web/static/maps/
@app.get("/maps/<path:filename>")
def maps(filename):
    maps_dir = os.path.join(WEB_DIR, "static/maps")
    return send_from_directory(maps_dir, filename)


# --- Settings page ---

@app.get("/settings")
def settings_page():
    return render_template("settings.html")


@app.get("/settings/config")
def settings_config():
    return jsonify(get_merged_config())


@app.post("/settings/teams/add")
def settings_teams_add():
    body = request.get_json(force=True, silent=True) or {}
    name = body.get("name", "").strip()
    abbreviation = body.get("abbreviation", "").strip()
    sport = body.get("sport", "").strip()
    league = body.get("league", "").strip()

    if not all([name, abbreviation, sport, league]):
        return jsonify({"error": "All fields are required"}), 400

    cfg = get_merged_config()
    teams = cfg.get("sports_teams", [])

    if any(t["abbreviation"].upper() == abbreviation.upper() for t in teams):
        return jsonify({"error": f"Team with abbreviation '{abbreviation}' already exists"}), 409

    teams.append({"name": name, "abbreviation": abbreviation, "sport": sport, "league": league})
    cfg["sports_teams"] = teams

    user_cfg = load_user_config()
    user_cfg["sports_teams"] = teams
    save_user_config(user_cfg)

    return jsonify({"status": "ok", "teams": teams})


@app.post("/settings/teams/remove")
def settings_teams_remove():
    body = request.get_json(force=True, silent=True) or {}
    abbreviation = body.get("abbreviation", "").strip()

    if not abbreviation:
        return jsonify({"error": "abbreviation is required"}), 400

    cfg = get_merged_config()
    teams = [t for t in cfg.get("sports_teams", []) if t["abbreviation"].upper() != abbreviation.upper()]

    user_cfg = load_user_config()
    user_cfg["sports_teams"] = teams
    save_user_config(user_cfg)

    return jsonify({"status": "ok", "teams": teams})


@app.post("/settings/delays")
def settings_delays():
    body = request.get_json(force=True, silent=True) or {}

    try:
        score_delay = int(body.get("sports_score_delay"))
        display_interval = int(body.get("sports_display_interval"))
    except (TypeError, ValueError):
        return jsonify({"error": "Both values must be integers"}), 400

    if score_delay <= 0 or display_interval <= 0:
        return jsonify({"error": "Both values must be positive integers"}), 400

    user_cfg = load_user_config()
    user_cfg["sports_score_delay"] = score_delay
    user_cfg["sports_display_interval"] = display_interval
    save_user_config(user_cfg)

    return jsonify({"status": "ok", "sports_score_delay": score_delay, "sports_display_interval": display_interval})


# --- Brightness settings ---

@app.post("/settings/brightness")
def settings_brightness():
    body = request.get_json(force=True, silent=True) or {}

    try:
        brightness = int(body.get("brightness", 100))
        brightness_night = int(body.get("brightness_night", 50))
    except (TypeError, ValueError):
        return jsonify({"error": "Brightness values must be integers"}), 400

    if not (0 <= brightness <= 100 and 0 <= brightness_night <= 100):
        return jsonify({"error": "Brightness must be between 0 and 100"}), 400

    night_brightness = bool(body.get("night_brightness", False))
    night_start = str(body.get("night_start", "22:00")).strip()
    night_end = str(body.get("night_end", "06:00")).strip()

    def valid_time(t):
        parts = t.split(":")
        return len(parts) == 2 and all(p.isdigit() for p in parts)

    if not valid_time(night_start) or not valid_time(night_end):
        return jsonify({"error": "Times must be in HH:MM format"}), 400

    user_cfg = load_user_config()
    user_cfg.update({
        "brightness": brightness,
        "brightness_night": brightness_night,
        "night_brightness": night_brightness,
        "night_start": night_start,
        "night_end": night_end,
    })
    save_user_config(user_cfg)
    return jsonify({"status": "ok"})


# --- Display theme (sports score colours) ---

_THEME_KEYS = [
    "clock_day_colour", "clock_night_colour",
    "flight_num_alpha_colour", "flight_num_numeric_colour",
    "plane_colour", "plane_distance_colour",
    "forecast_day_colour", "forecast_min_temp_colour", "forecast_max_temp_colour",
    "sports_home_colour", "sports_away_colour",
]


@app.post("/settings/theme")
def settings_theme():
    body = request.get_json(force=True, silent=True) or {}

    def valid_hex(s):
        return isinstance(s, str) and len(s) == 7 and s.startswith("#") and \
               all(c in "0123456789abcdefABCDEF" for c in s[1:])

    updates = {}
    for key in _THEME_KEYS:
        val = body.get(key, "").strip()
        if val and not valid_hex(val):
            return jsonify({"error": f"Invalid colour for {key}: must be #RRGGBB"}), 400
        if val:
            updates[key] = val

    user_cfg = load_user_config()
    user_cfg.update(updates)
    save_user_config(user_cfg)
    return jsonify({"status": "ok"})


# --- Sports score pause ---

@app.get("/settings/sports/pause")
def sports_pause_status():
    try:
        with open(SPORTS_PAUSE_FILE) as f:
            data = json.load(f)
        expires_at = data.get("expires_at", 0)
        remaining = max(0, expires_at - time.time())
        return jsonify({"paused": remaining > 0, "expires_at": expires_at,
                        "remaining_seconds": int(remaining)})
    except FileNotFoundError:
        return jsonify({"paused": False})


@app.post("/settings/sports/pause")
def sports_pause_set():
    body = request.get_json(force=True, silent=True) or {}
    try:
        hours = float(body.get("hours", 1))
    except (TypeError, ValueError):
        hours = 1.0
    expires_at = time.time() + hours * 3600
    with open(SPORTS_PAUSE_FILE, "w") as f:
        json.dump({"expires_at": expires_at}, f)
    return jsonify({"status": "paused", "expires_at": expires_at,
                    "remaining_seconds": int(hours * 3600)})


@app.post("/settings/sports/resume")
def sports_pause_clear():
    try:
        os.remove(SPORTS_PAUSE_FILE)
    except FileNotFoundError:
        pass
    return jsonify({"status": "resumed"})


# --- Test scene controls ---

@app.get("/test/scene")
def test_scene_get():
    try:
        with open(TEST_SCENE_FILE) as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"mode": None})


@app.post("/test/scene")
def test_scene_set():
    body = request.get_json(force=True, silent=True) or {}
    mode = body.get("mode")  # None clears test mode

    if mode is not None and mode not in _VALID_TEST_MODES:
        return jsonify({"error": f"Invalid mode. Valid: {sorted(_VALID_TEST_MODES)}"}), 400

    if mode is None:
        try:
            os.remove(TEST_SCENE_FILE)
        except FileNotFoundError:
            pass
    else:
        with open(TEST_SCENE_FILE, "w") as f:
            json.dump({"mode": mode}, f)

    return jsonify({"status": "ok", "mode": mode})


# --- Location settings (per-SSID min altitude + scan radius) ---

_LOCATION_DEFAULTS = {"min_altitude": 2000, "radius_miles": 3.0}


@app.get("/settings/location")
def settings_location_get():
    overrides = get_merged_config().get("ssid_overrides", {})
    ssids = []
    for ssid, entry in SSID_LOCATIONS.items():
        o = overrides.get(ssid, {})
        ssids.append({
            "ssid": ssid,
            "airport": entry.get("airport", ""),
            "min_altitude": o.get("min_altitude", _LOCATION_DEFAULTS["min_altitude"]),
            "radius_miles": o.get("radius_miles", _LOCATION_DEFAULTS["radius_miles"]),
        })
    return jsonify({"ssids": ssids})


@app.post("/settings/location")
def settings_location_save():
    body = request.get_json(force=True, silent=True) or {}
    ssid = body.get("ssid", "").strip()

    if not ssid or ssid not in SSID_LOCATIONS:
        return jsonify({"error": f"Unknown SSID '{ssid}'"}), 400

    try:
        min_altitude = int(body.get("min_altitude"))
        radius_miles = float(body.get("radius_miles"))
    except (TypeError, ValueError):
        return jsonify({"error": "min_altitude must be an integer, radius_miles must be a number"}), 400

    if min_altitude < 0:
        return jsonify({"error": "min_altitude must be 0 or greater"}), 400
    if radius_miles <= 0:
        return jsonify({"error": "radius_miles must be greater than 0"}), 400

    user_cfg = load_user_config()
    overrides = user_cfg.get("ssid_overrides", {})
    overrides[ssid] = {"min_altitude": min_altitude, "radius_miles": radius_miles}
    user_cfg["ssid_overrides"] = overrides
    save_user_config(user_cfg)

    return jsonify({"status": "ok", "ssid": ssid, "min_altitude": min_altitude, "radius_miles": radius_miles})


# --- System controls ---

APP_SCRIPT = "/home/tyler/plane-tracker/its-a-plane-python/its-a-plane.py"
APP_LOG    = "/home/tyler/plane-tracker/logs/app.log"

@app.post("/system/app/restart")
def system_app_restart():
    """Kill and relaunch its-a-plane.py without rebooting the Pi.

    Writes the restart logic to a temp script and runs it so that bash's own
    cmdline never contains 'its-a-plane.py' — otherwise pkill would match and
    kill the bash process before it could relaunch the app.
    """
    import stat, tempfile
    script = (
        "#!/bin/bash\n"
        "sleep 3\n"
        'pkill -f "its-a-plane.py" || true\n'
        'pkill -f "web/app.py" || true\n'
        "sleep 2\n"
        f'nohup /usr/bin/python3 "{APP_SCRIPT}" >> "{APP_LOG}" 2>&1 &\n'
        'rm -f "$0"\n'
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write(script)
        tmp = f.name
    os.chmod(tmp, stat.S_IRWXU)
    subprocess.Popen(["bash", tmp])
    return jsonify({"status": "restarting app"})


@app.post("/system/restart")
def system_restart():
    subprocess.Popen(["sudo", "reboot"])
    return jsonify({"status": "rebooting"})


@app.post("/system/shutdown")
def system_shutdown():
    subprocess.Popen(["sudo", "shutdown", "-h", "now"])
    return jsonify({"status": "shutting down"})


# --- Log viewer ---

LOGS_DIR = os.path.join(BASE_DIR, "..", "logs")
ALLOWED_LOGS = {"app": "app.log", "update": "update.log"}

@app.get("/logs/<logname>")
def view_log(logname):
    if logname not in ALLOWED_LOGS:
        return jsonify({"error": "Unknown log"}), 404
    log_path = os.path.abspath(os.path.join(LOGS_DIR, ALLOWED_LOGS[logname]))
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return jsonify({"log": logname, "lines": lines[-200:]})
    except FileNotFoundError:
        return jsonify({"log": logname, "lines": []})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    app.run(host="0.0.0.0", port=8080, debug=False)
