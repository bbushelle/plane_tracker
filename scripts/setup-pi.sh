#!/usr/bin/env bash
# setup-pi.sh — One-time migration script: moves the plane-tracker from the
# original its-a-plane-python setup to the new git-managed repo layout.
#
# Safe to re-run (idempotent). All actions are logged to stdout with
# timestamps. Run this script directly on the Raspberry Pi as the 'tyler' user.
#
# Usage:
#   bash /path/to/setup-pi.sh
#
# After a successful run the application will be running from the new location
# and the nightly auto-update cron job will be installed.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REPO_URL="https://github.com/bbushelle/plane_tracker.git"
REPO_DIR="/home/tyler/plane-tracker"
OLD_DIR="/home/tyler/its-a-plane-python"

APP_SCRIPT="${REPO_DIR}/its-a-plane-python/its-a-plane.py"
APP_LOG="${REPO_DIR}/logs/app.log"
SETUP_LOG="${REPO_DIR}/logs/setup.log"

# Runtime data files that should survive the migration.
MIGRATE_FILES=(
    "close.txt"
    "farthest.txt"
)

# The old @reboot cron entry we want to remove.
OLD_CRON_PATTERN="its-a-plane-python/its-a-plane.py"

# The new @reboot cron entry we want to install.
NEW_CRON_LINE="@reboot sleep 60 && ${APP_SCRIPT} >> ${APP_LOG} 2>&1"

# ---------------------------------------------------------------------------
# Logging — writes to stdout AND to the setup log file (once the log dir
# exists). All messages are prefixed with an ISO-8601 timestamp.
# ---------------------------------------------------------------------------
_LOG_READY=0

log() {
    local msg="[$(date '+%Y-%m-%dT%H:%M:%S%z')] $*"
    echo "$msg"
    if [[ "$_LOG_READY" -eq 1 ]]; then
        echo "$msg" >> "$SETUP_LOG"
    fi
}

# ---------------------------------------------------------------------------
# Step banner — makes the output easy to skim.
# ---------------------------------------------------------------------------
step() {
    log ""
    log ">>> $*"
}

# ---------------------------------------------------------------------------
# Guard: must not run as root.
# ---------------------------------------------------------------------------
if [[ "$(id -u)" -eq 0 ]]; then
    echo "ERROR: Do not run this script as root. Run it as the 'tyler' user."
    exit 1
fi

# ---------------------------------------------------------------------------
# STEP 1 — Check prerequisites
# ---------------------------------------------------------------------------
step "STEP 1: Checking prerequisites"

if ! command -v git &>/dev/null; then
    log "ERROR: git is not installed. Install it with: sudo apt-get install -y git"
    exit 1
fi
log "git found: $(git --version)"

if ! command -v python3 &>/dev/null; then
    log "ERROR: python3 is not installed. Install it with: sudo apt-get install -y python3"
    exit 1
fi
log "python3 found: $(python3 --version)"

# Validate that the repo URL placeholder has been replaced.
if [[ "$REPO_URL" == "YOUR_REPO_URL" ]]; then
    log "ERROR: REPO_URL has not been set. Edit this script and replace"
    log "       YOUR_REPO_URL with the actual repository URL, then re-run."
    exit 1
fi

# ---------------------------------------------------------------------------
# STEP 2 — Clone the repository (skip if already present)
# ---------------------------------------------------------------------------
step "STEP 2: Cloning repository"

if [[ -d "${REPO_DIR}/.git" ]]; then
    log "Repository already exists at ${REPO_DIR}. Skipping clone."
else
    log "Cloning ${REPO_URL} → ${REPO_DIR} ..."
    git clone "$REPO_URL" "$REPO_DIR"
    log "Clone complete."
fi

# Now that the repo exists the log directory can be initialised.
mkdir -p "${REPO_DIR}/logs"
_LOG_READY=1
log "Log directory ready. Subsequent messages are also written to ${SETUP_LOG}."

# Ensure the main app script is executable.
if [[ -f "$APP_SCRIPT" ]]; then
    chmod +x "$APP_SCRIPT"
    log "Made ${APP_SCRIPT} executable."
else
    log "WARNING: ${APP_SCRIPT} not found in the cloned repo. Verify the repo"
    log "         contents — the application may not launch correctly."
fi

# ---------------------------------------------------------------------------
# STEP 3 — Install Python dependencies
# ---------------------------------------------------------------------------
step "STEP 3: Installing Python dependencies"

REQUIREMENTS="${REPO_DIR}/its-a-plane-python/requirements.txt"

if [[ -f "$REQUIREMENTS" ]]; then
    log "Installing from ${REQUIREMENTS} ..."
    pip3 install -r "$REQUIREMENTS"
    log "Dependencies installed."
else
    log "WARNING: requirements.txt not found at ${REQUIREMENTS}. Skipping."
fi

# ---------------------------------------------------------------------------
# STEP 3b — Check for .env file (gitignored, must be copied manually)
# ---------------------------------------------------------------------------
ENV_FILE="${REPO_DIR}/.env"

if [[ -f "$ENV_FILE" ]]; then
    log ".env file found at ${ENV_FILE}."
else
    log "WARNING: .env file not found at ${ENV_FILE}."
    log "  The app will fall back to config.py defaults for location settings."
    log "  To fix, copy your .env from your local machine:"
    log "    scp /path/to/plane_tracker/.env tyler@autism-pi:${ENV_FILE}"
    log "  Then restart the app."
fi

# ---------------------------------------------------------------------------
# STEP 4 — Migrate runtime data from the old location
# ---------------------------------------------------------------------------
step "STEP 3: Migrating runtime data"

DEST_DIR="${REPO_DIR}/its-a-plane-python"

for fname in "${MIGRATE_FILES[@]}"; do
    src="${OLD_DIR}/${fname}"
    dst="${DEST_DIR}/${fname}"

    if [[ ! -f "$src" ]]; then
        log "  ${fname}: not found in old location, skipping."
        continue
    fi

    if [[ -f "$dst" ]]; then
        log "  ${fname}: already exists at destination, skipping (no overwrite)."
        continue
    fi

    cp "$src" "$dst"
    log "  ${fname}: copied ${src} → ${dst}"
done

# ---------------------------------------------------------------------------
# STEP 4 — Remove old @reboot cron entry
# ---------------------------------------------------------------------------
step "STEP 5: Removing old @reboot cron entry"

EXISTING_CRONTAB=$(crontab -l 2>/dev/null || true)

if echo "$EXISTING_CRONTAB" | grep -qF "$OLD_CRON_PATTERN"; then
    UPDATED_CRONTAB=$(echo "$EXISTING_CRONTAB" | grep -vF "$OLD_CRON_PATTERN")
    echo "$UPDATED_CRONTAB" | crontab -
    log "Removed old cron entry containing '${OLD_CRON_PATTERN}'."
else
    log "Old cron entry not found. Nothing to remove."
fi

# ---------------------------------------------------------------------------
# STEP 5 — Install new @reboot cron entry
# ---------------------------------------------------------------------------
step "STEP 6: Installing new @reboot cron entry"

EXISTING_CRONTAB=$(crontab -l 2>/dev/null || true)

if echo "$EXISTING_CRONTAB" | grep -qF "$APP_SCRIPT"; then
    log "New @reboot cron entry already present. No changes made."
    log "  Entry: $(echo "$EXISTING_CRONTAB" | grep -F "$APP_SCRIPT")"
else
    (
        echo "$EXISTING_CRONTAB"
        echo "$NEW_CRON_LINE"
    ) | crontab -
    log "Installed new @reboot cron entry:"
    log "  ${NEW_CRON_LINE}"
fi

# ---------------------------------------------------------------------------
# STEP 6 — Install nightly update cron via install-cron.sh
# ---------------------------------------------------------------------------
step "STEP 7: Installing nightly update cron"

INSTALL_CRON="${REPO_DIR}/scripts/install-cron.sh"

if [[ ! -f "$INSTALL_CRON" ]]; then
    log "WARNING: ${INSTALL_CRON} not found. Skipping nightly update cron install."
    log "         Re-run this script after the repo is fully cloned, or run"
    log "         install-cron.sh manually."
else
    chmod +x "$INSTALL_CRON"
    # install-cron.sh prints its own status messages; prefix them with a tab
    # so they are visually nested under this step.
    "$INSTALL_CRON" 2>&1 | while IFS= read -r line; do
        log "  [install-cron] ${line}"
    done
fi

# ---------------------------------------------------------------------------
# STEP 7 — Stop old app instance and launch from new location
# ---------------------------------------------------------------------------
step "STEP 8: Restarting application from new location"

if pkill -f "its-a-plane.py" 2>/dev/null; then
    log "Stopped running its-a-plane.py process."
    # Brief pause to let the process fully exit before re-launching.
    sleep 2
else
    log "No running its-a-plane.py process found (will still launch fresh)."
fi

if [[ ! -f "$APP_SCRIPT" ]]; then
    log "WARNING: ${APP_SCRIPT} does not exist. Cannot launch application."
    log "         Verify the repository contents and re-run this script."
else
    nohup /usr/bin/python3 "$APP_SCRIPT" >> "$APP_LOG" 2>&1 &
    NEW_PID=$!
    log "Launched its-a-plane.py from new location with PID ${NEW_PID}."
    log "Application output: ${APP_LOG}"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
log ""
log "====================================================================="
log " Setup complete. Summary of actions taken:"
log "====================================================================="
log ""
log "  Repository   : ${REPO_DIR}"
log "  App script   : ${APP_SCRIPT}"
log "  App log      : ${APP_LOG}"
log "  Setup log    : ${SETUP_LOG}"
log ""
log "  Old location : ${OLD_DIR}"
log "  (The old directory has NOT been removed. Once you have verified the"
log "   new setup is working correctly you may delete it manually.)"
log ""
log "  Verify the app is running:"
log "    pgrep -fa its-a-plane.py"
log ""
log "  Tail the application log:"
log "    tail -f ${APP_LOG}"
log ""
log "  Check the installed cron jobs:"
log "    crontab -l"
log ""
log "====================================================================="
