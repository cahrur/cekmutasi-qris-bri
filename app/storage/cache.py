"""
Cache interface for tracking sent mutation IDs
"""
from abc import ABC, abstractmethod


class CacheInterface(ABC):
    """Abstract interface for caching sent mutation IDs"""
    
    @abstractmethod
    async def seen(self, id_ext: str) -> bool:
        """Check if ID has been seen before"""
        pass
    
    @abstractmethod
    async def mark(self, id_ext: str) -> None:
        """Mark ID as seen"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close cache connection"""
        pass
