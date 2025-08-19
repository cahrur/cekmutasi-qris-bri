"""
Session storage for Playwright browser state
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any, TYPE_CHECKING
from ..logger import LoggerMixin

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext


class SessionStore(LoggerMixin):
    """Manages browser session state (cookies, localStorage) persistence"""
    
    def __init__(self, session_file: str):
        super().__init__()
        self.session_file = Path(session_file)
        
        # Ensure parent directory exists
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
    
    async def save_session(self, context: 'BrowserContext') -> bool:
        """Save browser context state to file"""
        try:
            # Get storage state from context
            storage_state = await context.storage_state()
            
            # Save to file
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(storage_state, f, indent=2, ensure_ascii=False)
            
            self.log_info("Session saved successfully", file=str(self.session_file))
            return True
            
        except Exception as e:
            self.log_error("Failed to save session", error=e, file=str(self.session_file))
            return False
    
    async def load_session(self) -> Optional[Dict[str, Any]]:
        """Load browser context state from file"""
        try:
            if not self.session_file.exists():
                self.log_info("No existing session file found", file=str(self.session_file))
                return None
            
            with open(self.session_file, 'r', encoding='utf-8') as f:
                storage_state = json.load(f)
            
            self.log_info("Session loaded successfully", file=str(self.session_file))
            return storage_state
            
        except Exception as e:
            self.log_error("Failed to load session", error=e, file=str(self.session_file))
            return None
    
    def session_exists(self) -> bool:
        """Check if session file exists"""
        return self.session_file.exists()
    
    def clear_session(self) -> bool:
        """Remove session file"""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
                self.log_info("Session file cleared", file=str(self.session_file))
                return True
            return False
        except Exception as e:
            self.log_error("Failed to clear session", error=e, file=str(self.session_file))
            return False
    
    def get_session_age_hours(self) -> Optional[float]:
        """Get age of session file in hours"""
        try:
            if not self.session_file.exists():
                return None
            
            import time
            file_mtime = self.session_file.stat().st_mtime
            current_time = time.time()
            age_seconds = current_time - file_mtime
            age_hours = age_seconds / 3600
            
            return age_hours
            
        except Exception as e:
            self.log_error("Failed to get session age", error=e)
            return None
