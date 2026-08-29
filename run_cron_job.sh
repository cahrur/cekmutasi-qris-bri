#!/bin/bash
# QRIS Scraper single job for system cron
# Optimized for memory efficiency

cd "$(dirname "$0")"

# Log to logs/cron.log as well as stdout, so both cron runs and manual runs land
# in the same file and `tail -f logs/cron.log` always works.
mkdir -p logs
exec > >(tee -a "logs/cron.log") 2>&1

if ! source .venv/bin/activate 2>/dev/null; then
    echo "[$(date '+%Y-%m-%dT%H:%M:%S')] ERROR: .venv tidak ditemukan. Jalankan: python3 -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true

# Run single scraper job
python -m app.main_cron once
