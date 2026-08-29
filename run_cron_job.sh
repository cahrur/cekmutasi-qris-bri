#!/bin/bash
# QRIS Scraper single job for system cron
# Satu run pada satu waktu, tidak pernah menumpuk.

cd "$(dirname "$0")"

# Batas waktu satu run. Run normal ~20 detik; ini hanya jaring pengaman agar run
# yang menggantung tidak menahan lock selamanya.
RUN_TIMEOUT_SECONDS=300

mkdir -p logs
LOG_FILE="logs/cron.log"

stamp() { date '+%Y-%m-%dT%H:%M:%S'; }

# Rotate at ~10 MB. `find -mtime +30 -delete` never removes this file because its
# mtime is refreshed on every run.
if [[ -f "$LOG_FILE" ]] && [[ $(stat -c %s "$LOG_FILE" 2>/dev/null || echo 0) -gt 10485760 ]]; then
    mv -f "$LOG_FILE" "$LOG_FILE.1"
fi

# Log to logs/cron.log as well as stdout, so cron runs and manual runs land in the
# same file. Done before the lock is opened so `tee` does not inherit fd 200 and
# hold the lock after this script exits.
exec > >(tee -a "$LOG_FILE") 2>&1

# One run at a time. Each run drives a full Chromium (~0.5-0.9 GB); a second one
# starting while the first is still working would double that. -n = do not queue:
# skip this tick entirely and let the running scrape finish undisturbed.
if command -v flock >/dev/null 2>&1; then
    exec 200>"logs/.cron.lock"
    if ! flock -n 200; then
        echo "[$(stamp)] SKIP: run sebelumnya masih berjalan, tick ini dilewati"
        exit 0
    fi
else
    echo "[$(stamp)] WARNING: flock tidak tersedia, proteksi run ganda nonaktif (apt install util-linux)"
fi

if ! source .venv/bin/activate 2>/dev/null; then
    echo "[$(stamp)] ERROR: .venv tidak ditemukan. Jalankan: python3 -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true

# Run single scraper job
timeout -k 10 "$RUN_TIMEOUT_SECONDS" python -m app.main_cron once
EXIT_CODE=$?

# 124 = SIGTERM oleh timeout, 137 = SIGKILL setelah -k
if [[ $EXIT_CODE -eq 124 || $EXIT_CODE -eq 137 ]]; then
    echo "[$(stamp)] ERROR: run melebihi ${RUN_TIMEOUT_SECONDS} detik dan dihentikan paksa"
    # Bersihkan Chromium yatim supaya tidak menahan RAM. Aman: lock di atas
    # menjamin tidak ada run lain milik bot ini yang sedang berjalan.
    if pkill -f "ms-playwright.*chrome" 2>/dev/null; then
        echo "[$(stamp)] Chromium sisa dibersihkan"
    fi
fi

exit $EXIT_CODE
