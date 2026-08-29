#!/usr/bin/env python3
"""
Main entry point untuk QRIS scraper dengan system cron
Simplified untuk system cron usage - no internal scheduler
"""
import asyncio
import sys
from datetime import datetime

import pytz

from .config import config
from .logger import setup_logger
from .main import QRISMutationScraper


class QRISCronApp:
    """QRIS Scraper untuk system cron usage"""
    
    def __init__(self):
        self.logger = setup_logger('qris_cron')
    
    async def run_single_job(self):
        """Run single scraper job - designed for system cron"""
        try:
            self.logger.info("=== QRIS Scraper Job Started ===")

            # Skip entirely during quiet hours, before starting a browser.
            if config.is_quiet_time():
                now = datetime.now(pytz.timezone(config.TIMEZONE))
                self.logger.info(
                    "Jam jeda aktif, scraping dilewati | sekarang=%s jeda=%s-%s (%s)",
                    now.strftime('%H:%M'),
                    config.QUIET_HOURS_START.strftime('%H:%M'),
                    config.QUIET_HOURS_END.strftime('%H:%M'),
                    config.TIMEZONE,
                )
                self.logger.info("=== QRIS Scraper Job Skipped ===")
                return

            # Create fresh scraper instance
            scraper = QRISMutationScraper()
            
            try:
                await scraper.initialize()
                await scraper.run_scrape_job()
                self.logger.info("=== QRIS Scraper Job Completed ===")
            finally:
                await scraper.cleanup()
                
        except Exception as e:
            self.logger.error(f"Scraper job failed: {e}")
            sys.exit(1)
    
    def show_status(self):
        """Show current configuration and status"""
        self.logger.info("QRIS Scraper Configuration")
        self.logger.info("=" * 60)
        self.logger.info(f"Base URL: {config.BASE_URL}")
        self.logger.info(f"Webhook URL: {config.WEBHOOK_URL}")
        self.logger.info(f"Headless Mode: {config.HEADLESS}")
        self.logger.info(f"Timezone: {config.TIMEZONE}")
        if config.QUIET_HOURS_START and config.QUIET_HOURS_END:
            self.logger.info(
                f"Quiet hours: {config.QUIET_HOURS_START.strftime('%H:%M')}"
                f"-{config.QUIET_HOURS_END.strftime('%H:%M')} "
                f"(sekarang {'AKTIF - tidak scraping' if config.is_quiet_time() else 'tidak aktif'})"
            )
        else:
            self.logger.info("Quiet hours: nonaktif")
        self.logger.info("=" * 60)


async def main():
    """Main entry point"""
    app = QRISCronApp()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command in ['once', 'single', 'run-once', 'cron']:
            await app.run_single_job()
        elif command in ['status', 'config']:
            app.show_status()
        else:
            print("Available commands:")
            print("  once/single     - Run scraper once (for system cron)")
            print("  status/config   - Show configuration")
            sys.exit(1)
    else:
        # Default: run single job (for system cron)
        await app.run_single_job()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 QRIS Scraper stopped by user")
    except Exception as e:
        print(f"\n💥 Application error: {e}")
        sys.exit(1)