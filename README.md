# 🔥 QRIS Mutation Scraper - Auto Checker

Aplikasi Python untuk **auto checking mutasi QRIS** dari QRIS BRI secara otomatis. Scraper ini menggunakan Playwright untuk automasi browser dan mengirim data mutasi ke webhook Anda.

## 🎯 Fitur Utama

- 🤖 **Auto Check Mutasi QRIS** - Monitoring mutasi 24/7
- ⏰ **Interval Configurable** - Atur interval cek lewat `CRON_INTERVAL_MINUTES`
- 🔗 **Webhook Integration** - Kirim data mutasi ke endpoint Anda
- 🔐 **Credential Management** - Login otomatis dengan session persistence
- 🧠 **Smart Deduplication** - Hindari duplikasi pengiriman data
- 📊 **Memory Optimized** - Satu run sekali jalan, tidak ada proses nganggur
- 🚀 **Production Ready** - System cron untuk stability
- 📱 **AAPanel Compatible** - Easy deployment di shared hosting

## ⚠️ Prasyarat Akun BRI Merchant (WAJIB DIBACA)

> **Akun BRI Merchant yang dipakai bot ini HARUS hanya memiliki 1 QRIS / 1 outlet.**

Per pembaruan terbaru di portal **BRI Merchant**, halaman transaksi tidak lagi memakai
URL khusus per outlet maupun segmen tanggal. Bot sekarang langsung membuka halaman
transaksi umum (`/transaksi`) — persis seperti yang diisi di `MUTASI_URL` — dan membaca
daftar transaksi hari ini milik outlet aktif.

Konsekuensinya:

- ✅ **1 akun = 1 QRIS/outlet** → bot berjalan normal, semua mutasi terbaca.
- ❌ **1 akun berisi banyak QRIS/outlet** → bot hanya membaca outlet yang sedang
  aktif/terpilih di portal, sehingga mutasi outlet lain **tidak akan terkirim** ke webhook.

Jika Anda punya beberapa QRIS/outlet, pisahkan tiap QRIS ke akun BRI Merchant
tersendiri, lalu jalankan 1 instance bot (folder + `.env` terpisah) untuk masing-masing akun.


## 🛠️ Instalasi di VPS Ubuntu

### **1. Persiapan Awal**

Update sistem dan install dependensi OS:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install git python3 python3-pip python3-venv -y
```

### **2. Clone Repositori**

```bash
git clone https://github.com/cahrur/cekmutasi-qris-bri.git
cd cekmutasi-qris-bri
```

### **3. Buat dan Aktifkan Virtual Environment**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

> Pastikan selalu jalankan `source .venv/bin/activate` setiap kali akan menjalankan script ini.

### **4. Install Dependensi & Browser Playwright**

```bash
pip install -r requirements.txt
playwright install chromium
playwright install-deps
```

> `playwright install-deps` penting di VPS untuk menginstal dependensi OS yang dibutuhkan browser.

### **5. Setup Konfigurasi**

```bash
cp env.example .env
nano .env
```

Isikan kredensial Anda:

| Variable | Keterangan |
|---|---|
| `LOGIN_PHONE` | Nomor HP akun BRI Merchant |
| `PASSWORD` | Password akun |
| `MUTASI_URL` | Biarkan default `https://brimerchant.bri.co.id/transaksi` |
| `BROWSER_CHANNEL` | Biarkan `chromium` (wajib, lihat *Troubleshooting*) |
| `WEBHOOK_URL` | URL endpoint untuk menerima data mutasi |
| `CRON_INTERVAL_MINUTES` | Interval pengecekan (contoh: `10`) |
| `QUIET_HOURS_START` / `QUIET_HOURS_END` | Jam jeda, bot berhenti scraping (contoh: `23:00` dan `02:00`). Kosongkan untuk nonaktif |

> 📌 **Tidak perlu lagi menyalin URL outlet Anda ke `MUTASI_URL`.**
> Cukup isi `https://brimerchant.bri.co.id/transaksi`. Bot membuka URL ini **apa adanya**
> tanpa menambahkan rentang tanggal, karena halaman transaksi BRI Merchant sudah otomatis
> menampilkan transaksi hari ini. Pastikan akun hanya berisi 1 QRIS/outlet
> (lihat bagian *Prasyarat Akun BRI Merchant*).

Tekan `Ctrl + X`, lalu `Y` dan `Enter` untuk menyimpan.

### **6. Uji Coba**

```bash
python -m app.main_cron once
```

### **7. Jalankan di Background (Production)**

```bash
chmod +x update_cron_interval.sh run_cron_job.sh
./update_cron_interval.sh
```

Monitor log:

```bash
tail -f logs/cron.log
```

---

### **AAPanel / CyberPanel**

Jika VPS menggunakan AAPanel atau CyberPanel, tersedia bash script installer khusus:

```bash
cd /www/wwwroot/domainanda.com
git clone https://github.com/cahrur/cekmutasi-qris-bri.git .
chmod +x install_aapanel.sh
./install_aapanel.sh
```

Lalu edit konfigurasi `.env` seperti langkah nomor 5 di atas.

## ⚙️ Konfigurasi

Edit file `.env`:

```env
# Kredensial Login (WAJIB DIISI)
LOGIN_PHONE=your_phone
PASSWORD=your_password

# Halaman transaksi BRI Merchant (biarkan default)
BASE_URL=https://brimerchant.bri.co.id
LOGIN_URL=https://brimerchant.bri.co.id/auth/login
MUTASI_URL=https://brimerchant.bri.co.id/transaksi

# Webhook URL (GANTI DENGAN URL ANDA)
WEBHOOK_URL=http://your-domain.com/webhook/callback

# Interval Auto Check (dalam menit)
CRON_INTERVAL_MINUTES=10  # Check setiap 10 menit

# Jam jeda (opsional) - bot berhenti scraping di rentang ini
QUIET_HOURS_START=23:00
QUIET_HOURS_END=02:00

# Browser Settings
HEADLESS=true
BROWSER_CHANNEL=chromium
TIMEZONE=Asia/Jakarta
```

### ⏸️ Jam Jeda (berhenti otomatis di jam tertentu)

Kalau tidak perlu memantau 24 jam penuh, atur jam jeda lewat `.env` — tidak perlu
mengubah kode maupun jadwal cron:

```env
QUIET_HOURS_START=23:00
QUIET_HOURS_END=02:00
```

Artinya bot **berhenti scraping jam 23:00 dan jalan lagi jam 02:00**. Cron tetap
berdetak seperti biasa, tetapi setiap tick di dalam rentang itu langsung berhenti
**sebelum browser dibuka**, jadi tidak ada pemakaian RAM maupun kuota data. Di log:

```
INFO  qris_cron | Jam jeda aktif, scraping dilewati | sekarang=23:04 jeda=23:00-02:00 (Asia/Jakarta)
INFO  qris_cron | === QRIS Scraper Job Skipped ===
```

Catatan penting:

- Format **24 jam `HH:MM`**. Rentang boleh melewati tengah malam (`23:00`–`02:00`).
- Jam dihitung memakai **`TIMEZONE`** di `.env` (default `Asia/Jakarta`), **bukan** jam
  server. Jadi tetap benar walaupun jam VPS diset UTC atau zona lain.
- Batas awal termasuk, batas akhir tidak: jeda `23:00`–`02:00` berarti `23:00` sudah
  berhenti dan `02:00` sudah jalan lagi.
- **Kosongkan salah satu atau keduanya** untuk menonaktifkan fitur ini.

#### ⚠️ Jangan sampai jeda melewati tengah malam

Halaman transaksi BRI Merchant **hanya menampilkan transaksi hari ini** — tidak ada
daftar hari kemarin, dan di-scroll pun tidak memuat lebih banyak. Karena itu:

| Jeda | Akibat |
|---|---|
| `00:00`–`02:00` | ✅ **Aman.** Transaksi jam 00:00–02:00 tetap terkirim saat bot jalan jam 02:00, karena masih tanggal yang sama |
| `23:00`–`02:00` | ⚠️ Transaksi jam **23:00–23:59 tidak akan pernah terkirim**. Saat bot jalan lagi jam 02:00, tanggal sudah berganti dan transaksi kemarin tidak lagi tampil di halaman |

Jadi kalau ingin bot istirahat malam **tanpa kehilangan transaksi**, mulai jedanya
tepat di tengah malam (`00:00`), bukan sebelum tengah malam.

Cek apakah sedang dalam jam jeda:

```bash
./status.sh
```

## 🚀 Penggunaan

### **Cek Sistem Sudah Jalan atau Belum**

```bash
./status.sh
```

Menampilkan dalam satu layar: cron sudah terpasang atau belum, konfigurasi `.env`
yang penting, kapan run terakhir dan hasilnya (sukses/gagal), jumlah mutasi yang
sudah terkirim, serta status sesi login.

### **Monitoring Realtime**

```bash
tail -f logs/cron.log
```

File `logs/cron.log` diisi oleh `run_cron_job.sh` — baik saat dijalankan cron
maupun manual. Kalau file ini belum ada, berarti bot memang belum pernah jalan.

Tanda sistem sehat pada log:

```
INFO  BrowserManager | Browser started successfully | headless=True channel=chromium ...
INFO  AuthManager    | Login successful
INFO  MutasiScraper  | Parsing revamped transaction cards | cards=3
INFO  WebhookClient  | Batch posting completed | total=3 successful=3 failed=0
INFO  qris_cron      | === QRIS Scraper Job Completed ===
```

> `Found 0 new mutations out of N total` **bukan error**. Artinya semua transaksi
> yang terbaca sudah pernah dikirim ke webhook dan tidak dikirim ulang (deduplikasi).

Hanya melihat aktivitas terbaru:

```bash
tail -n 50 logs/cron.log
grep -E "Job Completed|failed" logs/cron.log | tail -20
```

### **Production (System Cron)**
```bash
# Lihat jadwal cron yang terpasang
crontab -l

# Jalankan manual sekali (tetap tercatat ke logs/cron.log)
./run_cron_job.sh
```

### **Development**
```bash
# Single run test
python -m app.main_cron once

# Test kirim webhook
python test_webhook_simple.py

# Diagnosa browser vs WAF BRI Merchant
python diagnose_browser.py
```

## 📊 Format Data Webhook

Setiap mutasi dikirim sebagai **satu POST terpisah** dengan
`Content-Type: application/x-www-form-urlencoded` (bukan JSON):

```
target=mutation&bank=QRIS&account=-&date=2026-08-29&time=17%3A21%3A39
&description=QRIS+-+DANA+No.+Ref+624130689335+Pencairan+Berhasil
&type=K&amount=85903&balance=
```

| Field | Isi |
|---|---|
| `target` | Selalu `mutation` |
| `bank` | Selalu `QRIS` |
| `account` | Selalu `-` |
| `date` | Tanggal transaksi, `YYYY-MM-DD` |
| `time` | Jam transaksi, `HH:MM:SS` |
| `description` | Channel + No. Ref + status pencairan |
| `type` | `K` (kredit / uang masuk) |
| `amount` | Nominal tanpa pemisah ribuan |
| `balance` | **Selalu kosong** — BRI Merchant tidak menampilkan saldo di daftar transaksi |

Contoh penerima sederhana untuk uji coba ada di `test_webhook_simple.py`.

## 🔄 Management Commands

```bash
# Update cron interval setelah edit .env
./update_cron_interval.sh

# Check system status (cron, config, run terakhir, mutasi terkirim)
./status.sh

# Manual single run
./run_cron_job.sh

# Monitor logs
tail -f logs/cron.log

# Check processes
ps aux | grep python | grep qris
```

## 📋 Requirements

- **Python 3.8+**
- **RAM**: cukup untuk 1 instance Chromium (~1 GB saat scraping)
- **Linux/Ubuntu** (tested on Ubuntu 22.04)
- **Root access** (untuk AAPanel installation)

## 🔧 Troubleshooting

### **Login Gagal / `Failed to find or fill login identifier field`**

Penyebab paling umum **bukan** kredensial, melainkan browser yang dipakai. BRI Merchant
berada di belakang WAF **Imperva/Incapsula** yang memblokir *headless shell* bawaan
Playwright: semua aset `/_nuxt/*.js` dijawab `403`, aplikasi Nuxt-nya tidak pernah
render, dan form login tidak pernah muncul sehingga bot melaporkan field tidak ditemukan.

Solusinya memakai build Chromium reguler:

```bash
# 1. Pastikan build Chromium reguler terpasang (bukan sekadar headless shell)
playwright install chromium

# 2. Pastikan .env memakai channel chromium
cat .env | grep BROWSER_CHANNEL
# Harus: BROWSER_CHANNEL=chromium
```

> ⚠️ **Jangan menambahkan header HTTP statis** (`Sec-Fetch-Dest`, `Sec-Fetch-Mode`,
> `Accept`, dst.) lewat `set_extra_http_headers()` di `app/scraper/browser.py`.
> Header itu ikut terpasang di **semua** request, sehingga file `_nuxt/*.js` terkirim
> sebagai `Sec-Fetch-Dest: document` dan langsung ditolak WAF — gejalanya sama persis
> dengan di atas. Sudah diverifikasi di VPS: tanpa header itu lolos, dengan header itu
> 22 aset ditolak.

Log yang benar akan menampilkan `channel=chromium`:

```
INFO  BrowserManager | Browser started successfully | headless=True channel=chromium ...
```

Kalau tetap gagal, baru periksa kredensial:

```bash
cat .env | grep LOGIN_PHONE
cat .env | grep PASSWORD
```

### **Mutasi Tidak Terbaca / Hanya Sebagian**

Penyebab paling umum: akun BRI Merchant berisi **lebih dari 1 QRIS/outlet**, sehingga
bot hanya membaca outlet yang sedang aktif.

```bash
# Pastikan MUTASI_URL memakai halaman transaksi umum
cat .env | grep MUTASI_URL
# Harus: MUTASI_URL=https://brimerchant.bri.co.id/transaksi
```

Login manual ke https://brimerchant.bri.co.id dan pastikan hanya ada 1 QRIS/outlet
pada akun tersebut. Jika lebih dari satu, pisahkan ke akun BRI Merchant berbeda dan
jalankan instance bot terpisah untuk tiap akun.

### **Webhook Tidak Terkirim**
```bash
# Test webhook
python test_webhook_simple.py

# Check webhook URL (payload berupa form data, bukan JSON)
curl -X POST $WEBHOOK_URL -d "target=mutation&bank=QRIS&amount=1000"
```

### **Cron Tidak Jalan**
```bash
# Check cron service
service cron status

# Check cron logs
grep CRON /var/log/syslog

# Re-setup cron
./update_cron_interval.sh
```

### **Memory Issues**
```bash
# Check memory usage
free -h

# Kill stuck processes
pkill -f "python.*qris"

# Restart clean
./run_cron_job.sh

## Rotasi log

`run_cron_job.sh` merotasi sendiri `logs/cron.log` saat ukurannya melewati 10 MB
(dipindah ke `logs/cron.log.1`), jadi tidak perlu cron tambahan.

> Perintah lama `find logs/ -type f -mtime +30 -delete` **tidak berguna** untuk file
> ini: `cron.log` ditulis setiap run sehingga `mtime`-nya selalu baru dan tidak pernah
> memenuhi syarat `-mtime +30`.
```

### **Aktifkan Debug**
```bash
# Edit file .env
DEBUG_SCREENSHOTS=true
```

## 🎯 Production Tips

- ✅ **Monitor status**: `./status.sh`, realtime: `tail -f logs/cron.log`
- ✅ **Backup konfigurasi** `.env` secara berkala
- ✅ **Test webhook** sebelum production

### Konsumsi resource per interval

Diukur pada satu siklus scraping (memakai sesi tersimpan, tanpa login ulang):
**110 request, ~2 MB, ~5 detik**. Satu instance Chromium memuncak di **0,5–0,9 GB RAM**.

| Interval | Run/bulan | Bandwidth/bulan |
|---|---|---|
| 1 menit | 43.200 | ~86 GB |
| 2 menit | 21.600 | ~43 GB |
| 5 menit | 8.640 | ~17 GB |
| 10 menit | 4.320 | ~9 GB |
| 15 menit | 2.880 | ~6 GB |

Yang perlu dijaga bukan bandwidth, melainkan **RAM**: setiap run menjalankan satu
Chromium penuh, jadi dua run yang tumpang tindih melipatgandakan pemakaian memori.

### Proteksi run menumpuk

`run_cron_job.sh` menjamin **hanya ada satu scraping pada satu waktu**, berapa pun
interval cron-nya:

1. **`flock -n`** — saat cron berdetak sementara run sebelumnya masih bekerja, tick itu
   **dilewati**, bukan diantrekan. Run yang sedang jalan dibiarkan selesai tanpa
   diganggu, dan di log tercatat:
   ```
   [2026-08-29T23:15:00] SKIP: run sebelumnya masih berjalan, tick ini dilewati
   ```
2. **`timeout 300`** — jika sebuah run menggantung (jaringan atau WAF bermasalah), run
   itu dihentikan paksa setelah 5 menit dan sisa proses Chromium dibersihkan. Tanpa ini,
   satu run yang macet akan menahan lock selamanya dan bot berhenti diam-diam.

Karena itu interval sekecil **1 menit pun aman**: run normal hanya ~20 detik, dan kalau
sedang lambat, tick berikutnya otomatis dilewati sampai run yang berjalan selesai.

## 📞 Support

Jika mengalami masalah:
1. Check logs: `tail -50 logs/cron.log`
2. Test manual: `./run_cron_job.sh`
3. Verify config: `./status.sh`
4. Check system: `free -h && df -h`

---

**🚀 QRIS Auto Checker siap monitoring mutasi 24/7!**
