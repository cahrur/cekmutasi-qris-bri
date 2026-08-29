#!/bin/bash
# QRIS Scraper single job for system cron
# Optimized for memory efficiency

cd "$(dirname "$0")"

mkdir -p logs
LOG_FILE="logs/cron.log"

# Rotate at ~10 MB. With a 2-minute interval this file grows ~50 MB/month, and
# the `find -mtime +30 -delete` cron in the README never removes it because its
# mtime is refreshed on every run.
if [[ -f "$LOG_FILE" ]] && [[ $(stat -c %s "$LOG_FILE" 2>/dev/null || echo 0) -gt 10485760 ]]; then
    mv -f "$LOG_FILE" "$LOG_FILE.1"
fi

# Log to logs/cron.log as well as stdout, so both cron runs and manual runs land
# in the same file and `tail -f logs/cron.log` always works.
exec > >(tee -a "$LOG_FILE") 2>&1

# One run at a time. A single Chromium peaks around 0.5-0.9 GB; if a run hangs
# (WAF stall, slow network) the next cron tick would start a second browser and
# a 2 GB VPS runs out of memory.
if command -v flock >/dev/null 2>&1; then
    exec 200>"logs/.cron.lock"
    if ! flock -n 200; then
        echo "[$(date '+%Y-%m-%dT%H:%M:%S')] SKIP: run sebelumnya masih berjalan"
        exit 0
    fi
fi

if ! source .venv/bin/activate 2>/dev/null; then
    echo "[$(date '+%Y-%m-%dT%H:%M:%S')] ERROR: .venv tidak ditemukan. Jalankan: python3 -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true

# Run single scraper job
python -m app.main_cron once
