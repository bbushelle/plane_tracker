# Plane Tracker

## Overview
This is based off of this project but with some modifications - https://github.com/c0wsaysmoo/plane-tracker-rgb-pi?tab=readme-ov-file

## Current Setup
- Hardware: Raspberry Pi 3 Model A+, hostname `autism-pi`
- Running the c0wsaysmoo plane-tracker project
- Primary config file: `/home/tyler/its-a-plane-python/config.py`
- SSH credentials are stored in Claude memory (not in this repo)

## Project Goals & Specifications

### 1. Git Auto-Update (Nightly Pull)
- The pi should check for upstream changes before pulling (don't pull if nothing to update)
- If changes are found, pull and restart affected services
- Log all results (success, failure, what changed)
- Configured via a cron job with an easily adjustable schedule
- Script should be robust: handle conflicts, log errors, and avoid breaking a running system silently

### 2. Location (LOCATION_HOME)
- The pi moves between 3 different SSIDs
- Location is determined by current SSID — each SSID maps to a lat/lon pair
- SSID names, passwords, and lat/lon mappings will be provided and stored in a config file (not hardcoded)
- LOCATION_HOME should be set automatically at startup/network change based on detected SSID

### 3. Zone (ZONE_HOME)
- Automatically calculated as a 3-mile radius around LOCATION_HOME
- Should update whenever LOCATION_HOME changes

### 4. Sports Scores Display
- API: `site.api.espn.com/apis/site/v2`
- Display scores during **live games only** (configurable behavior for future flexibility)
- When a live game is active, alternate between plane display and scores at a **configurable interval**
- Also trigger a score display immediately when a score change is detected
- Initial teams: Edmonton Oilers (NHL), Green Bay Packers (NFL)
- Teams and leagues are fully configurable (add/remove via config, no code changes needed)

### 5. Weather Data Cache
- Cache weather data to avoid unnecessary re-fetching on restart
- Data is considered **fresh if fetched within the last 4 hours**
- On startup, check cache age — use cached data if fresh, re-fetch if stale

### 6. Tailscale Remote Access
- Set up Tailscale on the pi for remote SSH access while away
- Provide a **setup guide** (not an automated script)

## Documentation
- Create and maintain documentation as features are built
- Docs should live in a `/docs` directory in this repo
