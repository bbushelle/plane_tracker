#!/usr/bin/env bash
# install-cron.sh — Install (or verify) the nightly auto-update cron job.
#
# Run this once on the Raspberry Pi after cloning the repo. Safe to re-run;
# it will not add a duplicate entry if the job already exists.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — change CRON_SCHEDULE here to adjust the update frequency.
# Format: minute hour day-of-month month day-of-week
# Default: 3:00 AM every night.
# ---------------------------------------------------------------------------
CRON_SCHEDULE="0 3 * * *"

UPDATE_SCRIPT="/home/tyler/plane-tracker/scripts/update.sh"

# Full cron line that will be written to the user's crontab.
CRON_LINE="${CRON_SCHEDULE} ${UPDATE_SCRIPT}"

# ---------------------------------------------------------------------------
# Ensure the update script exists and is executable before installing the job.
# ---------------------------------------------------------------------------
if [[ ! -f "$UPDATE_SCRIPT" ]]; then
    echo "ERROR: $UPDATE_SCRIPT not found."
    echo "       Make sure the repository is fully cloned before running this script."
    exit 1
fi

if [[ ! -x "$UPDATE_SCRIPT" ]]; then
    echo "Making $UPDATE_SCRIPT executable..."
    chmod +x "$UPDATE_SCRIPT"
fi

# ---------------------------------------------------------------------------
# Check whether the cron entry already exists.
# ---------------------------------------------------------------------------
EXISTING_CRONTAB=$(crontab -l 2>/dev/null || true)

if echo "$EXISTING_CRONTAB" | grep -qF "$UPDATE_SCRIPT"; then
    echo "Cron job already installed. No changes made."
    echo ""
    echo "Current entry:"
    echo "$EXISTING_CRONTAB" | grep -F "$UPDATE_SCRIPT"
    exit 0
fi

# ---------------------------------------------------------------------------
# Append the new entry to the current crontab (preserving existing jobs).
# ---------------------------------------------------------------------------
(
    echo "$EXISTING_CRONTAB"
    echo "$CRON_LINE"
) | crontab -

echo "Cron job installed successfully."
echo ""
echo "Schedule : $CRON_SCHEDULE"
echo "Command  : $UPDATE_SCRIPT"
echo ""
echo "To change the schedule, edit CRON_SCHEDULE at the top of this script"
echo "and re-run it, or edit the crontab directly with: crontab -e"
echo ""
echo "To verify the installed job: crontab -l"
