"""
Configuration management for QRIS mutation scraper
"""
import os
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

try:
    import pytz
except ImportError:  # pragma: no cover - handled at runtime
    pytz = None


class Config:
    """Application configuration loaded from environment variables"""
    
    def __init__(self):
        # Load .env file if it exists
        env_path = Path('.env')
        if env_path.exists():
            load_dotenv(env_path)
        
        # URLs
        self.BASE_URL = self._get_env('BASE_URL', 'https://brimerchant.bri.co.id')
        self.LOGIN_URL = self._get_env('LOGIN_URL', f'{self.BASE_URL}/auth/login')
        self.MUTASI_URL = self._get_env('MUTASI_URL', f'{self.BASE_URL}/transaksi')
        
        # Authentication
        self.LOGIN_PHONE = self._get_env('LOGIN_PHONE', '')
        self.EMAIL = self._get_env('EMAIL', '')
        self.LOGIN_ID = self._get_env('LOGIN_ID', self.LOGIN_PHONE or self.EMAIL)
        self.PASSWORD = self._get_env('PASSWORD', required=True)
        
        # Webhook
        self.WEBHOOK_URL = self._get_env('WEBHOOK_URL', 'http://localhost:8080/webhook/mutasi')
        
        # Browser settings
        self.TIMEZONE = self._get_env('TIMEZONE', 'Asia/Jakarta')
        self.HEADLESS = self._get_bool('HEADLESS', True)
        # Chromium build to launch. The bundled headless shell is blocked by the
        # Imperva/Incapsula WAF in front of BRI Merchant; the regular Chromium
        # build ('chromium') is not. Set empty to use Playwright's bundled build.
        self.BROWSER_CHANNEL = self._get_env('BROWSER_CHANNEL', 'chromium')
        self.USER_AGENT = self._get_env(
            'USER_AGENT', 
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Polling
        self.POLL_SECONDS = self._get_int('POLL_SECONDS', 120)
        
        # Cron settings
        self.CRON_INTERVAL_MINUTES = self._get_int('CRON_INTERVAL_MINUTES', 10)  # Increased for memory relief

        # Quiet hours: skip scraping between these times (in TIMEZONE, 24h "HH:MM").
        # Leave either empty to disable. A range may cross midnight (23:00-02:00).
        self.QUIET_HOURS_START = self._parse_time(self._get_env('QUIET_HOURS_START', ''))
        self.QUIET_HOURS_END = self._parse_time(self._get_env('QUIET_HOURS_END', ''))
        
        # File paths
        self.SESSION_FILE = self._get_env('SESSION_FILE', './data/session.json')
        self.CACHE_DB = self._get_env('CACHE_DB', './data/sent_ids.sqlite')
        
        # Debug settings
        self.DEBUG_SCREENSHOT = './data/debug_last.png'
        self.DEBUG_HTML = './data/debug_last.html'

        # Ensure data directory exists
        self._ensure_data_dir()
        
        # Validation
        self._validate()
    
    def _get_env(self, key: str, default: Optional[str] = None, required: bool = False) -> str:
        """Get environment variable with optional default"""
        value = os.getenv(key, default)
        if required and not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value or ""
    
    def _get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable"""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def _get_int(self, key: str, default: int) -> int:
        """Get integer environment variable"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default
    
    def _parse_time(self, value: str) -> Optional[dtime]:
        """Parse "HH:MM" (or "HH") into a time; returns None when unset/invalid"""
        value = (value or '').strip()
        if not value:
            return None
        try:
            parts = value.split(':')
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            return dtime(hour, minute)
        except (ValueError, IndexError):
            raise ValueError(
                f"Invalid time format '{value}'. Use 24-hour HH:MM, e.g. 23:00"
            )

    def is_quiet_time(self, now: Optional[datetime] = None) -> bool:
        """True when the current time falls inside the configured quiet hours.

        Times are evaluated in TIMEZONE, not the server's local timezone, so the
        window means the same thing regardless of how the VPS clock is set.
        """
        if not self.QUIET_HOURS_START or not self.QUIET_HOURS_END:
            return False

        if now is None:
            if pytz is None:
                raise ImportError("pytz is required for quiet hours. Run: pip install pytz")
            now = datetime.now(pytz.timezone(self.TIMEZONE))

        current = now.time()
        start, end = self.QUIET_HOURS_START, self.QUIET_HOURS_END

        if start == end:
            return False
        if start < end:
            return start <= current < end
        # Window crosses midnight, e.g. 23:00-02:00
        return current >= start or current < end

    def _ensure_data_dir(self):
        """Ensure data directory exists"""
        data_dir = Path('./data')
        data_dir.mkdir(exist_ok=True)
    
    def _validate(self):
        """Validate configuration"""
        if not self.LOGIN_ID:
            raise ValueError("LOGIN_ID (or LOGIN_PHONE/EMAIL) must be provided")

        if not self.PASSWORD:
            raise ValueError("PASSWORD must be provided")
        
        if self.POLL_SECONDS < 10:
            raise ValueError("POLL_SECONDS must be at least 10 seconds")
        
        if not self.WEBHOOK_URL:
            raise ValueError("WEBHOOK_URL must be provided")

        if not self.MUTASI_URL:
            raise ValueError("MUTASI_URL must be provided")

    def build_mutasi_url(self) -> str:
        """Return the mutation URL exactly as configured in MUTASI_URL.

        BRI Merchant already defaults its transaction page to the current date,
        so no date range or query string is appended here.
        """
        return self.MUTASI_URL


# Global config instance
config = Config()
