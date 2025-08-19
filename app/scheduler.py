"""
Scheduler for periodic mutation scraping with graceful shutdown
"""
import asyncio
import signal
from typing import Optional, Callable
from .config import config
from .logger import LoggerMixin


class Scheduler(LoggerMixin):
    """Manages periodic execution of scraping tasks"""
    
    def __init__(self, scrape_function: Callable):
        super().__init__()
        self.scrape_function = scrape_function
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        try:
            # Handle SIGINT (Ctrl+C) and SIGTERM
            for sig in [signal.SIGINT, signal.SIGTERM]:
                signal.signal(sig, self._signal_handler)
            
            self.log_info("Signal handlers setup completed")
            
        except Exception as e:
            self.log_warning("Could not setup signal handlers", error=str(e))
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        signal_name = signal.Signals(signum).name
        self.log_info(f"Received {signal_name}, initiating graceful shutdown")
        
        # Set shutdown event
        if hasattr(asyncio, '_get_running_loop') and asyncio._get_running_loop():
            asyncio.create_task(self._async_shutdown())
        else:
            # If no event loop is running, just set the flag
            self.running = False
    
    async def _async_shutdown(self):
        """Async shutdown handler"""
        self._shutdown_event.set()
        self.running = False
    
    async def start(self):
        """Start the scheduler"""
        if self.running:
            self.log_warning("Scheduler is already running")
            return
        
        self.running = True
        self.log_info("Starting scheduler", poll_interval=config.POLL_SECONDS)
        
        try:
            # Run initial scrape
            self.log_info("Running initial scrape")
            await self._run_scrape_safely()
            
            # Start periodic loop
            while self.running:
                try:
                    # Wait for next interval or shutdown signal
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=config.POLL_SECONDS
                    )
                    
                    # If we reach here, shutdown was requested
                    break
                    
                except asyncio.TimeoutError:
                    # Timeout is expected - time for next scrape
                    if self.running:
                        await self._run_scrape_safely()
                
        except Exception as e:
            self.log_error("Scheduler error", error=e)
            raise
        finally:
            self.running = False
            self.log_info("Scheduler stopped")
    
    async def _run_scrape_safely(self):
        """Run scrape function with error handling"""
        try:
            self.log_info("Starting scheduled scrape")
            await self.scrape_function()
            self.log_info("Scheduled scrape completed successfully")
            
        except Exception as e:
            self.log_error("Error during scheduled scrape", error=e)
            # Don't re-raise - scheduler should continue running
    
    async def stop(self):
        """Stop the scheduler gracefully"""
        if not self.running:
            self.log_info("Scheduler is not running")
            return
        
        self.log_info("Stopping scheduler")
        self.running = False
        self._shutdown_event.set()
        
        # Wait for current task to complete if running
        if self.task and not self.task.done():
            try:
                await asyncio.wait_for(self.task, timeout=30.0)
            except asyncio.TimeoutError:
                self.log_warning("Scheduler task did not complete within timeout")
                self.task.cancel()
    
    async def run_once(self):
        """Run scrape function once"""
        self.log_info("Running one-time scrape")
        await self._run_scrape_safely()


class GracefulShutdown:
    """Context manager for graceful shutdown of resources"""
    
    def __init__(self, cleanup_functions: Optional[list] = None):
        self.cleanup_functions = cleanup_functions or []
        logger_mixin = LoggerMixin()
        self.logger = logger_mixin.logger
    
    def add_cleanup(self, func: Callable):
        """Add cleanup function"""
        self.cleanup_functions.append(func)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources"""
        self.logger.info("Running cleanup functions")
        
        for cleanup_func in self.cleanup_functions:
            try:
                if asyncio.iscoroutinefunction(cleanup_func):
                    await cleanup_func()
                else:
                    cleanup_func()
            except Exception as e:
                self.logger.error(f"Error in cleanup function: {e}")
        
        self.logger.info("Cleanup completed")
