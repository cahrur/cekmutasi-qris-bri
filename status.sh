#!/bin/bash
# Cek status QRIS Auto Checker: cron aktif? kapan run terakhir? berhasil atau gagal?

cd "$(dirname "$0")"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
bad()  { echo -e "${RED}❌ $1${NC}"; }

echo "=============================================="
echo " STATUS QRIS AUTO CHECKER"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="

# 1. Cron terpasang?
echo ""
echo "--- 1. Penjadwalan (cron) ---"
CRON_LINE=$(crontab -l 2>/dev/null | grep "run_cron_job.sh")
if [[ -n "$CRON_LINE" ]]; then
    ok "Cron aktif: $CRON_LINE"
else
    bad "Cron BELUM terpasang. Jalankan: ./update_cron_interval.sh"
fi

if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet cron 2>/dev/null; then
    ok "Service cron berjalan"
elif command -v service >/dev/null 2>&1; then
    service cron status >/dev/null 2>&1 && ok "Service cron berjalan" || warn "Service cron tidak terdeteksi aktif"
fi

# 2. Konfigurasi penting
echo ""
echo "--- 2. Konfigurasi (.env) ---"
if [[ -f .env ]]; then
    for KEY in LOGIN_PHONE WEBHOOK_URL MUTASI_URL BROWSER_CHANNEL CRON_INTERVAL_MINUTES QUIET_HOURS_START QUIET_HOURS_END; do
        VALUE=$(grep "^$KEY=" .env | head -1 | cut -d'=' -f2-)
        if [[ -n "$VALUE" ]]; then
            [[ "$KEY" == "LOGIN_PHONE" ]] && VALUE="${VALUE:0:4}****"
            ok "$KEY = $VALUE"
        else
            case "$KEY" in
                BROWSER_CHANNEL) bad "$KEY kosong - WAF BRI akan memblokir. Set: BROWSER_CHANNEL=chromium" ;;
                QUIET_HOURS_*)   echo "   $KEY = (kosong, jam jeda nonaktif)" ;;
                *)               warn "$KEY belum diisi" ;;
            esac
        fi
    done
else
    bad ".env tidak ditemukan. Jalankan: cp env.example .env"
fi

# 2b. Sedang jam jeda?
QH_START=$(grep "^QUIET_HOURS_START=" .env 2>/dev/null | cut -d'=' -f2- | tr -d ' ')
QH_END=$(grep "^QUIET_HOURS_END=" .env 2>/dev/null | cut -d'=' -f2- | tr -d ' ')
if [[ -n "$QH_START" && -n "$QH_END" ]]; then
    TZ_NAME=$(grep "^TIMEZONE=" .env 2>/dev/null | cut -d'=' -f2- | tr -d ' ')
    TZ_NAME=${TZ_NAME:-Asia/Jakarta}
    NOW_HM=$(TZ="$TZ_NAME" date +%H:%M)
    # Bandingkan sebagai menit sejak tengah malam agar rentang lintas tengah malam benar
    to_min() { echo $((10#${1%%:*} * 60 + 10#${1##*:})); }
    N=$(to_min "$NOW_HM"); S=$(to_min "$QH_START"); E=$(to_min "$QH_END")
    IN_QUIET=false
    if [[ $S -lt $E ]]; then
        [[ $N -ge $S && $N -lt $E ]] && IN_QUIET=true
    elif [[ $S -gt $E ]]; then
        { [[ $N -ge $S ]] || [[ $N -lt $E ]]; } && IN_QUIET=true
    fi
    if [[ "$IN_QUIET" == true ]]; then
        warn "Sekarang $NOW_HM $TZ_NAME - SEDANG JAM JEDA, scraping dilewati sampai $QH_END"
    else
        ok "Sekarang $NOW_HM $TZ_NAME - di luar jam jeda, bot aktif"
    fi
fi

# 3. Run terakhir
echo ""
echo "--- 3. Run terakhir ---"
LOG="logs/cron.log"
if [[ -f "$LOG" ]]; then
    LAST_START=$(grep "Job Started" "$LOG" | tail -1)
    if [[ -n "$LAST_START" ]]; then
        ok "Terakhir jalan: $(echo "$LAST_START" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+')"
    else
        warn "Belum ada run tercatat di $LOG"
    fi

    LAST_RESULT=$(grep -E "Job Completed|Scraper job failed" "$LOG" | tail -1)
    if [[ "$LAST_RESULT" == *"Completed"* ]]; then
        ok "Hasil terakhir: SUKSES"
    elif [[ -n "$LAST_RESULT" ]]; then
        bad "Hasil terakhir: GAGAL -> $LAST_RESULT"
    fi

    SKIPPED_LOCK=$(grep -c "SKIP: run sebelumnya" "$LOG" 2>/dev/null || echo 0)
    SKIPPED_QUIET=$(grep -c "Jam jeda aktif" "$LOG" 2>/dev/null || echo 0)
    echo "   Tick dilewati: $SKIPPED_LOCK (run masih jalan) | $SKIPPED_QUIET (jam jeda)"

    SENT=$(grep -c "Mutation posted successfully" "$LOG" 2>/dev/null || echo 0)
    FAILED=$(grep -c "Request error posting mutation" "$LOG" 2>/dev/null || echo 0)
    echo "   Total mutasi terkirim (sepanjang log): $SENT | gagal kirim: $FAILED"

    SIZE=$(du -h "$LOG" 2>/dev/null | cut -f1)
    echo "   Ukuran log: $SIZE"
else
    warn "$LOG belum ada. Jalankan ./run_cron_job.sh sekali, atau tunggu cron berjalan."
fi

# 4. Cache dedup
echo ""
echo "--- 4. Cache deduplikasi ---"
CACHE=$(grep "^CACHE_DB=" .env 2>/dev/null | cut -d'=' -f2- | tr -d ' ')
CACHE=${CACHE:-./data/sent_ids.sqlite}
if [[ -f "$CACHE" ]]; then
    ok "Cache ada: $CACHE ($(du -h "$CACHE" | cut -f1))"
    if command -v sqlite3 >/dev/null 2>&1; then
        COUNT=$(sqlite3 "$CACHE" "SELECT COUNT(*) FROM sent_ids;" 2>/dev/null)
        [[ -n "$COUNT" ]] && echo "   Transaksi sudah tercatat terkirim: $COUNT"
    fi
else
    warn "Cache belum ada (belum pernah ada mutasi terkirim)"
fi

# 5. Sesi login
echo ""
echo "--- 5. Sesi login ---"
SESSION=$(grep "^SESSION_FILE=" .env 2>/dev/null | cut -d'=' -f2- | tr -d ' ')
SESSION=${SESSION:-./data/session.json}
if [[ -f "$SESSION" ]]; then
    ok "Sesi tersimpan ($(date -r "$SESSION" '+%Y-%m-%d %H:%M:%S'))"
else
    warn "Belum ada sesi tersimpan - bot akan login ulang pada run berikutnya"
fi

echo ""
echo "=============================================="
echo " Monitoring realtime:  tail -f logs/cron.log"
echo " Jalankan manual    :  ./run_cron_job.sh"
echo " Diagnosa browser   :  python diagnose_browser.py"
echo "=============================================="
