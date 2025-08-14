"""
Core dependencies for dependency injection - MIGRATED TO CONSOLIDATED CACHE.

This module provides centralized dependency management for the application,
including database connections, cache services, and other shared resources.
Updated to use the consolidated CacheService with backward compatibility.
"""

from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from src.services.cache_service import get_cache_instance, CacheService
from src.services.cache_compatibility import (
    get_redis_cache_compat, 
    get_ngx_cache_manager_compat,
    log_cache_migration_progress
)
from src.config import settings
from src.integrations.supabase.client import supabase_client
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)

# Global instances
_cache_service: Optional[CacheService] = None
_ngx_cache_manager = None
_redis_cache = None


async def get_redis_cache():
    """
    Get Redis cache service instance (with compatibility layer).
    
    Returns:
        Redis cache service or None if not available
    """
    global _redis_cache
    
    if _redis_cache is None:
        try:
            if settings.use_consolidated_cache:
                _redis_cache = await get_cache_instance()
                if _redis_cache and not hasattr(get_redis_cache, '_logged'):
                    logger.info("Consolidated cache service initialized")
                    get_redis_cache._logged = True
            else:
                _redis_cache = await get_redis_cache_compat()
                if _redis_cache and not hasattr(get_redis_cache, '_logged'):
                    logger.info("Legacy Redis cache service initialized")
                    get_redis_cache._logged = True
        except Exception as e:
            logger.error(f"Failed to get Redis cache: {e}")
            _redis_cache = None
    
    return _redis_cache


async def get_ngx_cache_manager():
    """
    Get NGX cache manager instance (with compatibility layer).
    
    Returns:
        NGX cache manager or None if not available
    """
    global _ngx_cache_manager
    
    if _ngx_cache_manager is None:
        try:
            if settings.use_consolidated_cache:
                cache_service = await get_cache_instance()
                if cache_service:
                    _ngx_cache_manager = cache_service  # Use consolidated cache directly
                    logger.info("NGX cache manager initialized with consolidated cache")
            else:
                _ngx_cache_manager = await get_ngx_cache_manager_compat()
                logger.info("NGX cache manager initialized with compatibility layer")
            
            # Warm up cache with frequently accessed data
            if _ngx_cache_manager:
                try:
                    warmers = []  # Add specific warmers as needed
                    if hasattr(_ngx_cache_manager, 'warm_cache') and callable(getattr(_ngx_cache_manager, 'warm_cache')):
                        if settings.use_consolidated_cache:
                            await _ngx_cache_manager.warm_cache(warmers)
                            logger.info("Consolidated cache warmed up")
                        else:
                            stats = await _ngx_cache_manager.warm_cache()
                            logger.info(f"Legacy cache warmed up with {stats.get('total', 0)} entries")
                except Exception as e:
                    logger.error(f"Failed to warm cache: {e}")
        except Exception as e:
            logger.error(f"Failed to get NGX cache manager: {e}")
            _ngx_cache_manager = None
    
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
    
    # Log cache migration status
    log_cache_migration_progress()
    
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
    global _redis_cache, _ngx_cache_manager, _cache_service
    
    logger.info("Cleaning up application dependencies")
    
    # Close cache connections
    if _redis_cache:
        try:
            if hasattr(_redis_cache, 'close'):
                await _redis_cache.close()
                logger.info("Redis cache closed")
        except Exception as e:
            logger.error(f"Error closing Redis cache: {e}")
    
    if _cache_service:
        try:
            await _cache_service.close()
            logger.info("Consolidated cache closed")
        except Exception as e:
            logger.error(f"Error closing consolidated cache: {e}")
    
    _redis_cache = None
    _ngx_cache_manager = None
    _cache_service = None
    
    logger.info("All dependencies cleaned up")


class DependencyProvider:
    """
    Dependency provider for services.
    
    This class can be used to inject dependencies into services
    that need access to cache, database, etc.
    """
    
    def __init__(self):
        self._cache = None
        self._redis = None
        self._db = None
    
    async def initialize(self):
        """Initialize all dependencies."""
        self._redis = await get_redis_cache()
        self._cache = await get_ngx_cache_manager()
        self._db = supabase_client
    
    @property
    def cache(self):
        """Get cache manager."""
        return self._cache
    
    @property
    def redis(self):
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
                if hasattr(self._redis, 'health_check'):
                    cache_health = await self._redis.health_check()
                    if isinstance(cache_health, dict):
                        health["cache"] = "healthy" if cache_health.get("healthy") else "unhealthy"
                    else:
                        health["cache"] = "healthy" if cache_health else "unhealthy"
                else:
                    health["cache"] = "healthy"  # Assume healthy if no health_check method
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

async def get_cache_dependency():
    """
    FastAPI dependency for cache injection.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(cache = Depends(get_cache_dependency)):
            # Use cache
    """
    return await get_ngx_cache_manager()


async def get_redis_dependency():
    """
    FastAPI dependency for Redis cache injection.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(redis = Depends(get_redis_dependency)):
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