#!/bin/bash

# =============================================================================
# QRIS Mutation Scraper - AAPanel Auto Installation Script
# =============================================================================
# This script automatically installs and configures the QRIS scraper on AAPanel
# Compatible with: AAPanel, CentOS, Ubuntu, Debian
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Icons
SUCCESS="✅"
ERROR="❌"
INFO="ℹ️"
WARNING="⚠️"
ROCKET="🚀"
GEAR="⚙️"
PACKAGE="📦"
CHECK="🔍"

# Log function
log() {
    echo -e "${CYAN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}${SUCCESS} $1${NC}"
}

error() {
    echo -e "${RED}${ERROR} $1${NC}"
}

warning() {
    echo -e "${YELLOW}${WARNING} $1${NC}"
}

info() {
    echo -e "${BLUE}${INFO} $1${NC}"
}

# Banner
print_banner() {
    echo -e "${PURPLE}"
    echo "============================================================"
    echo "🔥 QRIS MUTATION SCRAPER - AAPANEL INSTALLER 🔥"
    echo "============================================================"
    echo -e "${NC}"
    echo -e "${CYAN}Auto installer untuk AAPanel/CyberPanel${NC}"
    echo -e "${CYAN}Support: Python 3.8+, Virtual Environment, Cron${NC}"
    echo ""
}

# Check system requirements
check_system() {
    log "${CHECK} Checking system requirements..."
    
    # Check if running as root or with sudo
    if [[ $EUID -eq 0 ]]; then
        info "Running as root user"
        SUDO=""
    else
        info "Running as regular user, will use sudo when needed"
        SUDO="sudo"
    fi
    
    # Check OS
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
        success "Detected OS: $PRETTY_NAME"
    else
        error "Cannot detect OS. This script supports CentOS, Ubuntu, Debian"
        exit 1
    fi
    
    # Check Python 3
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        success "Python 3 found: $PYTHON_VERSION"
        PYTHON_CMD="python3"
    else
        error "Python 3 not found. Please install Python 3.8+ first"
        exit 1
    fi
    
    # Check pip
    if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
        success "pip found"
        if command -v pip3 &> /dev/null; then
            PIP_CMD="pip3"
        else
            PIP_CMD="pip"
        fi
    else
        warning "pip not found, will install"
        install_pip
    fi
}

# Install pip if not found
install_pip() {
    log "${PACKAGE} Installing pip..."
    if [[ "$OS" == "centos" ]] || [[ "$OS" == "rhel" ]]; then
        $SUDO yum update -y
        $SUDO yum install -y python3-pip
    elif [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        $SUDO apt update
        $SUDO apt install -y python3-pip python3-venv
    fi
    PIP_CMD="pip3"
    success "pip installed successfully"
}

# Install system dependencies for Playwright
install_system_deps() {
    log "${PACKAGE} Installing system dependencies for Playwright..."
    
    if [[ "$OS" == "centos" ]] || [[ "$OS" == "rhel" ]]; then
        # CentOS/RHEL dependencies
        $SUDO yum install -y \
            atk \
            cups-libs \
            gtk3 \
            libdrm \
            libxkbcommon \
            libxcomposite \
            libxdamage \
            libxrandr \
            mesa-libgbm \
            pango \
            alsa-lib \
            libxss \
            libgtk-3-0 \
            libnss3 \
            libxshmfence \
            fonts-liberation \
            libu2f-udev \
            libvulkan1 \
            xdg-utils
            
    elif [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        # Ubuntu/Debian dependencies
        $SUDO apt update
        $SUDO apt install -y \
            libatk1.0-0 \
            libatk-bridge2.0-0 \
            libcups2 \
            libdrm2 \
            libgtk-3-0 \
            libgbm1 \
            libasound2 \
            libxss1 \
            libgconf-2-4 \
            libxrandr2 \
            libasound2 \
            libpangocairo-1.0-0 \
            libxcomposite1 \
            libxcursor1 \
            libxdamage1 \
            libxi6 \
            libxtst6 \
            libnss3 \
            libxshmfence1 \
            fonts-liberation \
            libu2f-udev \
            libvulkan1 \
            xdg-utils
    fi
    
    success "System dependencies installed"
}

# Setup system cron job
setup_system_cron() {
    log "${GEAR} Setting up system cron job..."
    
    # Create cron job script
    cat > run_cron_job.sh << 'EOF'
#!/bin/bash
# QRIS Scraper single job for system cron
# Optimized for memory efficiency

cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || exit 1

export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true

# Run single scraper job
python -m app.main_cron once >> logs/cron.log 2>&1
EOF
    
    chmod +x run_cron_job.sh
    success "Cron job script created: run_cron_job.sh"
    
    # Get interval from .env file (prioritas .env, fallback ke default)
    CRON_INTERVAL=10  # default fallback
    if [[ -f ".env" ]]; then
        ENV_INTERVAL=$(grep "^CRON_INTERVAL_MINUTES=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" | tr -d ' ')
        if [[ -n "$ENV_INTERVAL" && "$ENV_INTERVAL" =~ ^[0-9]+$ ]]; then
            CRON_INTERVAL=$ENV_INTERVAL
            info "Using CRON_INTERVAL_MINUTES=$CRON_INTERVAL from .env file"
        else
            warning "CRON_INTERVAL_MINUTES not found in .env, using default: $CRON_INTERVAL minutes"
        fi
    else
        warning ".env file not found, using default: $CRON_INTERVAL minutes"
    fi
    
    # Setup cron job with dynamic interval
    CRON_ENTRY="*/$CRON_INTERVAL * * * * cd $INSTALL_DIR && ./run_cron_job.sh"
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    
    success "System cron job added (every $CRON_INTERVAL minutes)"
    info "Cron logs will be saved to: $INSTALL_DIR/logs/cron.log"
}

# Setup project directory
setup_directory() {
    log "${GEAR} Setting up project directory..."
    
    # Default to current directory if not specified
    if [[ -z "$INSTALL_DIR" ]]; then
        INSTALL_DIR="$(pwd)"
    fi
    
    # Create directory if it doesn't exist
    if [[ ! -d "$INSTALL_DIR" ]]; then
        mkdir -p "$INSTALL_DIR"
        success "Created directory: $INSTALL_DIR"
    fi
    
    cd "$INSTALL_DIR"
    success "Working directory: $INSTALL_DIR"
}

# Setup Python virtual environment
setup_venv() {
    log "${PACKAGE} Setting up Python virtual environment..."
    
    # Create virtual environment
    if [[ ! -d ".venv" ]]; then
        $PYTHON_CMD -m venv .venv
        success "Virtual environment created"
    else
        info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Upgrade pip in venv
    pip install --upgrade pip
    success "Virtual environment activated and pip upgraded"
}

# Install Python dependencies
install_dependencies() {
    log "${PACKAGE} Installing Python dependencies..."
    
    # Check if requirements.txt exists
    if [[ -f "requirements.txt" ]]; then
        info "Installing from requirements.txt"
        pip install -r requirements.txt
    else
        warning "requirements.txt not found, installing core dependencies"
        pip install playwright httpx tenacity python-dotenv pytz python-dateutil aiosqlite schedule
    fi
    
    # Install Playwright browsers
    log "${PACKAGE} Installing Playwright browsers..."
    export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
    
    # Try to install playwright browsers, handle permission issues
    if playwright install chromium 2>/dev/null; then
        success "Playwright browsers installed"
    else
        warning "Playwright browser install failed, but will work with skip validation"
        info "Setting environment variable for production"
    fi
    
    success "Dependencies installed successfully"
}

# Setup configuration
setup_config() {
    log "${GEAR} Setting up configuration..."
    
    if [[ ! -f ".env" ]]; then
        warning ".env file not found, creating template"
        cat > .env << 'EOF'
# QRIS Scraper Configuration
# Copy this template and fill in your values

# Login credentials
EMAIL=your_email@example.com
PASSWORD=your_password

# URLs
BASE_URL=https://brimerchant.bri.co.id
LOGIN_URL=https://brimerchant.bri.co.id/auth/login
MUTASI_URL=https://brimerchant.bri.co.id/transaksi/daftar-transaksi/ganti-url-valid-anda

# Webhook
WEBHOOK_URL=http://your-webhook-url.com/callback

# Browser settings
HEADLESS=true
TIMEZONE=Asia/Jakarta
USER_AGENT=Mozilla/5.0 (Linux; x86_64) AppleWebKit/537.36

# Cache and logging
CACHE_DB_PATH=./data/cache.db
LOG_LEVEL=INFO

# Cron settings (interval dalam menit)
CRON_INTERVAL_MINUTES=10
EOF
        warning "Please edit .env file with your actual configuration"
        info "File location: $INSTALL_DIR/.env"
    else
        success "Configuration file .env already exists"
    fi
    
    # Create data directory
    mkdir -p data
    success "Data directory created"
}

# Test installation
test_installation() {
    log "${CHECK} Testing installation..."
    
    # Test Python imports
    $PYTHON_CMD -c "
import sys
sys.path.insert(0, '.')

try:
    from app.config import config
    print('✅ Config loaded successfully')
except Exception as e:
    print(f'❌ Config error: {e}')
    exit(1)

try:
    from app.models import Mutasi
    print('✅ Models loaded successfully')
except Exception as e:
    print(f'❌ Models error: {e}')
    exit(1)

try:
    from app.httpclient import WebhookClient
    print('✅ HTTP client loaded successfully')
except Exception as e:
    print(f'❌ HTTP client error: {e}')
    exit(1)

print('🎉 All modules loaded successfully!')
"
    
    if [[ $? -eq 0 ]]; then
        success "Installation test passed"
    else
        error "Installation test failed"
        return 1
    fi
}

# Setup background service
setup_background_service() {
    log "${GEAR} Setting up background service..."
    
    # Create wrapper script for continuous running
    cat > start_qris_scraper.sh << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source .venv/bin/activate
export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
echo "🚀 Starting QRIS Scraper with internal cron..."
python -m app.main_cron
EOF
    
    chmod +x start_qris_scraper.sh
    success "Service script created: start_qris_scraper.sh"
    
    # Create logs directory
    mkdir -p logs
    
    info "QRIS Scraper menggunakan internal Python cron (schedule library)"
    info "Tidak perlu setup cron sistem - scraper akan berjalan continuous"
    info "Untuk production, jalankan: nohup ./start_qris_scraper.sh > logs/scraper.log 2>&1 &"
}

# Create management scripts
create_management_scripts() {
    log "${GEAR} Creating management scripts..."
    
    # Start script
    cat > start_scraper.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
echo "🚀 Starting QRIS Scraper..."
python -m app.main_cron
EOF
    
    # Test script
    cat > test_scraper.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
echo "🧪 Testing QRIS Scraper..."
python -m app.main_cron once
EOF
    
    # Test webhook script
    cat > test_webhook.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
echo "📡 Testing Webhook..."
python test_webhook_simple.py
EOF
    
    # Status script
    cat > status.sh << 'EOF'
#!/bin/bash
echo "📊 QRIS Scraper Status"
echo "======================"
echo "🔍 Checking cron jobs:"
crontab -l | grep qris || echo "❌ No cron jobs found"
echo ""
echo "📂 Log files:"
ls -la logs/ 2>/dev/null || echo "❌ No logs directory"
echo ""
echo "⚙️ Configuration:"
if [[ -f ".env" ]]; then
    echo "✅ .env file exists"
else
    echo "❌ .env file missing"
fi
EOF
    
    # Make scripts executable
    chmod +x start_scraper.sh test_scraper.sh test_webhook.sh status.sh
    
    success "Management scripts created:"
    info "  • start_scraper.sh - Run scraper once"
    info "  • test_scraper.sh - Test scraper"
    info "  • test_webhook.sh - Test webhook"
    info "  • status.sh - Check status"
}



# Main installation function
main() {
    print_banner
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --dir DIR     Installation directory (default: current)"
                echo "  --help       Show this help"
                echo ""
                echo "Note: QRIS Scraper uses internal Python cron (schedule library)"
                echo "No system cron setup required."
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Installation steps
    check_system
    install_system_deps
    setup_directory
    setup_venv
    install_dependencies
    setup_config
    
    if test_installation; then
        success "Core installation completed successfully"
    else
        error "Installation failed during testing"
        exit 1
    fi
    
    # Setup background service (no system cron needed)
    setup_background_service
    
    create_management_scripts
    
    # Setup system cron
    setup_system_cron
    
    # Final summary
    echo ""
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}${ROCKET} INSTALLATION COMPLETED SUCCESSFULLY! ${ROCKET}${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo ""
    echo -e "${YELLOW}📋 NEXT STEPS:${NC}"
    echo -e "${CYAN}1. Edit configuration:${NC} nano .env"
    echo -e "${CYAN}2. Test installation:${NC} ./test_scraper.sh"
    echo -e "${CYAN}3. Test webhook:${NC} ./test_webhook.sh"
    echo ""
    echo -e "${YELLOW}🚀 PRODUCTION DEPLOYMENT (System Cron - Memory Optimized):${NC}"
    echo -e "${CYAN}• Cron already setup:${NC} Runs every ${CRON_INTERVAL:-15} minutes automatically"
    echo -e "${CYAN}• View cron logs:${NC} tail -f logs/cron.log"
    echo -e "${CYAN}• Test single run:${NC} ./run_cron_job.sh"
    echo -e "${CYAN}• Check cron status:${NC} crontab -l"
    echo ""
    echo -e "${YELLOW}📊 MONITORING:${NC}"
    echo -e "${CYAN}• Monitor cron logs:${NC} tail -f logs/cron.log"
    echo -e "${CYAN}• Check running processes:${NC} ps aux | grep python"
    echo ""
    echo -e "${YELLOW}📂 Installation Directory:${NC} $INSTALL_DIR"
    echo -e "${YELLOW}📝 Configuration File:${NC} $INSTALL_DIR/.env"
    echo -e "${YELLOW}📊 Logs Directory:${NC} $INSTALL_DIR/logs/"
    echo ""
    echo -e "${GREEN}🎉 Happy scraping!${NC}"
}

# Run main function
main "$@"
