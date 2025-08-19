"""
Dependency management and imports with fallbacks
"""

# Check for required dependencies
def check_dependencies():
    """Check if all required dependencies are available"""
    missing = []
    
    try:
        import playwright
    except ImportError:
        missing.append("playwright")
    
    try:
        import httpx
    except ImportError:
        missing.append("httpx")
    
    try:
        import aiosqlite
    except ImportError:
        missing.append("aiosqlite")
    
    try:
        import pytz
    except ImportError:
        missing.append("pytz")
    
    try:
        from dateutil import parser
    except ImportError:
        missing.append("python-dateutil")
    
    try:
        import tenacity
    except ImportError:
        missing.append("tenacity")
    
    if missing:
        deps_str = ", ".join(missing)
        raise ImportError(f"Missing required dependencies: {deps_str}. Run: pip install {deps_str}")

# Safe imports with error handling
def safe_import_playwright():
    """Safely import playwright modules"""
    try:
        from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Locator
        return async_playwright, Browser, BrowserContext, Page, Locator
    except ImportError:
        return None, None, None, None, None

def safe_import_httpx():
    """Safely import httpx"""
    try:
        import httpx
        return httpx
    except ImportError:
        return None

def safe_import_aiosqlite():
    """Safely import aiosqlite"""
    try:
        import aiosqlite
        return aiosqlite
    except ImportError:
        return None

def safe_import_pytz():
    """Safely import pytz"""
    try:
        import pytz
        return pytz
    except ImportError:
        return None

def safe_import_dateutil():
    """Safely import dateutil"""
    try:
        from dateutil import parser as date_parser
        return date_parser
    except ImportError:
        return None

def safe_import_tenacity():
    """Safely import tenacity"""
    try:
        from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
        return retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    except ImportError:
        # Create dummy decorators
        def dummy_retry(*args, **kwargs):
            def decorator(func):
                return func
            return decorator
        
        return dummy_retry, None, None, None
