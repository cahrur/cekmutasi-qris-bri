"""
HTTP client for webhook posting with retry and backoff
"""
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from .config import config
from .logger import LoggerMixin
from .models import Mutasi

if TYPE_CHECKING:
    import httpx
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
else:
    try:
        import httpx
    except ImportError:
        httpx = None

    try:
        from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    except ImportError:
        def retry(*args, **kwargs):
            def decorator(func):
                return func
            return decorator
        stop_after_attempt = wait_exponential = retry_if_exception_type = None


class WebhookClient(LoggerMixin):
    """HTTP client for posting mutation data to webhook"""
    
    def __init__(self):
        super().__init__()
        if httpx is None:
            raise ImportError("httpx is required but not installed. Run: pip install httpx")
        self.client: Optional['httpx.AsyncClient'] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        if httpx is None:
            raise ImportError("httpx is required but not installed")
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),  # 30 second timeout
            headers={
                'User-Agent': config.USER_AGENT
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
    
    async def post_mutation(self, mutation: Mutasi) -> bool:
        """
        Post a single mutation to webhook with retry logic
        Returns True if successful, False otherwise
        """
        import asyncio
        
        for attempt in range(1):  # Single attempt only (no retry for webhook)
            try:
                payload = mutation.to_webhook_payload()
                
                self.log_info("Posting mutation to webhook", 
                             id_ext=mutation.id_ext, 
                             webhook_url=config.WEBHOOK_URL,
                             attempt=attempt + 1)
                
                if self.client is None:
                    raise RuntimeError("HTTP client not initialized")
                
                # Kirim sebagai form-data murni sesuai dokumentasi
                response = await self.client.post(
                    config.WEBHOOK_URL,
                    data=payload
                )
                
                # Raise for HTTP error status codes
                response.raise_for_status()
                
                self.log_info("Mutation posted successfully", 
                             id_ext=mutation.id_ext, 
                             status_code=response.status_code)
                
                return True
                
            except Exception as e:
                if httpx and isinstance(e, httpx.HTTPStatusError):
                    self.log_error("HTTP error posting mutation", 
                                  error=e, 
                                  id_ext=mutation.id_ext,
                                  status_code=e.response.status_code,
                                  response_text=e.response.text if hasattr(e.response, 'text') else 'N/A',
                                  attempt=attempt + 1)
                    return False  # No retry
                elif httpx and isinstance(e, httpx.RequestError):
                    self.log_error("Request error posting mutation", 
                                  error=e, 
                                  id_ext=mutation.id_ext,
                                  attempt=attempt + 1)
                    return False  # No retry
                else:
                    self.log_error("Unexpected error posting mutation", 
                                  error=e, 
                                  id_ext=mutation.id_ext,
                                  attempt=attempt + 1)
                    return False
                
                # No retry logic needed anymore
        
        return False
    
    async def post_mutations_batch(self, mutations: List[Mutasi]) -> Dict[str, Any]:
        """
        Post multiple mutations and return results summary
        """
        results = {
            'total': len(mutations),
            'successful': 0,
            'failed': 0,
            'failed_ids': []
        }
        
        if not mutations:
            self.log_info("No mutations to post")
            return results
        
        self.log_info(f"Posting {len(mutations)} mutations to webhook")
        
        for mutation in mutations:
            try:
                success = await self.post_mutation(mutation)
                if success:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                    results['failed_ids'].append(mutation.id_ext)
                    
            except Exception as e:
                self.log_error("Failed to post mutation in batch", 
                              error=e, 
                              id_ext=mutation.id_ext)
                results['failed'] += 1
                results['failed_ids'].append(mutation.id_ext)
        
        self.log_info("Batch posting completed", 
                     total=results['total'],
                     successful=results['successful'],
                     failed=results['failed'])
        
        return results
    
    async def test_webhook(self) -> bool:
        """Test webhook connectivity with a simple ping"""
        try:
            test_payload = {
                "test": True,
                "message": "Webhook connectivity test",
                "timestamp": "2024-01-01T00:00:00+07:00"
            }
            
            self.log_info("Testing webhook connectivity", webhook_url=config.WEBHOOK_URL)
            
            if self.client is None:
                raise RuntimeError("HTTP client not initialized")
                
            response = await self.client.post(
                config.WEBHOOK_URL,
                json=test_payload
            )
            
            # Accept both 2xx and 4xx (some webhooks return 400 for test data)
            if 200 <= response.status_code < 500:
                self.log_info("Webhook test successful", status_code=response.status_code)
                return True
            else:
                self.log_warning("Webhook test returned unexpected status", 
                               status_code=response.status_code)
                return False
                
        except Exception as e:
            self.log_error("Webhook test failed", error=e)
            return False
