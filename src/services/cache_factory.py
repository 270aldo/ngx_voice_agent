"""
Cache Factory Module - Centralized cache initialization to avoid circular dependencies.
"""

import logging
from typing import Optional
from src.services.redis_cache_service import RedisCacheService
from src.services.redis_mock import MockRedisCacheService
from src.config import settings

logger = logging.getLogger(__name__)

# Global cache instance
_cache_instance: Optional[RedisCacheService] = None


async def create_cache_instance() -> RedisCacheService:
    """Create a new cache instance based on configuration."""
    global _cache_instance
    
    if settings.redis_mock_enabled:
        logger.info("Using mock Redis cache service")
        _cache_instance = MockRedisCacheService()
    else:
        logger.info("Using real Redis cache service")
        _cache_instance = RedisCacheService(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            ssl=settings.redis_ssl,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
    
    # Initialize the cache
    await _cache_instance.initialize()
    
    return _cache_instance


async def get_cache_instance() -> Optional[RedisCacheService]:
    """Get the global cache instance, creating it if necessary."""
    global _cache_instance
    
    if _cache_instance is None:
        try:
            _cache_instance = await create_cache_instance()
        except Exception as e:
            logger.error(f"Failed to create cache instance: {e}")
            return None
    
    return _cache_instance


def get_cache_sync() -> Optional[RedisCacheService]:
    """Get the cache instance synchronously (returns None if not initialized)."""
    return _cache_instance


async def close_cache() -> None:
    """Close the cache connection and cleanup."""
    global _cache_instance
    
    if _cache_instance:
        try:
            await _cache_instance.close()
            logger.info("Cache connection closed")
        except Exception as e:
            logger.error(f"Error closing cache: {e}")
        finally:
            _cache_instance = None