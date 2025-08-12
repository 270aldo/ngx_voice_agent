"""
Database Connection Pool Configuration for Production

Optimized connection pooling for Supabase/PostgreSQL to handle
high concurrent loads in production environment.
"""

import asyncio
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import asyncpg
from urllib.parse import urlparse
import logging

from src.config.settings import settings
from src.core.constants import DatabaseConstants

logger = logging.getLogger(__name__)


class DatabaseConnectionPool:
    """Manages database connection pooling for production scalability."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.config = self._get_pool_config()
        
    def _get_pool_config(self) -> Dict[str, Any]:
        """Get optimized pool configuration based on environment."""
        base_config = {
            "min_size": DatabaseConstants.MIN_POOL_SIZE,  # 5
            "max_size": DatabaseConstants.MAX_POOL_SIZE,  # 20
            "max_queries": 50000,
            "max_inactive_connection_lifetime": 300.0,
            "timeout": DatabaseConstants.CONNECTION_TIMEOUT,  # 30
            "command_timeout": 60.0,
            "statement_cache_size": 20,
            "max_cached_statement_lifetime": 3600.0,
        }
        
        # Adjust for production
        if settings.is_production:
            base_config.update({
                "min_size": 10,  # Higher minimum for production
                "max_size": 50,  # Much higher max for production
                "max_queries": 100000,
                "max_inactive_connection_lifetime": 600.0,
            })
        
        # Adjust for beta testing (balanced approach)
        elif settings.environment == "staging":
            base_config.update({
                "min_size": 8,
                "max_size": 30,
                "max_queries": 75000,
            })
            
        return base_config
    
    async def initialize(self, database_url: Optional[str] = None) -> None:
        """Initialize the connection pool."""
        try:
            # Use provided URL or get from settings
            db_url = database_url or settings.get_database_url()
            
            if not db_url:
                logger.warning("No database URL configured, skipping pool initialization")
                return
            
            # Parse and validate database URL
            parsed = urlparse(db_url)
            if parsed.scheme not in ["postgresql", "postgres"]:
                raise ValueError(f"Invalid database scheme: {parsed.scheme}")
            
            # Create the connection pool
            self.pool = await asyncpg.create_pool(
                db_url,
                **self.config
            )
            
            # Test the pool with a simple query
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            logger.info(
                f"Database pool initialized successfully "
                f"(min={self.config['min_size']}, max={self.config['max_size']})"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close(self) -> None:
        """Close the connection pool gracefully."""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        
        async with self.pool.acquire() as conn:
            yield conn
    
    async def execute(self, query: str, *args, timeout: Optional[float] = None) -> str:
        """Execute a query using a pooled connection."""
        async with self.acquire() as conn:
            return await conn.execute(query, *args, timeout=timeout)
    
    async def fetch(self, query: str, *args, timeout: Optional[float] = None) -> list:
        """Fetch results using a pooled connection."""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args, timeout=timeout)
    
    async def fetchrow(self, query: str, *args, timeout: Optional[float] = None) -> Optional[dict]:
        """Fetch a single row using a pooled connection."""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args, timeout=timeout)
    
    async def fetchval(self, query: str, *args, timeout: Optional[float] = None) -> Any:
        """Fetch a single value using a pooled connection."""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args, timeout=timeout)
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get current pool statistics."""
        if not self.pool:
            return {"status": "not_initialized"}
        
        return {
            "status": "active",
            "size": self.pool.get_size(),
            "free_connections": self.pool.get_idle_size(),
            "used_connections": self.pool.get_size() - self.pool.get_idle_size(),
            "min_size": self.config["min_size"],
            "max_size": self.config["max_size"],
        }
    
    async def health_check(self) -> bool:
        """Perform a health check on the connection pool."""
        try:
            if not self.pool:
                return False
            
            # Try to acquire a connection and run a simple query
            async with asyncio.timeout(5):
                async with self.acquire() as conn:
                    result = await conn.fetchval("SELECT 1")
                    return result == 1
                    
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global connection pool instance
db_pool = DatabaseConnectionPool()


async def initialize_db_pool(database_url: Optional[str] = None) -> None:
    """Initialize the global database connection pool."""
    await db_pool.initialize(database_url)


async def close_db_pool() -> None:
    """Close the global database connection pool."""
    await db_pool.close()


def get_db_pool() -> DatabaseConnectionPool:
    """Get the global database connection pool instance."""
    return db_pool