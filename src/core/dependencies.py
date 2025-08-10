"""
Core dependencies for dependency injection.

This module provides centralized dependency management for the application,
including database connections, cache services, and other shared resources.
"""

from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from src.services.cache_factory import get_cache_instance, RedisCacheService
from src.services.ngx_cache_manager import NGXCacheManager
from src.integrations.supabase.client import supabase_client
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)

# Global instances
_ngx_cache_manager: Optional[NGXCacheManager] = None


async def get_redis_cache() -> Optional[RedisCacheService]:
    """
    Get Redis cache service instance.
    
    Returns:
        Redis cache service or None if not available
    """
    try:
        cache = await get_cache_instance()
        if cache and not hasattr(get_redis_cache, '_logged'):
            logger.info("Redis cache service initialized")
            get_redis_cache._logged = True
        return cache
    except Exception as e:
        logger.error(f"Failed to get Redis cache: {e}")
        return None


async def get_ngx_cache_manager() -> Optional[NGXCacheManager]:
    """
    Get NGX cache manager instance.
    
    Returns:
        NGX cache manager or None if not available
    """
    global _ngx_cache_manager
    
    if _ngx_cache_manager is None:
        redis_cache = await get_redis_cache()
        if redis_cache:
            _ngx_cache_manager = NGXCacheManager(redis_cache)
            logger.info("NGX cache manager initialized")
            
            # Warm up cache with frequently accessed data
            try:
                stats = await _ngx_cache_manager.warm_cache()
                logger.info(f"Cache warmed up with {stats['total']} entries")
            except Exception as e:
                logger.error(f"Failed to warm cache: {e}")
    
    return _ngx_cache_manager


@asynccontextmanager
async def get_database():
    """
    Get database connection.
    
    Yields:
        Database client
    """
    client = None
    try:
        client = supabase_client
        yield client
    finally:
        # Supabase client doesn't need explicit cleanup
        pass


async def initialize_dependencies():
    """
    Initialize all application dependencies.
    
    This should be called during application startup.
    """
    logger.info("Initializing application dependencies")
    
    # Initialize cache
    cache = await get_redis_cache()
    if cache:
        cache_manager = await get_ngx_cache_manager()
        if cache_manager:
            logger.info("Cache services initialized successfully")
    else:
        logger.warning("Running without cache - Redis not available")
    
    # Initialize other dependencies as needed
    logger.info("All dependencies initialized")


async def cleanup_dependencies():
    """
    Cleanup all application dependencies.
    
    This should be called during application shutdown.
    """
    global _redis_cache, _ngx_cache_manager
    
    logger.info("Cleaning up application dependencies")
    
    # Close cache connections
    if _redis_cache:
        try:
            await _redis_cache.close()
            logger.info("Redis cache closed")
        except Exception as e:
            logger.error(f"Error closing Redis cache: {e}")
    
    _redis_cache = None
    _ngx_cache_manager = None
    
    logger.info("All dependencies cleaned up")


class DependencyProvider:
    """
    Dependency provider for services.
    
    This class can be used to inject dependencies into services
    that need access to cache, database, etc.
    """
    
    def __init__(self):
        self._cache: Optional[NGXCacheManager] = None
        self._redis: Optional[RedisCacheService] = None
        self._db = None
    
    async def initialize(self):
        """Initialize all dependencies."""
        self._redis = await get_redis_cache()
        self._cache = await get_ngx_cache_manager()
        self._db = supabase_client
    
    @property
    def cache(self) -> Optional[NGXCacheManager]:
        """Get cache manager."""
        return self._cache
    
    @property
    def redis(self) -> Optional[RedisCacheService]:
        """Get Redis cache service."""
        return self._redis
    
    @property
    def db(self):
        """Get database client."""
        return self._db
    
    async def health_check(self) -> dict:
        """
        Check health of all dependencies.
        
        Returns:
            Health status of each dependency
        """
        health = {
            "cache": "unavailable",
            "database": "unavailable"
        }
        
        # Check cache
        if self._redis:
            try:
                cache_health = await self._redis.health_check()
                health["cache"] = "healthy" if cache_health["healthy"] else "unhealthy"
            except Exception as e:
                health["cache"] = f"error: {str(e)}"
        
        # Check database
        if self._db:
            try:
                # Simple query to check connection
                result = self._db.table("conversations").select("id").limit(1).execute()
                health["database"] = "healthy"
            except Exception as e:
                health["database"] = f"error: {str(e)}"
        
        return health


# FastAPI dependency injection

async def get_cache_dependency() -> Optional[NGXCacheManager]:
    """
    FastAPI dependency for cache injection.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(cache: NGXCacheManager = Depends(get_cache_dependency)):
            # Use cache
    """
    return await get_ngx_cache_manager()


async def get_redis_dependency() -> Optional[RedisCacheService]:
    """
    FastAPI dependency for Redis cache injection.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(redis: RedisCacheService = Depends(get_redis_dependency)):
            # Use Redis
    """
    return await get_redis_cache()


async def get_db_dependency():
    """
    FastAPI dependency for database injection.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(db = Depends(get_db_dependency)):
            # Use database
    """
    async with get_database() as db:
        yield db