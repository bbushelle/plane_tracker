# Auto-Update System

The plane-tracker includes a lightweight auto-update mechanism. A cron job
runs nightly, checks for new commits on `origin/main`, and — if changes are
found — pulls them and restarts the application automatically.

---

## How the update script works

`scripts/update.sh` performs the following steps in order:

1. **Fetch** — runs `git fetch origin main` to download the latest remote
   state without touching the working tree.
2. **Compare** — compares the local `HEAD` SHA to `origin/main`. If they are
   identical the script logs "Already up to date" and exits cleanly (exit 0).
3. **Log incoming commits** — if there is a difference, every new commit
   (`git log --oneline`) is written to the update log so the history is
   auditable.
4. **Pull** — runs `git pull origin main`. If the pull fails (e.g. a merge
   conflict or a dirty working tree) an error is logged and the script exits
   with a non-zero status; the application is **not** restarted.
5. **Restart the application** — kills any running `its-a-plane.py` process
   with `pkill -f`, then re-launches it in the background via `nohup` so it
   picks up the updated code. Application output continues to flow into
   `logs/app.log`.

> **Note:** The web UI's "Reboot Pi" button performs a full `sudo reboot`, which
> is the recommended way to apply new code after a manual pull. The auto-update
> script uses `nohup` restart (not full reboot) since it runs unattended at 3 AM.

The script is **idempotent** — running it multiple times with no new commits
is harmless.

---

## Log files

| File | Contents |
|------|----------|
| `/home/tyler/plane-tracker/logs/update.log` | Timestamped record of every update run, including which commits were pulled and whether the restart succeeded. |
| `/home/tyler/plane-tracker/logs/app.log` | stdout/stderr of the `its-a-plane.py` process itself. |

Both log directories are created automatically by `update.sh` if they do not
already exist.

---

## Initial setup (run once on the Pi)

```bash
# 1. Clone the repo (if not already done)
git clone https://github.com/<your-org>/plane-tracker.git /home/tyler/plane-tracker

# 2. Make the scripts executable
chmod +x /home/tyler/plane-tracker/scripts/update.sh
chmod +x /home/tyler/plane-tracker/scripts/install-cron.sh

# 3. Install the nightly cron job
/home/tyler/plane-tracker/scripts/install-cron.sh
```

---

## Changing the cron schedule

Open `scripts/install-cron.sh` and edit the `CRON_SCHEDULE` variable near
the top of the file:

```bash
CRON_SCHEDULE="0 3 * * *"   # default: 3:00 AM every night
```

Common examples:

| Value | Meaning |
|-------|---------|
| `0 3 * * *` | 3:00 AM every night (default) |
| `0 */6 * * *` | Every 6 hours |
| `30 2 * * 0` | 2:30 AM every Sunday |

After editing, re-run the installer — it will replace the old entry:

```bash
# Remove the old entry first, then reinstall
crontab -l | grep -v "plane-tracker/scripts/update.sh" | crontab -
/home/tyler/plane-tracker/scripts/install-cron.sh
```

Alternatively, edit the crontab directly:

```bash
crontab -e
```

---

## Manually triggering an update

You can run the update script at any time without waiting for the cron job:

```bash
/home/tyler/plane-tracker/scripts/update.sh
```

Then tail the log to watch progress:

```bash
tail -f /home/tyler/plane-tracker/logs/update.log
```

---

## Disabling auto-updates

To remove the cron job entirely:

```bash
crontab -l | grep -v "plane-tracker/scripts/update.sh" | crontab -
```

Verify the entry is gone:

```bash
crontab -l
```

The application will continue running normally; it just will no longer be
updated or restarted automatically.
