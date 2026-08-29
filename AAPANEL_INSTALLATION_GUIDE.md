# 🚀 PANDUAN INSTALASI QRIS SCRAPER DI AAPANEL

## 📋 Prerequisites

### 1. Akses Server AAPanel
- Login ke server via SSH dengan akses **root**
- Python 3.8+ sudah terinstall
- RAM minimum 4GB (optimized untuk low memory)

### 2. Upload Project Files
Upload semua file project ke server AAPanel melalui File Manager atau git clone

## 🛠️ Cara Instalasi

### **Method 1: Auto Installation + System Cron (Recommended - Memory Optimized)**

```bash
# 1. SSH ke server AAPanel sebagai root
ssh root@your-server-ip

# 2. Masuk ke direktori website
cd /www/wwwroot/your-domain.com

# 3. Upload project files atau clone repository
# Option A: Upload via AAPanel File Manager
# Option B: git clone https://github.com/cahrur/cekmutasi-qris-bri.git .

# 4. Jalankan auto installer (otomatis baca .env untuk cron interval)
chmod +x install_aapanel.sh
./install_aapanel.sh

# 5. Edit konfigurasi WAJIB
nano .env
# Update: LOGIN_PHONE, PASSWORD, WEBHOOK_URL, CRON_INTERVAL_MINUTES

# 6. Test installation
./test_scraper.sh

# 7. Cron sudah auto-setup sesuai CRON_INTERVAL_MINUTES di .env
# Monitor logs: tail -f logs/cron.log
```

### **Method 2: Manual Installation**

```bash
# 1. Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browsers
export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
playwright install chromium

# 4. Setup configuration
cp .env.example .env
nano .env  # Edit dengan kredensial Anda

# 5. Setup system cron job
chmod +x run_cron_job.sh
# Add to crontab:
# */15 * * * * cd /www/wwwroot/your-domain.com && ./run_cron_job.sh

# 6. Test installation
./run_cron_job.sh
```

## ⚙️ Konfigurasi AAPanel

### 1. **Python Manager**
- Masuk ke AAPanel → Software Store → Python Manager
- Install Python 3.8+ jika belum ada
- Create Python project di direktori website

### 2. **Process Manager (Optional)**
- Masuk ke AAPanel → Process Manager
- Monitor running Python processes
- QRIS Scraper menggunakan internal cron Python (tidak perlu cron sistem)

### 3. **File Manager**
Struktur direktori harus seperti ini:
```
/www/wwwroot/your-domain.com/
├── app/
├── tests/
├── .venv/
├── .env
├── requirements.txt
├── install_aapanel.sh
├── run_cron_job.sh
├── update_cron_interval.sh
├── start_qris_scraper.sh
├── test_scraper.sh
├── test_webhook.sh
├── status.sh
└── test_webhook_simple.py
```

## 🔧 Konfigurasi Environment

Edit file `.env`:
```env
# Login credentials (WAJIB DIISI)
LOGIN_PHONE=your_phone
PASSWORD=your_password

# URLs (Sesuaikan)
BASE_URL=https://brimerchant.bri.co.id
LOGIN_URL=https://brimerchant.bri.co.id/auth/login
MUTASI_URL=https://brimerchant.bri.co.id/transaksi

# Webhook URL (GANTI DENGAN URL ANDA)
WEBHOOK_URL=http://your-domain.com/webhook/callback

# Browser settings
HEADLESS=true
TIMEZONE=Asia/Jakarta

# Cron settings (interval dalam menit: 5-60)
CRON_INTERVAL_MINUTES=10
```

### **⚙️ Update Cron Interval (Setelah Mengubah .env):**
```bash
# Jika mengubah CRON_INTERVAL_MINUTES di .env, jalankan:
./update_cron_interval.sh
```

## 🧪 Testing

### 1. **Test Manual**
```bash
cd /www/wwwroot/your-domain.com
source .venv/bin/activate
python test_webhook_simple.py
```

### 2. **Test Scraper**
```bash
./test_scraper.sh
```

### 3. **Test Webhook**
```bash
./test_webhook.sh
```

## 📊 Monitoring & Logs

### 1. **Check Status**
```bash
./status.sh
```

### 2. **View Logs**
```bash
# Cron logs
tail -f logs/cron.log

# Application logs
tail -f logs/app.log
```

### 3. **AAPanel File Manager**
- Masuk ke AAPanel → Files
- Navigate ke direktori project
- Check folder `logs/` untuk melihat log files

## 🔄 Management Commands

Auto installer membuat script management:

### **System Cron Commands (Production Ready)**
```bash
./run_cron_job.sh          # Manual single run (untuk cron)
./update_cron_interval.sh  # Update cron interval dari .env
./test_scraper.sh          # Test scraper sekali
./test_webhook.sh          # Test webhook connectivity
./status.sh                # Check system status
```

### **Monitoring Commands**
```bash
# View cron logs
tail -f logs/cron.log

# Check cron status
crontab -l

# Check running processes
ps aux | grep python | grep qris

# Monitor system resources
free -h && df -h
```

## 🚀 **Production Deployment dengan System Cron (Memory Optimized)**

### **1. Auto-Setup Complete!**
Auto installer sudah setup system cron otomatis sesuai `CRON_INTERVAL_MINUTES` di `.env`.

### **2. Cron Configuration**
Cron job otomatis dibuat saat installation:
```bash
# Example: Every 10 minutes (sesuai CRON_INTERVAL_MINUTES di .env)
*/10 * * * * cd /www/wwwroot/your-domain.com && ./run_cron_job.sh
```

### **3. Production Commands**
```bash
# Check cron status
crontab -l

# Manual test run
./run_cron_job.sh

# Update cron interval setelah edit .env
./update_cron_interval.sh

# Monitor logs
tail -f logs/cron.log

# Check process
ps aux | grep python | grep qris
```

### **4. Memory Benefits**
- ✅ **Low Memory Usage**: ~300-500MB (vs 800MB+ dengan PM2)
- ✅ **Efficient**: Process hanya running saat scraping
- ✅ **Auto-cleanup**: No lingering processes
- ✅ **Perfect for 4GB RAM servers**

### **5. Monitoring & Management**
```bash
# Real-time log monitoring
watch -n 5 "tail -10 logs/cron.log"

# System resource check
free -h && df -h

# Cron job verification
crontab -l | grep qris

# Emergency stop all QRIS processes
pkill -f "python.*qris"
```

## 🚨 Troubleshooting

### **Problem 1: Permission Denied**
```bash
# Fix permissions
chmod +x *.sh
chown -R www:www /www/wwwroot/your-domain.com
```

### **Problem 2: Python Module Not Found**
```bash
# Reinstall dependencies
source .venv/bin/activate
pip install -r requirements.txt
```

### **Problem 3: Playwright Issues**
```bash
# Set environment variable
export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
```

### **Problem 4: Cron Issues**
```bash
# Check cron service
service cron status

# Restart cron service
service cron restart

# Check cron logs
grep CRON /var/log/syslog

# Re-add cron job
./update_cron_interval.sh

# Manual test
./run_cron_job.sh
```

## 📱 AAPanel GUI Setup

### 1. **Website Management**
- Create new website/subdomain untuk project
- Set document root ke project directory

### 2. **SSL Certificate**
- Install SSL untuk webhook endpoint
- Pastikan webhook URL menggunakan HTTPS

### 3. **Database (Optional)**
- Create MySQL database untuk extended logging
- Update .env dengan database credentials

## 🔐 Security Best Practices

### 1. **File Permissions**
```bash
chmod 600 .env  # Protect configuration
chmod +x *.sh   # Make scripts executable
```

### 2. **Firewall Rules**
- Whitelist IP mesinotomatis: `172.104.187.51`
- Allow webhook traffic on required ports

### 3. **Monitoring**
- Setup log rotation
- Monitor disk space usage
- Check cron job execution

## ✅ Verification Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment activated
- [ ] Dependencies installed
- [ ] .env configured
- [ ] Playwright working
- [ ] Webhook test successful
- [ ] System cron working (crontab -l)
- [ ] Cron logs being generated
- [ ] Logs directory created
- [ ] File permissions correct

## 🎯 Final Commands - Production Ready!

```bash
# 1. Quick setup verification
cd /www/wwwroot/your-domain.com
./status.sh
./test_webhook.sh

# 2. Check cron status
crontab -l

# 3. Manual test run
./run_cron_job.sh

# 4. Monitor aplikasi
tail -f logs/cron.log

# 5. Semua sudah siap production! 🚀
```

### **Super Quick Start (After Auto Install):**
```bash
nano .env                     # Edit config
./test_scraper.sh            # Test sekali
./run_cron_job.sh            # Test cron job
crontab -l                   # Verify cron setup
tail -f logs/cron.log        # Monitor logs
```

---

## 📞 Support

Jika ada masalah:
1. Check logs di `logs/` directory
2. Run `./status.sh` untuk diagnostic
3. Verify .env configuration
4. Test webhook connectivity

**Happy Scraping! 🎉**
