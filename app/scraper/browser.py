"""
Browser management for Playwright automation
"""
from typing import Optional, TYPE_CHECKING
from ..config import config
from ..logger import LoggerMixin

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None


class BrowserManager(LoggerMixin):
    """Manages browser instance and context for scraping"""
    
    def __init__(self):
        super().__init__()
        if async_playwright is None:
            raise ImportError("playwright is required but not installed. Run: pip install playwright")
        
        self.playwright = None
        self.browser: Optional['Browser'] = None
        self.context: Optional['BrowserContext'] = None
    
    async def start(self, storage_state: Optional[dict] = None) -> 'BrowserContext':
        """Start browser and create context with proper settings"""
        try:
            # Set environment variables for better compatibility
            import os
            import tempfile
            
            # Skip host validation for shared hosting
            os.environ['PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS'] = 'true'
            
            if os.name == 'nt':  # Windows
                if not os.environ.get('TMPDIR'):
                    os.environ['TMPDIR'] = tempfile.gettempdir()
                if not os.environ.get('TMP'):
                    os.environ['TMP'] = tempfile.gettempdir()
                if not os.environ.get('TEMP'):
                    os.environ['TEMP'] = tempfile.gettempdir()
            
            if async_playwright is None:
                raise ImportError("playwright is required but not installed")
            self.playwright = await async_playwright().start()
            
            # Launch browser with memory optimization and Windows fixes
            launch_args = [
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--memory-pressure-off',
                '--max_old_space_size=256',
                '--no-zygote',
                '--no-first-run',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--aggressive-cache-discard',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-background-networking'
            ]
            
            # Additional Windows fixes
            if os.name == 'nt':
                launch_args.extend([
                    '--disable-gpu',
                    '--disable-gpu-sandbox',
                    '--disable-software-rasterizer',
                    '--no-first-run'
                ])
            
            # BRI Merchant sits behind Imperva/Incapsula, which blocks Playwright's
            # bundled headless shell: every /_nuxt/*.js asset comes back 403 and the
            # Nuxt SPA never renders, so no login field ever appears. The regular
            # Chromium build (channel='chromium') runs new-headless and passes.
            launch_kwargs = {
                'headless': config.HEADLESS,
                'args': launch_args,
            }
            if config.BROWSER_CHANNEL:
                launch_kwargs['channel'] = config.BROWSER_CHANNEL

            try:
                self.browser = await self.playwright.chromium.launch(**launch_kwargs)
            except Exception as exc:
                if not config.BROWSER_CHANNEL:
                    raise
                self.log_warning(
                    "Browser channel not available, falling back to bundled Chromium. "
                    "Run: playwright install chromium",
                    channel=config.BROWSER_CHANNEL,
                    error=str(exc),
                )
                launch_kwargs.pop('channel')
                self.browser = await self.playwright.chromium.launch(**launch_kwargs)
            
            # Create context with proper settings
            context_options = {
                'user_agent': config.USER_AGENT,
                'timezone_id': config.TIMEZONE,
                'locale': 'id-ID',
                'viewport': {'width': 1920, 'height': 1080},
                'java_script_enabled': True,
                'accept_downloads': False,
                'ignore_https_errors': True,
            }
            
            # Add storage state if provided
            if storage_state:
                context_options['storage_state'] = storage_state
            
            self.context = await self.browser.new_context(**context_options)
            
            # NOTE: do NOT set static extra HTTP headers or inject a "stealth"
            # script here. Both were present before and got this scraper blocked by
            # the Imperva/Incapsula WAF on datacenter IPs:
            #
            #  - Static Sec-Fetch-* / Accept headers are applied to EVERY request, so
            #    each /_nuxt/*.js subresource was sent as `Sec-Fetch-Dest: document`
            #    instead of `script`. The HTML document loaded (200) while every asset
            #    was refused, leaving the Nuxt SPA unrendered and no login field.
            #  - The stealth script claimed `navigator.platform = 'Win32'` on Linux and
            #    a fake plugins array, which is a stronger bot signal than plain headless.
            #
            # Chromium's own headers are consistent; leave them alone. Passing the WAF
            # relies on the regular Chromium build (BROWSER_CHANNEL=chromium) instead.

            self.log_info("Browser started successfully", 
                         headless=config.HEADLESS, 
                         channel=config.BROWSER_CHANNEL or 'bundled',
                         timezone=config.TIMEZONE)
            
            return self.context
            
        except Exception as e:
            self.log_error("Failed to start browser", error=e)
            await self.cleanup()
            raise
    
    async def new_page(self) -> 'Page':
        """Create a new page in the current context"""
        if not self.context:
            raise RuntimeError("Browser context not initialized")
        
        page = await self.context.new_page()
        
        # Set additional page settings with error handling
        try:
            if hasattr(page, 'set_default_timeout') and callable(getattr(page, 'set_default_timeout')):
                timeout_method = getattr(page, 'set_default_timeout')
                await timeout_method(30000)  # 30 seconds
            if hasattr(page, 'set_default_navigation_timeout') and callable(getattr(page, 'set_default_navigation_timeout')):
                nav_timeout_method = getattr(page, 'set_default_navigation_timeout')
                await nav_timeout_method(60000)  # 60 seconds
        except Exception as e:
            self.log_warning("Could not set page timeouts", error=str(e))
        
        return page
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.context:
                await self.context.close()
                self.context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            self.log_info("Browser cleanup completed")
            
        except Exception as e:
            self.log_error("Error during browser cleanup", error=e)
    
    async def save_debug_info(self, page: 'Page', prefix: str = "debug"):
        """Save screenshot and HTML for debugging"""
        try:
            # Take screenshot
            screenshot_path = f"./data/{prefix}_last.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            
            # Save HTML
            html_path = f"./data/{prefix}_last.html"
            html_content = await page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.log_info("Debug info saved", 
                         screenshot=screenshot_path, 
                         html=html_path)
            
        except Exception as e:
            self.log_error("Failed to save debug info", error=e)
    
    async def wait_for_network_idle(self, page: 'Page', timeout: int = 10000):
        """Wait for network to be idle"""
        try:
            await page.wait_for_load_state('networkidle', timeout=timeout)
        except Exception as e:
            self.log_warning("Network idle timeout", error=str(e))
    
    async def handle_dialogs(self, page: 'Page'):
        """Set up dialog handlers for alerts, confirms, etc."""
        async def dialog_handler(dialog):
            self.log_info(f"Dialog appeared: {dialog.type} - {dialog.message}")
            await dialog.accept()
        
        page.on("dialog", dialog_handler)
