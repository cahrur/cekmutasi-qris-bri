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

## 🛠️ Quick Installation

### **AAPanel/CyberPanel (Recommended)**
```bash
# 1. SSH ke server sebagai root
ssh root@your-server-ip

# 2. Masuk ke direktori website
cd /www/wwwroot/your-domain.com

# 3. Upload files atau git clone
git clone https://github.com/cahrur/cekmutasi-qris-bri.git .

# 4. Auto install (satu command!)
chmod +x install_aapanel.sh
./install_aapanel.sh

# 5. Edit konfigurasi
nano .env
```

### **Manual Installation**
```bash
# 1. Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 3. Setup configuration
cp .env.example .env
nano .env

# 4. Test installation
./test_scraper.sh
```

## ⚙️ Konfigurasi

Edit file `.env`:

```env
# Kredensial Login (WAJIB DIISI)
LOGIN_PHONE=your_phone
PASSWORD=your_password

# Webhook URL (GANTI DENGAN URL ANDA)
WEBHOOK_URL=http://your-domain.com/webhook/callback

# Interval Auto Check (dalam menit)
CRON_INTERVAL_MINUTES=10  # Check setiap 10 menit

# Browser Settings
HEADLESS=true
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

### **Login Gagal**
```bash
# Check kredensial di .env
cat .env | grep LOGIN_PHONE
cat .env | grep PASSWORD

# Test manual login
./test_scraper.sh
```

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
