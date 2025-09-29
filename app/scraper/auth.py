"""
Authentication module for login flow
"""
from typing import Optional, TYPE_CHECKING
from ..config import config
from ..logger import LoggerMixin

if TYPE_CHECKING:
    from playwright.async_api import Page, BrowserContext


class AuthManager(LoggerMixin):
    """Handles authentication flow"""
    
    def __init__(self):
        super().__init__()
    
    async def login(self, page: 'Page') -> bool:
        """
        Perform login flow with robust selectors and error handling
        Returns True if login successful, False otherwise
        """
        try:
            self.log_info("Starting login process", url=config.LOGIN_URL)
            
            # Navigate to login page
            await page.goto(config.LOGIN_URL, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)  # Wait for page to settle
            
            # Handle any dialogs that might appear
            page.on("dialog", lambda dialog: dialog.accept())
            
            # Find and fill login identifier field (email/phone)
            login_filled = await self._fill_login_identifier(page)
            if not login_filled:
                self.log_error("Failed to find or fill login identifier field")
                return False
            
            # Find and fill password field
            password_filled = await self._fill_password(page)
            if not password_filled:
                self.log_error("Failed to find or fill password field")
                return False
            
            # Handle CSRF token if present
            await self._handle_csrf_token(page)
            
            # Submit the form
            submitted = await self._submit_form(page)
            if not submitted:
                self.log_error("Failed to submit login form")
                return False
            
            # Wait for login success
            success = await self._wait_for_login_success(page)
            if success:
                self.log_info("Login successful")
                return True
            else:
                self.log_error("Login failed - success indicators not found")
                return False
                
        except Exception as e:
            self.log_error("Login process failed", error=e)
            return False
    
    async def _fill_login_identifier(self, page: 'Page') -> bool:
        """Find and fill login identifier (phone/email) with multiple selector strategies"""
        if not config.LOGIN_ID:
            self.log_error("LOGIN_ID not configured")
            return False

        login_selectors = [
            # Phone specific selectors
            'input[type="tel"]',
            'input[name="phone"]',
            'input[name="no_handphone"]',
            'input[name="handphone"]',
            'input[name="nohp"]',
            'input[id*="handphone" i]',
            'input[id*="nohp" i]',
            'input[placeholder*="handphone" i]',
            'input[placeholder*="no handphone" i]',
            'input[placeholder*="nomor hp" i]',
            'input[placeholder*="no hp" i]',

            # Generic login/email selectors
            'input[type="email"]',
            'input[name="email"]',
            'input[name="username"]',
            'input[name="user"]',
            'input[name="login"]',
            'input[name="userid"]',
            'input[name="user_email"]',
            '#email',
            '#username',
            '#user',
            '#login',
            '#userid',
            '#user_email',
            'input.email',
            'input.username',
            'input.login',
            'input.user',
            'form input[type="text"]',
            '.login-form input[type="text"]',
            '.form-login input[type="text"]',
            'input[type="text"]'
        ]

        for selector in login_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=1000) and await element.is_enabled():
                    await element.click()
                    await element.fill(config.LOGIN_ID)
                    self.log_debug(f"Login identifier filled using selector: {selector}")
                    return True
            except Exception as exc:
                self.log_debug("Login field selector failed", selector=selector, error=str(exc))
                continue

        return False
    
    async def _fill_password(self, page: 'Page') -> bool:
        """Find and fill password field with multiple selector strategies"""
        password_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            'input[name="pass"]',
            'input[placeholder*="password" i]',
            'input[placeholder*="Password" i]',
            'input[placeholder*="kata sandi" i]',
            'input[id*="password" i]',
            'input[id*="pass" i]',
            'input.password',
            '#password',
            '#pass',
            '[data-testid*="password"]'
        ]
        
        for selector in password_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=1000):
                    await element.click()
                    await element.fill(config.PASSWORD)
                    self.log_debug(f"Password filled using selector: {selector}")
                    return True
            except:
                continue
        
        return False
    
    async def _handle_csrf_token(self, page: 'Page'):
        """Handle CSRF token if present"""
        csrf_selectors = [
            'input[name="_token"]',
            'input[name="csrf_token"]',
            'input[name="authenticity_token"]',
            'input[type="hidden"][name*="token"]'
        ]
        
        for selector in csrf_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=1000):
                    value = await element.get_attribute('value')
                    if value:
                        self.log_debug(f"CSRF token found: {selector}")
                        # Token is already in the form, no need to set it
                        break
            except:
                continue
    
    async def _submit_form(self, page: 'Page') -> bool:
        """Submit the login form with multiple strategies"""
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Login")',
            'button:has-text("Masuk")',
            'button:has-text("Sign In")',
            'button:has-text("Submit")',
            'button:has-text("Kirim")',
            '.btn-login',
            '.login-button',
            '#login-btn',
            '#submit',
            '[data-testid*="login"]',
            '[data-testid*="submit"]'
        ]
        
        for selector in submit_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible(timeout=1000):
                    await element.click()
                    self.log_debug(f"Form submitted using selector: {selector}")
                    return True
            except:
                continue
        
        # Try submitting by pressing Enter on password field
        try:
            password_field = page.locator('input[type="password"]').first
            if await password_field.is_visible():
                await password_field.press('Enter')
                self.log_debug("Form submitted using Enter key")
                return True
        except:
            pass
        
        return False
    
    async def _wait_for_login_success(self, page: 'Page', timeout: int = 10000) -> bool:
        """Wait for indicators of successful login"""
        try:
            # Wait for URL change (not on login page anymore)
            await page.wait_for_function(
                f'window.location.href !== "{config.LOGIN_URL}"',
                timeout=timeout
            )
            
            # Additional checks for success indicators
            success_indicators = [
                # URL patterns that indicate success
                lambda: not page.url.endswith('/login'),
                lambda: 'dashboard' in page.url.lower(),
                lambda: 'home' in page.url.lower(),
                lambda: 'mutasi' in page.url.lower(),
            ]
            
            # Check if any success indicator is true
            for indicator in success_indicators:
                try:
                    if indicator():
                        return True
                except:
                    continue
            
            # Check for logout/profile elements that indicate logged in state
            logged_in_selectors = [
                'a:has-text("Logout")',
                'a:has-text("Keluar")',
                'button:has-text("Logout")',
                'button:has-text("Keluar")',
                '.user-profile',
                '.logout',
                '[data-testid*="logout"]'
            ]
            
            for selector in logged_in_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        self.log_debug(f"Login success confirmed by element: {selector}")
                        return True
                except:
                    continue
            
            # If URL changed from login page, consider it success
            if page.url != config.LOGIN_URL and not page.url.endswith('/login'):
                return True
            
            return False
            
        except Exception as e:
            self.log_warning("Error waiting for login success", error=str(e))
            # If URL changed, still consider it potentially successful
            return page.url != config.LOGIN_URL
    
    async def is_logged_in(self, page: 'Page') -> bool:
        """Check if user is already logged in"""
        try:
            # Navigate to a protected page to test login status
            url = config.build_mutasi_url()
            self.log_debug("Checking login status via mutation page", url=url)
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)

            current_url = page.url.lower()

            # Detect login form elements (phone/password fields, submit buttons)
            login_form_selectors = [
                'input[type="tel"]',
                'input[name="phone"]',
                'input[name="no_handphone"]',
                'input[name="handphone"]',
                'input[name="nohp"]',
                'input[type="password"]',
                'button:has-text("Masuk")',
                'button:has-text("Login")',
                'form button[type="submit"]'
            ]

            for selector in login_form_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible(timeout=1000):
                        self.log_info("Login form detected", selector=selector)
                        return False
                except Exception:
                    continue

            # If URL explicitly indicates login, treat as logged out
            if current_url.endswith('/login') or 'auth/login' in current_url:
                self.log_info("Not logged in - on login URL", url=page.url)
                return False

            # Check for elements that indicate we're logged in
            logged_in_indicators = [
                'table',  # Mutation table present
                '.table',
                '#mutasi',
                'tbody tr',  # Table rows present
                'h1:has-text("Daftar Transaksi")',
                'h2:has-text("Transaksi QRIS")',
                'a:has-text("Logout")',
                'button:has-text("Logout")'
            ]

            for selector in logged_in_indicators:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        self.log_info("Already logged in", indicator=selector)
                        return True
                except Exception:
                    continue

            # If no obvious login form and URL isn't login, treat as logged in to avoid re-login loops
            if 'login' not in current_url:
                self.log_info("Assuming logged in based on URL without login form", url=page.url)
                return True

            self.log_info("Login status unclear, assuming not logged in")
            return False

        except Exception as e:
            self.log_warning("Error checking login status", error=str(e))
            return False
