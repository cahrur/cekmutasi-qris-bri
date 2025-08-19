"""
Main entry point for QRIS mutation scraper
"""
import asyncio
import sys
from typing import List
from .config import config
from .logger import setup_logger, LoggerMixin
from .storage.sqlite_cache import SQLiteCache
from .storage.session_store import SessionStore
from .scraper.browser import BrowserManager
from .scraper.auth import AuthManager
from .scraper.mutasi import MutasiScraper
from .httpclient import WebhookClient
from .scheduler import Scheduler, GracefulShutdown
from .models import Mutasi


class QRISMutationScraper(LoggerMixin):
    """Main scraper application class using Playwright"""
    
    def __init__(self):
        super().__init__()
        self.browser_manager = BrowserManager()
        self.auth_manager = AuthManager()
        self.mutasi_scraper = MutasiScraper()
        self.cache = SQLiteCache(config.CACHE_DB)
        self.session_store = SessionStore(config.SESSION_FILE)
        self.context = None
    
    async def initialize(self):
        """Initialize all components"""
        self.log_info("Initializing QRIS Mutation Scraper")
        
        # Load existing session if available
        storage_state = await self.session_store.load_session()
        
        # Start browser with session
        self.context = await self.browser_manager.start(storage_state)
        
        self.log_info("Scraper initialized successfully")
    

    
    async def ensure_authenticated(self) -> bool:
        """Ensure user is authenticated, login if necessary"""
        page = await self.browser_manager.new_page()
        
        try:
            # Check if already logged in
            if await self.auth_manager.is_logged_in(page):
                self.log_info("Already authenticated")
                return True
            
            # Perform login
            self.log_info("Authentication required, starting login")
            login_success = await self.auth_manager.login(page)
            
            if login_success:
                # Save session state
                if self.context:
                    await self.session_store.save_session(self.context)
                    self.log_info("Login successful, session saved")
                return True
            else:
                self.log_error("Login failed")
                return False
                
        finally:
            await page.close()
    
    async def scrape_mutations(self) -> List[Mutasi]:
        """Scrape mutations from the website"""
        page = await self.browser_manager.new_page()
        
        try:
            # Ensure we're authenticated
            if not await self.ensure_authenticated():
                raise Exception("Authentication failed")
            
            # Scrape mutations
            mutations = await self.mutasi_scraper.scrape_mutations(page)
            
            self.log_info(f"Scraped {len(mutations)} total mutations")
            return mutations
            
        finally:
            await page.close()
    
    async def filter_new_mutations(self, mutations: List[Mutasi]) -> List[Mutasi]:
        """Filter out mutations that have already been sent"""
        if not mutations:
            return []
        
        new_mutations = []
        
        for mutation in mutations:
            if not await self.cache.seen(mutation.id_ext):
                new_mutations.append(mutation)
        
        self.log_info(f"Found {len(new_mutations)} new mutations out of {len(mutations)} total")
        return new_mutations
    
    async def send_mutations(self, mutations: List[Mutasi]) -> bool:
        """Send mutations to webhook and mark as sent"""
        if not mutations:
            self.log_info("No mutations to send")
            return True
        
        async with WebhookClient() as client:
            # Test webhook connectivity first
            webhook_ok = await client.test_webhook()
            if not webhook_ok:
                self.log_error("Webhook test failed, skipping mutation sending")
                return False
            
            # Send mutations
            results = await client.post_mutations_batch(mutations)
            
            # Mark successful ones as sent
            for mutation in mutations:
                if mutation.id_ext not in results['failed_ids']:
                    await self.cache.mark(mutation.id_ext)
            
            success = results['failed'] == 0
            if success:
                self.log_info("All mutations sent successfully")
            else:
                self.log_warning(f"Some mutations failed to send", 
                               failed_count=results['failed'])
            
            return success
    
    async def run_scrape_job(self):
        """Run a complete scrape job"""
        try:
            self.log_info("Starting scrape job")
            
            # Scrape mutations
            mutations = await self.scrape_mutations()
            
            # Filter new mutations
            new_mutations = await self.filter_new_mutations(mutations)
            
            # Send new mutations
            if new_mutations:
                await self.send_mutations(new_mutations)
            else:
                self.log_info("No new mutations to send")
            
            self.log_info("Scrape job completed successfully")
            
        except Exception as e:
            self.log_error("Scrape job failed", error=e)
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        self.log_info("Cleaning up resources")
        
        try:
            await self.cache.close()
        except Exception as e:
            self.log_error("Error closing cache", error=e)
        
        try:
            if hasattr(self, 'context') and self.context:
                await self.context.close()
            if hasattr(self, 'browser_manager') and self.browser_manager:
                await self.browser_manager.cleanup()
        except Exception as e:
            self.log_error("Error during cleanup", error=e)


async def run_once():
    """Run scraper once and exit"""
    scraper = QRISMutationScraper()
    
    async with GracefulShutdown([scraper.cleanup]):
        await scraper.initialize()
        await scraper.run_scrape_job()


async def run_scheduler():
    """Run scraper with scheduler (continuous mode)"""
    scraper = QRISMutationScraper()
    
    async with GracefulShutdown([scraper.cleanup]):
        await scraper.initialize()
        
        # Create and start scheduler
        scheduler = Scheduler(scraper.run_scrape_job)
        await scheduler.start()


async def main():
    """Main entry point"""
    # Setup logging
    logger = setup_logger('qris_scraper')
    
    try:
        # Display startup info
        logger.info("=" * 60)
        logger.info("QRIS Mutation Scraper Starting")
        logger.info("=" * 60)
        logger.info(f"Base URL: {config.BASE_URL}")
        logger.info(f"Login URL: {config.LOGIN_URL}")
        logger.info(f"Mutation URL: {config.MUTASI_URL}")
        logger.info(f"Webhook URL: {config.WEBHOOK_URL}")
        logger.info(f"Poll Interval: {config.POLL_SECONDS} seconds")
        logger.info(f"Headless Mode: {config.HEADLESS}")
        logger.info(f"Timezone: {config.TIMEZONE}")
        logger.info("=" * 60)
        
        # Check command line arguments
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            if command in ['once', 'single', 'run-once']:
                logger.info("Running in single-run mode")
                await run_once()
                return
        
        # Default: run with scheduler
        logger.info("Running in scheduled mode")
        await run_scheduler()
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
    finally:
        logger.info("Application shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
