"""
SQLite implementation of cache for tracking sent mutation IDs
"""
import sqlite3
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from .cache import CacheInterface
from ..logger import LoggerMixin

if TYPE_CHECKING:
    import aiosqlite
else:
    try:
        import aiosqlite
    except ImportError:
        aiosqlite = None


class SQLiteCache(CacheInterface, LoggerMixin):
    """SQLite-based cache for tracking sent mutation IDs"""
    
    def __init__(self, db_path: str):
        super().__init__()
        if aiosqlite is None:
            raise ImportError("aiosqlite is required but not installed. Run: pip install aiosqlite")
        
        self.db_path = Path(db_path)
        self.connection: Optional['aiosqlite.Connection'] = None
        
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def _init_db(self):
        """Initialize database with required tables"""
        if self.connection is None:
            if aiosqlite is None:
                raise ImportError("aiosqlite is required but not installed")
            self.connection = await aiosqlite.connect(str(self.db_path))
            
            # Create table if not exists
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS sent_ids (
                    id_ext TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await self.connection.commit()
            
            self.log_info("SQLite cache initialized", db_path=str(self.db_path))
    
    async def seen(self, id_ext: str) -> bool:
        """Check if ID has been seen before"""
        await self._init_db()
        
        if self.connection is None:
            raise RuntimeError("Database connection not initialized")
        
        cursor = await self.connection.execute(
            "SELECT 1 FROM sent_ids WHERE id_ext = ?", (id_ext,)
        )
        result = await cursor.fetchone()
        await cursor.close()
        
        seen = result is not None
        self.log_debug(f"Checked ID existence", id_ext=id_ext, seen=seen)
        return seen
    
    async def mark(self, id_ext: str) -> None:
        """Mark ID as seen"""
        await self._init_db()
        
        if self.connection is None:
            raise RuntimeError("Database connection not initialized")
        
        try:
            await self.connection.execute(
                "INSERT OR IGNORE INTO sent_ids (id_ext) VALUES (?)", (id_ext,)
            )
            await self.connection.commit()
            self.log_debug("Marked ID as sent", id_ext=id_ext)
        except Exception as e:
            self.log_error("Failed to mark ID", error=e, id_ext=id_ext)
            raise
    
    async def close(self) -> None:
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.log_info("SQLite cache connection closed")
    
    async def get_count(self) -> int:
        """Get total count of cached IDs"""
        await self._init_db()
        
        if self.connection is None:
            raise RuntimeError("Database connection not initialized")
        
        cursor = await self.connection.execute("SELECT COUNT(*) FROM sent_ids")
        result = await cursor.fetchone()
        await cursor.close()
        
        return result[0] if result else 0
    
    async def cleanup_old(self, days: int = 30) -> int:
        """Remove old entries older than specified days"""
        await self._init_db()
        
        if self.connection is None:
            raise RuntimeError("Database connection not initialized")
        
        cursor = await self.connection.execute(
            "DELETE FROM sent_ids WHERE created_at < datetime('now', '-{} days')".format(days)
        )
        await self.connection.commit()
        
        deleted_count = cursor.rowcount
        await cursor.close()
        
        if deleted_count > 0:
            self.log_info(f"Cleaned up old cache entries", deleted_count=deleted_count, days=days)
        
        return deleted_count
