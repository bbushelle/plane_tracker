"""
Automatic location detection based on current WiFi SSID.

At startup, detects the connected SSID via nmcli and returns the matching
LOCATION_HOME (lat/lon) and a computed ZONE_HOME bounding box (3-mile radius).

If the SSID is not in the map, falls back to the values hardcoded in config.py.

SSID_LOCATIONS is loaded from a .env file at the repo root (two directories
above this file). If the file or variable is missing, an empty dict is used
and the app falls back to config.py defaults.
"""

import json
import math
import os
import subprocess

from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Load SSID → location mapping from .env
# The .env file lives at the repo root: ../../ relative to this file.
# ---------------------------------------------------------------------------
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(dotenv_path=os.path.abspath(_ENV_PATH))

try:
    SSID_LOCATIONS = json.loads(os.environ.get("SSID_LOCATIONS", "{}"))
except (json.JSONDecodeError, TypeError):
    SSID_LOCATIONS = {}

# Radius in miles to use for ZONE_HOME bounding box
ZONE_RADIUS_MILES = 3.0


def _miles_to_degrees(miles_lat, miles_lon, lat):
    """Convert a distance in miles to degree offsets at a given latitude."""
    km_per_degree_lat = 111.0
    km_per_degree_lon = 111.0 * math.cos(math.radians(lat))
    km = miles_lat * 1.60934
    lat_offset = km / km_per_degree_lat
    lon_offset = (miles_lon * 1.60934) / km_per_degree_lon
    return lat_offset, lon_offset


def _bounding_box(lat, lon, radius_miles):
    """Return a ZONE_HOME bounding box dict for the given centre and radius."""
    lat_off, lon_off = _miles_to_degrees(radius_miles, radius_miles, lat)
    return {
        "tl_y": round(lat + lat_off, 8),   # Top-Left Latitude
        "tl_x": round(lon - lon_off, 8),   # Top-Left Longitude
        "br_y": round(lat - lat_off, 8),   # Bottom-Right Latitude
        "br_x": round(lon + lon_off, 8),   # Bottom-Right Longitude
    }


def get_current_ssid():
    """Return the currently connected WiFi SSID, or None if not connected."""
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if line.startswith("yes:"):
                return line.split(":", 1)[1].strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def get_location():
    """
    Detect the current SSID and return (location_home, zone_home).

    location_home: [lat, lon]
    zone_home:     {"tl_y": ..., "tl_x": ..., "br_y": ..., "br_x": ...}

    Returns None for both if detection fails (caller should use config.py defaults).
    """
    ssid = get_current_ssid()
    if ssid is None:
        return None, None, None

    entry = SSID_LOCATIONS.get(ssid)
    if entry is None:
        return None, None, None

    lat, lon = entry["lat"], entry["lon"]
    location_home = [lat, lon]
    zone_home = _bounding_box(lat, lon, ZONE_RADIUS_MILES)
    airport = entry.get("airport")
    return location_home, zone_home, airport
