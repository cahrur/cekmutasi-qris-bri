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

    # How long to wait for the client-side rendered login form to appear
    FORM_TIMEOUT_MS = 30000

    def __init__(self):
        super().__init__()

    async def _wait_for_any(self, page: 'Page', selectors: list, timeout: int) -> bool:
        """Wait until any of the given selectors is visible.

        Playwright's is_visible() ignores its timeout and returns immediately, so
        selector probing must be preceded by a real wait or a slow page always fails.
        """
        combined = ', '.join(selectors)
        try:
            await page.locator(combined).first.wait_for(state='visible', timeout=timeout)
            return True
        except Exception as exc:
            self.log_debug("No matching field appeared", error=str(exc))
            return False

    async def _log_page_inputs(self, page: 'Page'):
        """Log the input fields actually present, to diagnose selector mismatches"""
        try:
            fields = await page.evaluate(
                """() => Array.from(document.querySelectorAll('input, select, textarea')).map(el => ({
                    tag: el.tagName.toLowerCase(),
                    type: el.getAttribute('type'),
                    name: el.getAttribute('name'),
                    id: el.getAttribute('id'),
                    placeholder: el.getAttribute('placeholder'),
                }))"""
            )
            self.log_error("Fields found on page", url=page.url, count=len(fields), fields=fields)
            title = await page.title()
            self.log_error("Page title", title=title)
        except Exception as exc:
            self.log_warning("Could not inspect page fields", error=str(exc))
    
    async def login(self, page: 'Page') -> bool:
        """
        Perform login flow with robust selectors and error handling
        Returns True if login successful, False otherwise
        """
        try:
            self.log_info("Starting login process", url=config.LOGIN_URL)
            
            # Navigate to login page
            await page.goto(config.LOGIN_URL, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)  # Wait for page to settle
            
            # Save screenshot before login attempt (debug only)
            await self._save_debug_screenshot(page, "before_login")
            
            # Handle any dialogs that might appear
            page.on("dialog", lambda dialog: dialog.accept())
            
            # Find and fill login identifier field (email/phone)
            login_filled = await self._fill_login_identifier(page)
            if not login_filled:
                self.log_error("Failed to find or fill login identifier field")
                await self._save_debug_screenshot(page, "login_field_not_found")
                return False
            
            # Small delay after filling login field
            await page.wait_for_timeout(500)
            
            # Find and fill password field
            password_filled = await self._fill_password(page)
            if not password_filled:
                self.log_error("Failed to find or fill password field")
                await self._save_debug_screenshot(page, "password_field_not_found")
                return False
            
            # Small delay after filling password
            await page.wait_for_timeout(500)
            
            # Handle CSRF token if present
            await self._handle_csrf_token(page)
            
            # Submit the form
            submitted = await self._submit_form(page)
            if not submitted:
                self.log_error("Failed to submit login form")
                await self._save_debug_screenshot(page, "submit_failed")
                return False
            
            # Wait for form submission to process (important for VPS latency)
            await page.wait_for_timeout(5000)
            
            # Wait for login success
            success = await self._wait_for_login_success(page)
            if success:
                self.log_info("Login successful")
                return True
            else:
                self.log_error("Login failed - success indicators not found")
                await self._save_debug_screenshot(page, "login_failed")
                # Log current URL for debugging
                self.log_error("Current URL after login attempt", url=page.url)
                return False
                
        except Exception as e:
            self.log_error("Login process failed", error=e)
            try:
                await self._save_debug_screenshot(page, "login_exception")
            except:
                pass
            return False
    
    async def _save_debug_screenshot(self, page: 'Page', name: str):
        """Save debug screenshot and HTML (only when DEBUG_SCREENSHOTS is enabled)"""
        import os
        
        # Only save screenshots if DEBUG_SCREENSHOTS is enabled
        debug_enabled = os.getenv('DEBUG_SCREENSHOTS', 'false').lower() in ('true', '1', 'yes')
        if not debug_enabled:
            return
            
        try:
            os.makedirs('./data', exist_ok=True)
            
            screenshot_path = f"./data/debug_{name}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            self.log_debug(f"Debug screenshot saved: {screenshot_path}")
            
            html_path = f"./data/debug_{name}.html"
            html_content = await page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            self.log_debug(f"Debug HTML saved: {html_path}")
            
        except Exception as e:
            self.log_warning(f"Failed to save debug screenshot: {e}")
    
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

        # The login form is rendered client-side, so wait for any candidate field to
        # appear before probing selectors (is_visible() never waits on its own).
        if not await self._wait_for_any(page, login_selectors, self.FORM_TIMEOUT_MS):
            self.log_error(
                "Login form did not render within timeout",
                timeout_ms=self.FORM_TIMEOUT_MS,
                url=page.url,
            )
            await self._log_page_inputs(page)
            return False

        for selector in login_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible() and await element.is_enabled():
                    await element.click()
                    await element.fill(config.LOGIN_ID)
                    self.log_debug(f"Login identifier filled using selector: {selector}")
                    return True
            except Exception as exc:
                self.log_debug("Login field selector failed", selector=selector, error=str(exc))
                continue

        await self._log_page_inputs(page)
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
        
        if not await self._wait_for_any(page, password_selectors, self.FORM_TIMEOUT_MS):
            self.log_error(
                "Password field did not render within timeout",
                timeout_ms=self.FORM_TIMEOUT_MS,
                url=page.url,
            )
            await self._log_page_inputs(page)
            return False

        for selector in password_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible():
                    await element.click()
                    await element.fill(config.PASSWORD)
                    self.log_debug(f"Password filled using selector: {selector}")
                    return True
            except:
                continue
        
        await self._log_page_inputs(page)
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
                if await element.count():
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
    
    async def _wait_for_login_success(self, page: 'Page', timeout: int = 30000) -> bool:
        """Wait for indicators of successful login"""
        try:
            # Wait for URL change (not on login page anymore)
            # Check for both /login and /auth/login patterns
            await page.wait_for_function(
                '''() => {
                    const url = window.location.href.toLowerCase();
                    return !url.includes('/login') && !url.includes('/auth/login');
                }''',
                timeout=timeout
            )
            
            # Additional checks for success indicators
            success_indicators = [
                # URL patterns that indicate success
                lambda: '/login' not in page.url.lower(),
                lambda: '/auth/login' not in page.url.lower(),
                lambda: 'dashboard' in page.url.lower(),
                lambda: 'home' in page.url.lower(),
                lambda: 'mutasi' in page.url.lower(),
                lambda: 'transaksi' in page.url.lower(),
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
                '[data-testid*="logout"]',
                'nav',  # Navigation bar usually present when logged in
                '.navbar',
                '.sidebar'
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
            current_url = page.url.lower()
            if '/login' not in current_url and '/auth/login' not in current_url:
                return True
            
            return False
            
        except Exception as e:
            self.log_warning("Error waiting for login success", error=str(e))
            # If URL changed, still consider it potentially successful
            current_url = page.url.lower()
            return '/login' not in current_url and '/auth/login' not in current_url
    
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
