"""
Configuration management for QRIS mutation scraper
"""
import os
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional, Union
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
        self.LOGIN_URL = self._get_env('LOGIN_URL', f'{self.BASE_URL}/login')
        self.MUTASI_URL = self._get_env('MUTASI_URL', f'{self.BASE_URL}/mutasi_qris')
        mutasi_url_lower = self.MUTASI_URL.lower()
        
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
        self.USER_AGENT = self._get_env(
            'USER_AGENT', 
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Polling
        self.POLL_SECONDS = self._get_int('POLL_SECONDS', 120)
        
        # Cron settings
        self.CRON_INTERVAL_MINUTES = self._get_int('CRON_INTERVAL_MINUTES', 10)  # Increased for memory relief
        
        # File paths
        self.SESSION_FILE = self._get_env('SESSION_FILE', './data/session.json')
        self.CACHE_DB = self._get_env('CACHE_DB', './data/sent_ids.sqlite')
        
        # Debug settings
        self.DEBUG_SCREENSHOT = './data/debug_last.png'
        self.DEBUG_HTML = './data/debug_last.html'

        # Mutation date range handling
        date_range_default = 'brimerchant.bri.co.id' in mutasi_url_lower
        query_default = 'type=qris' if date_range_default else ''
        self.MUTASI_DATE_RANGE_REQUIRED = self._get_bool('MUTASI_DATE_RANGE_REQUIRED', date_range_default)
        self.MUTASI_DATE_FORMAT = self._get_env('MUTASI_DATE_FORMAT', '%Y-%m-%d')
        self.MUTASI_DATE_SEPARATOR = self._get_env('MUTASI_DATE_SEPARATOR', 'and')
        self.MUTASI_QUERY_STRING = self._get_env('MUTASI_QUERY_STRING', query_default)
        self.MUTASI_DATE_OFFSET_DAYS = self._get_int('MUTASI_DATE_OFFSET_DAYS', 0)
        
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

        if self.MUTASI_DATE_RANGE_REQUIRED and pytz is None:
            raise ImportError("pytz is required for date range handling. Install pytz or set MUTASI_DATE_RANGE_REQUIRED=false")

    def build_mutasi_url(
        self,
        start: Optional[Union[datetime, date, str]] = None,
        end: Optional[Union[datetime, date, str]] = None,
    ) -> str:
        """Build mutation URL, optionally injecting date range parameters"""
        if not self.MUTASI_DATE_RANGE_REQUIRED:
            return self.MUTASI_URL

        if pytz is None:
            raise ImportError("pytz is required to build mutation URL with date range")

        tz = pytz.timezone(self.TIMEZONE)

        def _to_date(value: Optional[Union[datetime, date, str]]) -> Optional[date]:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            try:
                return datetime.strptime(value, self.MUTASI_DATE_FORMAT).date()
            except ValueError as exc:
                raise ValueError(
                    f"Cannot parse date '{value}' using MUTASI_DATE_FORMAT='{self.MUTASI_DATE_FORMAT}'"
                ) from exc

        offset_now = datetime.now(tz) + timedelta(days=self.MUTASI_DATE_OFFSET_DAYS)
        start_date = _to_date(start) or offset_now.date()
        end_date = _to_date(end) or start_date

        start_str = start_date.strftime(self.MUTASI_DATE_FORMAT)
        end_str = end_date.strftime(self.MUTASI_DATE_FORMAT)

        base = self.MUTASI_URL.rstrip('/')
        date_segment = f"{start_str}{self.MUTASI_DATE_SEPARATOR}{end_str}"
        url = f"{base}/{date_segment}"

        query = (self.MUTASI_QUERY_STRING or '').strip()
        if query:
            query = query if query.startswith('?') else f"?{query}"
            url = f"{url}{query}"

        return url


# Global config instance
config = Config()
