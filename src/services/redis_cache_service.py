"""
Redis caching service for NGX Voice Sales Agent.

This service provides a high-performance caching layer for frequently accessed data,
reducing database load and improving response times.
"""

import json
import hashlib
import asyncio
from typing import Any, Optional, Union, List, Dict, Callable, TypeVar
from datetime import timedelta
from functools import wraps
import pickle
import logging

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from src.config import settings
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)

T = TypeVar('T')


class RedisCacheService:
    """
    Redis caching service with async support.
    
    Features:
    - Async/await support
    - Connection pooling
    - Automatic serialization/deserialization
    - TTL support
    - Namespace support for key organization
    - Circuit breaker pattern for resilience
    - Metrics and monitoring
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        pool_size: int = 10,
        decode_responses: bool = False,
        namespace: str = "ngx",
        default_ttl: int = 3600
    ):
        """
        Initialize Redis cache service.
        
        Args:
            url: Redis connection URL
            pool_size: Connection pool size
            decode_responses: Whether to decode responses as strings
            namespace: Key namespace prefix
            default_ttl: Default TTL in seconds
        """
        self.url = url or settings.redis_url
        self.pool_size = pool_size or settings.redis_pool_size
        self.decode_responses = decode_responses
        self.namespace = namespace
        self.default_ttl = default_ttl
        
        # Connection management
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._connected = False
        
        # Circuit breaker
        self._failure_count = 0
        self._max_failures = 5
        self._circuit_open = False
        self._circuit_open_until = 0
        
        # Metrics
        self._hits = 0
        self._misses = 0
        self._errors = 0
    
    async def initialize(self) -> None:
        """Initialize Redis connection."""
        try:
            self._pool = ConnectionPool.from_url(
                self.url,
                max_connections=self.pool_size,
                decode_responses=self.decode_responses
            )
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            await self._client.ping()
            self._connected = True
            
            logger.info("Redis cache service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            self._connected = False
            raise
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
        self._connected = False
        logger.info("Redis cache service closed")
    
    def _make_key(self, key: str) -> str:
        """Create namespaced key."""
        return f"{self.namespace}:{key}"
    
    async def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker allows operation."""
        if not self._circuit_open:
            return True
        
        # Check if circuit can be closed
        import time
        if time.time() > self._circuit_open_until:
            self._circuit_open = False
            self._failure_count = 0
            logger.info("Circuit breaker closed")
            return True
        
        return False
    
    async def _handle_error(self, error: Exception) -> None:
        """Handle Redis errors with circuit breaker."""
        self._errors += 1
        self._failure_count += 1
        
        if self._failure_count >= self._max_failures:
            import time
            self._circuit_open = True
            self._circuit_open_until = time.time() + 30  # 30 second timeout
            logger.error(f"Circuit breaker opened due to {self._failure_count} failures")
        
        logger.error(f"Redis error: {error}")
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        if not self._connected or not await self._check_circuit_breaker():
            return default
        
        try:
            full_key = self._make_key(key)
            value = await self._client.get(full_key)
            
            if value is None:
                self._misses += 1
                return default
            
            self._hits += 1
            
            # Try to deserialize JSON first, then pickle
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                try:
                    return pickle.loads(value)
                except (pickle.UnpicklingError, TypeError, AttributeError) as e:
                    logger.debug(f"Failed to unpickle value for key {key}: {e}")
                    return value
                    
        except Exception as e:
            await self._handle_error(e)
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (None = use default)
            nx: Only set if key doesn't exist
            xx: Only set if key exists
            
        Returns:
            True if successful
        """
        if not self._connected or not await self._check_circuit_breaker():
            return False
        
        try:
            full_key = self._make_key(key)
            ttl = ttl or self.default_ttl
            
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            else:
                try:
                    serialized = json.dumps(value)
                except (TypeError, ValueError):
                    serialized = pickle.dumps(value)
            
            # Set with options
            result = await self._client.set(
                full_key,
                serialized,
                ex=ttl,
                nx=nx,
                xx=xx
            )
            
            return bool(result)
            
        except Exception as e:
            await self._handle_error(e)
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted
        """
        if not self._connected or not await self._check_circuit_breaker():
            return False
        
        try:
            full_key = self._make_key(key)
            result = await self._client.delete(full_key)
            return bool(result)
            
        except Exception as e:
            await self._handle_error(e)
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
        """
        if not self._connected or not await self._check_circuit_breaker():
            return False
        
        try:
            full_key = self._make_key(key)
            return bool(await self._client.exists(full_key))
            
        except Exception as e:
            await self._handle_error(e)
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set TTL for existing key.
        
        Args:
            key: Cache key
            ttl: TTL in seconds
            
        Returns:
            True if TTL was set
        """
        if not self._connected or not await self._check_circuit_breaker():
            return False
        
        try:
            full_key = self._make_key(key)
            return bool(await self._client.expire(full_key, ttl))
            
        except Exception as e:
            await self._handle_error(e)
            return False
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values at once.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dict of key-value pairs
        """
        if not self._connected or not await self._check_circuit_breaker():
            return {}
        
        try:
            full_keys = [self._make_key(k) for k in keys]
            values = await self._client.mget(full_keys)
            
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        try:
                            result[key] = pickle.loads(value)
                        except (pickle.UnpicklingError, TypeError, AttributeError) as e:
                            logger.debug(f"Failed to deserialize value for key {key}: {e}")
                            result[key] = value
            
            return result
            
        except Exception as e:
            await self._handle_error(e)
            return {}
    
    async def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Set multiple values at once.
        
        Args:
            mapping: Dict of key-value pairs
            ttl: TTL for all keys
            
        Returns:
            True if successful
        """
        if not self._connected or not await self._check_circuit_breaker():
            return False
        
        try:
            # Use pipeline for atomic operation
            async with self._client.pipeline() as pipe:
                for key, value in mapping.items():
                    full_key = self._make_key(key)
                    
                    # Serialize value
                    if isinstance(value, (dict, list)):
                        serialized = json.dumps(value)
                    else:
                        try:
                            serialized = json.dumps(value)
                        except (TypeError, ValueError) as e:
                            logger.debug(f"JSON serialization failed for key {key}, using pickle: {e}")
                            serialized = pickle.dumps(value)
                    
                    pipe.set(full_key, serialized, ex=ttl or self.default_ttl)
                
                await pipe.execute()
            
            return True
            
        except Exception as e:
            await self._handle_error(e)
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment counter.
        
        Args:
            key: Counter key
            amount: Increment amount
            
        Returns:
            New counter value or None on error
        """
        if not self._connected or not await self._check_circuit_breaker():
            return None
        
        try:
            full_key = self._make_key(key)
            return await self._client.incrby(full_key, amount)
            
        except Exception as e:
            await self._handle_error(e)
            return None
    
    async def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Decrement counter.
        
        Args:
            key: Counter key
            amount: Decrement amount
            
        Returns:
            New counter value or None on error
        """
        if not self._connected or not await self._check_circuit_breaker():
            return None
        
        try:
            full_key = self._make_key(key)
            return await self._client.decrby(full_key, amount)
            
        except Exception as e:
            await self._handle_error(e)
            return None
    
    async def clear_namespace(self) -> int:
        """
        Clear all keys in namespace.
        
        Returns:
            Number of keys deleted
        """
        if not self._connected or not await self._check_circuit_breaker():
            return 0
        
        try:
            pattern = f"{self.namespace}:*"
            cursor = 0
            deleted = 0
            
            while True:
                cursor, keys = await self._client.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                
                if keys:
                    deleted += await self._client.delete(*keys)
                
                if cursor == 0:
                    break
            
            logger.info(f"Cleared {deleted} keys from namespace {self.namespace}")
            return deleted
            
        except Exception as e:
            await self._handle_error(e)
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0
        
        return {
            "connected": self._connected,
            "hits": self._hits,
            "misses": self._misses,
            "errors": self._errors,
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "circuit_breaker_open": self._circuit_open,
            "failure_count": self._failure_count
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health."""
        try:
            if not self._connected:
                return {"status": "disconnected", "healthy": False}
            
            # Ping Redis
            start = asyncio.get_event_loop().time()
            await self._client.ping()
            latency = (asyncio.get_event_loop().time() - start) * 1000
            
            # Get info
            info = await self._client.info()
            
            return {
                "status": "connected",
                "healthy": True,
                "latency_ms": round(latency, 2),
                "version": info.get("redis_version", "unknown"),
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                **self.get_stats()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "healthy": False,
                "error": str(e),
                **self.get_stats()
            }


def cached(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    key_func: Optional[Callable] = None,
    cache_none: bool = False
):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Cache TTL in seconds
        key_prefix: Key prefix (defaults to function name)
        key_func: Custom key generation function
        cache_none: Whether to cache None results
        
    Example:
        @cached(ttl=300)
        async def get_user(user_id: int):
            return await db.get_user(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache service
            from src.services.cache_factory import get_cache_instance
            cache = await get_cache_instance()
            
            if not cache:
                return await func(*args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                prefix = key_prefix or func.__name__
                # Create key from function args
                key_parts = [str(arg) for arg in args]
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key_hash = hashlib.md5("_".join(key_parts).encode()).hexdigest()
                cache_key = f"{prefix}:{key_hash}"
            
            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            if result is not None or cache_none:
                await cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(
    key_prefix: Optional[str] = None,
    key_func: Optional[Callable] = None
):
    """
    Decorator to invalidate cache after function execution.
    
    Args:
        key_prefix: Key prefix to invalidate
        key_func: Custom key generation function
        
    Example:
        @invalidate_cache(key_prefix="user")
        async def update_user(user_id: int, data: dict):
            return await db.update_user(user_id, data)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute function first
            result = await func(*args, **kwargs)
            
            # Get cache service
            from src.services.cache_factory import get_cache_instance
            cache = await get_cache_instance()
            
            if cache:
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    prefix = key_prefix or func.__name__
                    key_parts = [str(arg) for arg in args]
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    key_hash = hashlib.md5("_".join(key_parts).encode()).hexdigest()
                    cache_key = f"{prefix}:{key_hash}"
                
                # Delete from cache
                await cache.delete(cache_key)
            
            return result
        
        return wrapper
    return decorator


# Global cache instance
_cache_instance: Optional[RedisCacheService] = None


async def get_cache() -> Optional[RedisCacheService]:
    """Get global cache instance."""
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = RedisCacheService()
        try:
            await _cache_instance.initialize()
            if not _cache_instance.is_connected():
                raise Exception("Redis not connected")
        except Exception as e:
            logger.error(f"Failed to initialize cache: {e}, using mock cache")
            # Use mock cache as fallback
            from src.services.redis_mock import MockRedisCacheService
            _cache_instance = MockRedisCacheService()
            await _cache_instance.initialize()
            logger.info("Mock cache service initialized as fallback")
    
    return _cache_instance


async def close_cache() -> None:
    """Close global cache instance."""
    global _cache_instance
    
    if _cache_instance:
        await _cache_instance.close()
        _cache_instance = None