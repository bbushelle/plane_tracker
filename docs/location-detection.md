# Location Detection

## How It Works

At startup, `config.py` calls `utilities/location.py` to detect the current WiFi SSID using `nmcli`. It looks up the SSID in the `SSID_LOCATIONS` mapping and sets `LOCATION_HOME` and `ZONE_HOME` automatically.

If the SSID is not in the map, or if detection fails (no WiFi, nmcli unavailable), the app falls back to the hardcoded defaults in `config.py`.

## SSID Mappings

SSID names and their lat/lon coordinates are stored in a `.env` file at the repo root. This file is **gitignored** and must be copied to the Pi manually.

Format:
```
SSID_LOCATIONS={"YourSSID": {"lat": 44.12345, "lon": -88.12345}, "AnotherSSID": {"lat": 42.0, "lon": -87.5}}
```

`utilities/location.py` loads this value at startup using `python-dotenv`.

## Adding or Editing a Location

Edit the `.env` file in the repo root on your local machine:

```
SSID_LOCATIONS={"milloosh": {"lat": 42.283751, "lon": -87.969466}, "Komquat": {"lat": 44.60328619517002, "lon": -88.0988388865091}, "boosh-5": {"lat": 44.231570633645646, "lon": -88.3938172032542}}
```

Then copy the updated `.env` to the Pi:

```bash
scp .env tyler@autism-pi:/home/tyler/plane-tracker/.env
```

Reboot the Pi to apply the new mappings.

## WiFi Passwords

Passwords are **not stored in this repo**. They are stored in the Pi's NetworkManager config only.

To add a new network's password to the Pi:

```bash
sudo nmcli con add type wifi ssid 'YourSSID' con-name 'YourSSID' \
    wifi-sec.key-mgmt wpa-psk wifi-sec.psk 'yourpassword' \
    connection.autoconnect yes
```

## Current SSID Mappings

| SSID | Location |
|------|----------|
| milloosh | 42.283751, -87.969466 |
| Komquat | 44.60328619517002, -88.0988388865091 |
| boosh-5 | 44.231570633645646, -88.3938172032542 |

## Per-SSID Overrides (Web UI)

The web settings page (`/settings` → Location Settings) lets you override two values per SSID without editing `.env`:

| Setting | Default | Description |
|---------|---------|-------------|
| Min Altitude | 2000 ft | Flights below this are ignored |
| Radius | 3.0 mi | Bounding box radius around the home location |

Overrides are stored in `web/user_config.json` under the `ssid_overrides` key:

```json
{
  "ssid_overrides": {
    "milloosh": {"min_altitude": 1500, "radius_miles": 4.0}
  }
}
```

Changes take effect after **Restart App** (Settings → System Controls), not a full reboot.

## Zone Radius

The `ZONE_HOME` bounding box defaults to a **3-mile radius** around `LOCATION_HOME`. The radius used at startup is the per-SSID override from `user_config.json` if set, otherwise `ZONE_RADIUS_MILES = 3.0` from `utilities/location.py`.

## Verifying Detection

SSH into the pi and run:

```bash
cd /home/tyler/plane-tracker/its-a-plane-python
python3 -c "from utilities.location import get_current_ssid, get_location; print(get_current_ssid()); print(get_location())"
```
