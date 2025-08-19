#!/bin/bash
# QRIS Scraper single job for system cron
# Optimized for memory efficiency

cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || exit 1

export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true

# Run single scraper job
python -m app.main_cron once
