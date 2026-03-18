#!/usr/bin/env bash
# update.sh — Pull latest changes from origin/main and restart the plane-tracker
# service if an update was applied.
#
# Safe to run repeatedly (idempotent). All output is appended to update.log
# with timestamps. Intended to be invoked by cron; see install-cron.sh.

set -euo pipefail

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_DIR="/home/tyler/plane-tracker"
APP_SCRIPT="/home/tyler/plane-tracker/its-a-plane-python/its-a-plane.py"
APP_LOG="/home/tyler/plane-tracker/logs/app.log"
UPDATE_LOG="/home/tyler/plane-tracker/logs/update.log"

# ---------------------------------------------------------------------------
# Logging helper — every message is prefixed with an ISO-8601 timestamp.
# ---------------------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] $*" >> "$UPDATE_LOG"
}

# ---------------------------------------------------------------------------
# Bootstrap: make sure the log directory exists before we try to write to it.
# ---------------------------------------------------------------------------
mkdir -p "$(dirname "$UPDATE_LOG")"
mkdir -p "$(dirname "$APP_LOG")"

log "---------------------------------------------------------------------"
log "Starting update check"

# ---------------------------------------------------------------------------
# Verify the repo directory exists.
# ---------------------------------------------------------------------------
if [[ ! -d "$REPO_DIR/.git" ]]; then
    log "ERROR: $REPO_DIR is not a git repository. Aborting."
    exit 1
fi

cd "$REPO_DIR"

# ---------------------------------------------------------------------------
# Fetch from origin without merging so we can compare refs safely.
# ---------------------------------------------------------------------------
log "Fetching from origin..."
if ! git fetch origin main >> "$UPDATE_LOG" 2>&1; then
    log "ERROR: git fetch failed. Check network connectivity and remote URL."
    exit 1
fi

# ---------------------------------------------------------------------------
# Compare local HEAD to origin/main.
# ---------------------------------------------------------------------------
LOCAL_REF=$(git rev-parse HEAD)
REMOTE_REF=$(git rev-parse origin/main)

if [[ "$LOCAL_REF" == "$REMOTE_REF" ]]; then
    log "Already up to date (HEAD=$LOCAL_REF). Nothing to do."
    exit 0
fi

# ---------------------------------------------------------------------------
# Log incoming commits so the update history is auditable.
# ---------------------------------------------------------------------------
log "Update available: local=$LOCAL_REF  remote=$REMOTE_REF"
log "Incoming commits:"
git log --oneline "$LOCAL_REF..$REMOTE_REF" | while IFS= read -r line; do
    log "  $line"
done

# ---------------------------------------------------------------------------
# Pull the changes.
# ---------------------------------------------------------------------------
log "Pulling changes..."
if ! git pull origin main >> "$UPDATE_LOG" 2>&1; then
    log "ERROR: git pull failed. The working tree may be dirty or there is a"
    log "       merge conflict. Resolve manually, then re-run this script."
    exit 1
fi

NEW_REF=$(git rev-parse HEAD)
log "Pull successful. HEAD is now $NEW_REF."

# ---------------------------------------------------------------------------
# Restart the plane-tracker application.
#
# The app is launched at boot via a @reboot cron entry and runs as a
# background process. We kill the existing instance (if any) and start a
# fresh one so it picks up the updated code.
# ---------------------------------------------------------------------------
log "Restarting plane-tracker application..."

# Kill any running instance — pkill exits non-zero when no process matched,
# which is fine (the process might already be dead).
if pkill -f "its-a-plane.py" >> "$UPDATE_LOG" 2>&1; then
    log "Stopped existing its-a-plane.py process."
else
    log "No running its-a-plane.py process found (will still launch fresh)."
fi

# Brief pause to let the process fully exit before we re-launch.
sleep 2

# Re-launch in the background; stdout/stderr go to app.log.
# 'nohup' ensures the process survives the script's exit.
nohup /usr/bin/python3 "$APP_SCRIPT" >> "$APP_LOG" 2>&1 &
CHILD_PID=$!

log "Launched its-a-plane.py with PID $CHILD_PID."
log "Update complete."
