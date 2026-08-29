# 🔥 QRIS Mutation Scraper - Auto Checker

Aplikasi Python untuk **auto checking mutasi QRIS** dari QRIS BRI secara otomatis. Scraper ini menggunakan Playwright untuk automasi browser dan mengirim data mutasi ke webhook Anda.

## 🎯 Fitur Utama

- 🤖 **Auto Check Mutasi QRIS** - Monitoring mutasi 24/7
- ⏰ **Interval Configurable** - Atur interval cek sesuai kebutuhan (5-60 menit)
- 🔗 **Webhook Integration** - Kirim data mutasi ke endpoint Anda
- 🔐 **Credential Management** - Login otomatis dengan session persistence
- 🧠 **Smart Deduplication** - Hindari duplikasi pengiriman data
- 📊 **Memory Optimized** - Cocok untuk server dengan RAM 4GB
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

# Browser Settings
HEADLESS=true
BROWSER_CHANNEL=chromium
TIMEZONE=Asia/Jakarta
```

## 🚀 Penggunaan

### **Production (System Cron)**
```bash
# Cron sudah auto-setup setelah install
crontab -l  # Check cron status

# Monitor real-time
tail -f logs/cron.log

# Manual test
./run_cron_job.sh
```

### **Development**
```bash
# Single run test
python -m app.main_cron once

# Test webhook
./test_webhook.sh
```

## 📊 Format Data Webhook

Data mutasi dikirim dalam format JSON:
```json
{
  "target": "mutation",
  "bank": "QRIS", 
  "account": "-",
  "date": "2025-01-18",
  "time": "10:30:00",
  "description": "Transfer masuk dari BANK XYZ",
  "type": "K",
  "amount": "150000",
  "balance": "2500000"
}
```

## 🔄 Management Commands

```bash
# Update cron interval setelah edit .env
./update_cron_interval.sh

# Check system status
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
- **RAM 4GB+** (optimized untuk low memory)
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
./test_webhook.sh

# Check webhook URL
curl -X POST $WEBHOOK_URL -d "test=1"
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

## auto clear log yang lebih 30 hari
Tambahkan pada crontab
0 0 * * * find /opt/cekmutasi-qris-bri/logs/ -type f -mtime +30 -delete
```

### **Aktifkan Debug**
```bash
# Edit file .env
DEBUG_SCREENSHOTS=true
```

## 🎯 Production Tips

- ✅ **Set interval 10-15 menit** untuk balance antara update speed & resource usage
- ✅ **Monitor logs harian**: `tail -f logs/cron.log`
- ✅ **Setup log rotation** untuk mencegah disk penuh
- ✅ **Backup konfigurasi** `.env` secara berkala
- ✅ **Test webhook** sebelum production

## 📞 Support

Jika mengalami masalah:
1. Check logs: `tail -50 logs/cron.log`
2. Test manual: `./run_cron_job.sh`
3. Verify config: `./status.sh`
4. Check system: `free -h && df -h`

---

**🚀 QRIS Auto Checker siap monitoring mutasi 24/7!**
