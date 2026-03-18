# Weather Cache

## Overview

`temperature.py` caches responses from the tomorrow.io API to a local JSON file so that weather data survives process restarts and avoids unnecessary API calls against the 25-requests-per-hour rate limit.

## Cache file location

```
its-a-plane-python/.weather_cache.json
```

The path is resolved at runtime relative to `temperature.py` using `os.path`, so it works regardless of where the repository is cloned. The file is excluded from version control via `.gitignore`.

## Cache structure

```json
{
  "written_at": "2026-03-17T14:00:00.000000",
  "data": {
    "realtime": {
      "temperature": 52.3,
      "humidity": 61.0
    },
    "forecast_intervals": [ ... ]
  }
}
```

`written_at` is a UTC ISO-8601 timestamp recorded each time the cache is written. Both the realtime reading and the forecast are stored in the same file under separate keys so that one successful API call does not evict the other.

## Cache lifetime

The cache is considered **fresh** if it was written less than **4 hours** ago. On each call to `grab_temperature_and_humidity()` or `grab_forecast()`:

1. The cache file is read.
2. If the cache exists and is fresh, the cached value is returned immediately — no API call is made.
3. If the cache is missing or stale, the API is called. On success the result is written back to the cache before returning.
4. If the API call fails (network error, DNS failure, etc.) and a stale cache entry exists, a warning is logged and the stale value is returned as a fallback rather than returning nothing.

## Forcing a refresh

Delete the cache file to force the next call to hit the API regardless of age:

```bash
rm /path/to/its-a-plane-python/.weather_cache.json
```

On the Pi specifically:

```bash
rm ~/plane-tracker/its-a-plane-python/.weather_cache.json
```

The file will be recreated automatically on the next successful API response.
