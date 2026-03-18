# Pi Setup: Migrating to the Git-Managed Repo

This guide covers the one-time migration from the original `its-a-plane-python`
installation to the new git-managed `plane-tracker` repository.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| SSH access to `autism-pi` | `ssh tyler@autism-pi` (or use the IP address) |
| `git` installed on the Pi | `sudo apt-get install -y git` if missing |
| `python3` installed on the Pi | Should already be present on Raspberry Pi OS |
| The repo URL | Already set to `https://github.com/bbushelle/plane_tracker.git` in `scripts/setup-pi.sh` |

---

## One-time setup steps

### 1. Copy the script to the Pi

```bash
scp scripts/setup-pi.sh tyler@autism-pi:/home/tyler/setup-pi.sh
```

### 3. SSH into the Pi

```bash
ssh tyler@autism-pi
```

### 4. Run the setup script

```bash
bash /home/tyler/setup-pi.sh
```

The script will print timestamped progress to the terminal as it runs. Once
the repository has been cloned, output is also written to
`/home/tyler/plane-tracker/logs/setup.log`.

---

## What the script does

The script performs seven idempotent steps in order:

1. **Check prerequisites** — confirms `git` and `python3` are available and
   that `REPO_URL` has been filled in.

2. **Clone the repository** — clones to `/home/tyler/plane-tracker`. If the
   directory already exists and contains a valid git repo the clone is skipped.

3. **Migrate runtime data** — copies the following files from the old location
   if they exist, and only if the destination does not already have them
   (no overwrite):

   | Source | Destination |
   |--------|-------------|
   | `~/its-a-plane-python/close.txt` | `~/plane-tracker/its-a-plane-python/close.txt` |
   | `~/its-a-plane-python/farthest.txt` | `~/plane-tracker/its-a-plane-python/farthest.txt` |

4. **Remove the old `@reboot` cron entry** — deletes the cron line that
   pointed to `~/its-a-plane-python/its-a-plane.py`.

5. **Install the new `@reboot` cron entry** — adds:
   ```
   @reboot sleep 60 && /home/tyler/plane-tracker/its-a-plane-python/its-a-plane.py >> /home/tyler/plane-tracker/logs/app.log 2>&1
   ```
   If the entry already exists it is left unchanged.

6. **Install the nightly update cron** — calls
   `scripts/install-cron.sh`, which registers a 3 AM daily job that pulls
   the latest commits from `origin/main` and restarts the application if
   anything changed. See [auto-update.md](auto-update.md) for details.

7. **Restart the application** — kills any running `its-a-plane.py` instance
   and re-launches it from the new location using `nohup`, directing output
   to `/home/tyler/plane-tracker/logs/app.log`.

---

## Verifying the new setup

### Check that the application is running

```bash
pgrep -fa its-a-plane.py
```

You should see a line containing `/home/tyler/plane-tracker/its-a-plane-python/its-a-plane.py`.

### Tail the application log

```bash
tail -f /home/tyler/plane-tracker/logs/app.log
```

### Confirm the cron jobs are installed

```bash
crontab -l
```

Expected output should include both the `@reboot` line pointing to
`/home/tyler/plane-tracker/...` **and** the `0 3 * * *` nightly update line.
The old `its-a-plane-python` entry should be absent.

### Review the setup log

```bash
cat /home/tyler/plane-tracker/logs/setup.log
```

Each step is timestamped. Look for any `WARNING` or `ERROR` lines.

---

## Rolling back

The old directory (`~/its-a-plane-python/`) is left untouched by the setup
script. If you need to revert:

1. **Stop the new application instance:**
   ```bash
   pkill -f its-a-plane.py
   ```

2. **Remove the new cron entries:**
   ```bash
   crontab -l \
     | grep -v "plane-tracker/its-a-plane-python/its-a-plane.py" \
     | grep -v "plane-tracker/scripts/update.sh" \
     | crontab -
   ```

3. **Restore the old `@reboot` cron entry:**
   ```bash
   (crontab -l 2>/dev/null; echo "@reboot sleep 60 && ~/its-a-plane-python/its-a-plane.py >> ~/its-a-plane-python/workdammit.log 2>&1") | crontab -
   ```

4. **Relaunch from the old location:**
   ```bash
   nohup python3 ~/its-a-plane-python/its-a-plane.py >> ~/its-a-plane-python/workdammit.log 2>&1 &
   ```

5. Once you are confident the old setup is running again, you can remove the
   new directory:
   ```bash
   rm -rf /home/tyler/plane-tracker
   ```

---

## Cleaning up the old directory

Once you have verified the new setup is stable, you may delete the old
installation:

```bash
rm -rf /home/tyler/its-a-plane-python
```

There is no rush — the old directory is harmless until you are ready to
remove it.
