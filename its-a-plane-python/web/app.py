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
    # Sports score colours (hex strings matching colours.LIGHT_ORANGE / LIGHT_BLUE)
    "sports_home_colour": "#fea727",
    "sports_away_colour": "#28b7f6",
}

# Transient sports-pause file — written here, read by the display process
SPORTS_PAUSE_FILE = os.path.join(BASE_DIR, "sports_pause.json")


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

@app.post("/settings/theme")
def settings_theme():
    body = request.get_json(force=True, silent=True) or {}

    def valid_hex(s):
        return isinstance(s, str) and len(s) == 7 and s.startswith("#") and \
               all(c in "0123456789abcdefABCDEF" for c in s[1:])

    home_colour = body.get("sports_home_colour", "").strip()
    away_colour = body.get("sports_away_colour", "").strip()

    if not valid_hex(home_colour) or not valid_hex(away_colour):
        return jsonify({"error": "Colours must be in #RRGGBB format"}), 400

    user_cfg = load_user_config()
    user_cfg["sports_home_colour"] = home_colour
    user_cfg["sports_away_colour"] = away_colour
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


# --- System controls ---

APP_SCRIPT = "/home/tyler/plane-tracker/its-a-plane-python/its-a-plane.py"
APP_LOG    = "/home/tyler/plane-tracker/logs/app.log"

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
