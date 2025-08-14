"""
Unified Cache Service - Consolidated caching functionality for NGX Voice Sales Agent.

This service consolidates all caching functionality previously spread across:
- redis_cache_service.py
- ngx_cache_manager.py
- http_cache_service.py
- response_precomputation_service.py
- cache_factory.py

Provides:
- Redis caching with connection pooling
- HTTP response caching with ETags and compression
- NGX-specific data caching (conversations, customers, predictions)
- Precomputed response caching
- Cache factory functionality
"""

import asyncio
import gzip
import json
import hashlib
import logging
import pickle
from typing import Dict, Any, List, Optional, Set, Tuple, Union, TypeVar, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from src.config import settings
from src.models.conversation import ConversationState, CustomerData
from src.models.learning_models import LearnedModel
from src.utils.structured_logging import StructuredLogger
from src.core.constants import CacheConstants, TimeConstants

logger = StructuredLogger.get_logger(__name__)

T = TypeVar('T')


class CacheStrategy(Enum):
    """Cache strategies for different use cases."""
    STANDARD = "standard"
    STALE_WHILE_REVALIDATE = "stale_while_revalidate"
    EDGE_SIDE_INCLUDES = "edge_side_includes"
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"


@dataclass
class CacheEntry:
    """Represents a cached entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    last_accessed: datetime
    access_count: int = 0
    tags: Set[str] = field(default_factory=set)
    compressed: bool = False
    size_bytes: int = 0
    etag: Optional[str] = None


@dataclass
class CacheStats:
    """Cache statistics."""
    total_entries: int = 0
    total_size_bytes: int = 0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    compression_ratio: float = 0.0
    avg_response_time_ms: float = 0.0


class CacheService:
    """
    Unified cache service combining all caching functionality.
    
    Features:
    - Redis caching with async support and connection pooling
    - HTTP response caching with ETags and compression
    - NGX-specific data caching optimizations
    - Precomputed response caching
    - Cache factory functionality
    - Namespace support and TTL management
    - Circuit breaker pattern for resilience
    """
    
    # Cache TTLs (in seconds) - Optimized for performance
    TTL_CONVERSATION = 7200  # 2 hours
    TTL_CUSTOMER = 10800     # 3 hours
    TTL_PREDICTION = 3600    # 1 hour
    TTL_TIER = 7200         # 2 hours
    TTL_PROGRAM = 14400     # 4 hours
    TTL_ROI = 7200          # 2 hours
    TTL_CONFIG = 21600      # 6 hours
    TTL_KNOWLEDGE = 259200   # 72 hours
    TTL_PROMPT = 7200       # 2 hours
    TTL_RESPONSE = 3600     # 1 hour
    TTL_EMOTIONAL = 1800    # 30 minutes
    TTL_HOT_RESPONSES = 10800  # 3 hours
    TTL_COMMON_QUERIES = 14400  # 4 hours
    
    def __init__(
        self,
        url: Optional[str] = None,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        ssl: bool = False,
        pool_size: int = 10,
        decode_responses: bool = True,
        namespace: str = "ngx",
        default_ttl: int = 3600
    ):
        """
        Initialize unified cache service.
        
        Args:
            url: Redis connection URL (overrides other connection params)
            host: Redis host
            port: Redis port
            password: Redis password
            db: Redis database number
            ssl: Use SSL connection
            pool_size: Connection pool size
            decode_responses: Decode responses from bytes
            namespace: Key namespace prefix
            default_ttl: Default TTL in seconds
        """
        self.namespace = namespace
        self.default_ttl = default_ttl
        self.pool_size = pool_size
        
        # Redis connection setup
        if url:
            self.pool = ConnectionPool.from_url(
                url,
                max_connections=pool_size,
                decode_responses=decode_responses
            )
        else:
            connection_kwargs = {
                "host": host,
                "port": port,
                "password": password,
                "db": db,
                "max_connections": pool_size,
                "decode_responses": decode_responses,
                "socket_connect_timeout": 5,
                "socket_timeout": 5,
                "retry_on_timeout": True,
                "health_check_interval": 30
            }
            
            # Only add SSL parameter if it's True and supported
            if ssl:
                connection_kwargs["ssl"] = ssl
            
            self.pool = ConnectionPool(**connection_kwargs)
        
        self.redis: Optional[redis.Redis] = None
        self.is_connected = False
        self.stats = CacheStats()
        
        # Cache key prefixes
        self.keys = {
            "conversation": "conv",
            "customer": "cust",
            "prediction": "pred",
            "tier": "tier",
            "program": "prog",
            "roi": "roi",
            "config": "conf",
            "knowledge": "know",
            "metrics": "metr",
            "experiment": "exp",
            "http": "http",
            "precomputed": "precomp"
        }
        
        # In-memory structures for HTTP caching
        self.tag_index: Dict[str, Set[str]] = {}
        self.precomputed_responses: Dict[str, Dict[str, Any]] = {}
        
        # Mock mode for testing
        self.mock_mode = settings.redis_mock_enabled if hasattr(settings, 'redis_mock_enabled') else False
        self.mock_storage: Dict[str, Any] = {}  # Always initialize for potential mock use
        
        logger.info(f"CacheService initialized with namespace='{namespace}', mock_mode={self.mock_mode}")
    
    async def initialize(self) -> None:
        """Initialize Redis connection."""
        if self.mock_mode:
            logger.info("Running in mock mode - no Redis connection needed")
            self.is_connected = True
            return
        
        try:
            self.redis = redis.Redis(connection_pool=self.pool)
            await self.redis.ping()
            self.is_connected = True
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.is_connected = False
            raise
    
    def _make_key(self, key: str, prefix: str = "") -> str:
        """Generate namespaced cache key."""
        if prefix:
            return f"{self.namespace}:{prefix}:{key}"
        return f"{self.namespace}:{key}"
    
    # Core Cache Operations
    
    async def get(self, key: str, prefix: str = "") -> Optional[Any]:
        """Get value from cache."""
        cache_key = self._make_key(key, prefix)
        
        if self.mock_mode:
            value = self.mock_storage.get(cache_key)
            if value is not None:
                self.stats.hit_count += 1
                return value
            self.stats.miss_count += 1
            return None
        
        if not self.is_connected:
            return None
        
        try:
            data = await self.redis.get(cache_key)
            if data is not None:
                self.stats.hit_count += 1
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    return pickle.loads(data)
            self.stats.miss_count += 1
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {cache_key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        prefix: str = "",
        tags: Optional[List[str]] = None
    ) -> bool:
        """Set value in cache."""
        cache_key = self._make_key(key, prefix)
        ttl = ttl or self.default_ttl
        
        # Serialize value
        try:
            serialized = json.dumps(value, default=str)
        except (TypeError, ValueError):
            serialized = pickle.dumps(value)
        
        if self.mock_mode:
            self.mock_storage[cache_key] = value
            # Simulate TTL in mock mode (simplified)
            if tags:
                for tag in tags:
                    if tag not in self.tag_index:
                        self.tag_index[tag] = set()
                    self.tag_index[tag].add(cache_key)
            return True
        
        if not self.is_connected:
            return False
        
        try:
            await self.redis.setex(cache_key, ttl, serialized)
            
            # Handle tags for HTTP caching
            if tags:
                for tag in tags:
                    if tag not in self.tag_index:
                        self.tag_index[tag] = set()
                    self.tag_index[tag].add(cache_key)
            
            self.stats.total_entries += 1
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {cache_key}: {e}")
            return False
    
    async def delete(self, key: str, prefix: str = "") -> bool:
        """Delete value from cache."""
        cache_key = self._make_key(key, prefix)
        
        if self.mock_mode:
            if cache_key in self.mock_storage:
                del self.mock_storage[cache_key]
                return True
            return False
        
        if not self.is_connected:
            return False
        
        try:
            result = await self.redis.delete(cache_key)
            if result:
                self.stats.eviction_count += 1
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {cache_key}: {e}")
            return False
    
    async def invalidate_by_tags(self, tags: List[str]) -> int:
        """Invalidate all cache entries with specified tags."""
        invalidated = 0
        
        for tag in tags:
            if tag in self.tag_index:
                keys_to_delete = self.tag_index[tag].copy()
                for cache_key in keys_to_delete:
                    if self.mock_mode:
                        if cache_key in self.mock_storage:
                            del self.mock_storage[cache_key]
                            invalidated += 1
                    else:
                        if self.is_connected:
                            try:
                                result = await self.redis.delete(cache_key)
                                if result:
                                    invalidated += 1
                            except Exception as e:
                                logger.error(f"Error deleting cache key {cache_key}: {e}")
                
                # Clean up tag index
                del self.tag_index[tag]
        
        logger.info(f"Invalidated {invalidated} cache entries for tags: {tags}")
        return invalidated
    
    # NGX-Specific Caching Methods
    
    async def get_conversation(self, conversation_id: str) -> Optional[ConversationState]:
        """Get conversation state from cache."""
        data = await self.get(conversation_id, self.keys["conversation"])
        if data:
            try:
                return ConversationState(**data)
            except Exception as e:
                logger.error(f"Error deserializing conversation: {e}")
                await self.delete(conversation_id, self.keys["conversation"])
        return None
    
    async def set_conversation(
        self,
        conversation_id: str,
        state: ConversationState,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache conversation state."""
        ttl = ttl or self.TTL_CONVERSATION
        return await self.set(
            conversation_id,
            state.dict(),
            ttl,
            self.keys["conversation"]
        )
    
    async def get_customer_profile(self, customer_id: str) -> Optional[CustomerData]:
        """Get customer profile from cache."""
        data = await self.get(customer_id, self.keys["customer"])
        if data:
            try:
                return CustomerData(**data)
            except Exception as e:
                logger.error(f"Error deserializing customer profile: {e}")
                await self.delete(customer_id, self.keys["customer"])
        return None
    
    async def set_customer_profile(
        self,
        customer_id: str,
        profile: CustomerData,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache customer profile."""
        ttl = ttl or self.TTL_CUSTOMER
        return await self.set(
            customer_id,
            profile.dict(),
            ttl,
            self.keys["customer"]
        )
    
    async def get_prediction(self, prediction_key: str) -> Optional[Dict[str, Any]]:
        """Get ML prediction from cache."""
        return await self.get(prediction_key, self.keys["prediction"])
    
    async def set_prediction(
        self,
        prediction_key: str,
        prediction: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache ML prediction."""
        ttl = ttl or self.TTL_PREDICTION
        return await self.set(
            prediction_key,
            prediction,
            ttl,
            self.keys["prediction"]
        )
    
    # HTTP Response Caching
    
    async def get_http_response(self, request_key: str) -> Optional[Dict[str, Any]]:
        """Get cached HTTP response."""
        return await self.get(request_key, self.keys["http"])
    
    async def set_http_response(
        self,
        request_key: str,
        response: Dict[str, Any],
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
        etag: Optional[str] = None
    ) -> bool:
        """Cache HTTP response with metadata."""
        ttl = ttl or self.TTL_RESPONSE
        
        # Add metadata
        cached_response = {
            "response": response,
            "cached_at": datetime.utcnow().isoformat(),
            "etag": etag
        }
        
        return await self.set(
            request_key,
            cached_response,
            ttl,
            self.keys["http"],
            tags
        )
    
    # Precomputed Response Caching
    
    async def get_precomputed_response(self, response_key: str) -> Optional[str]:
        """Get precomputed response."""
        data = await self.get(response_key, self.keys["precomputed"])
        return data.get("response") if data else None
    
    async def set_precomputed_response(
        self,
        response_key: str,
        response: str,
        confidence: float = 1.0,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache precomputed response."""
        ttl = ttl or self.TTL_HOT_RESPONSES
        
        precomputed_data = {
            "response": response,
            "confidence": confidence,
            "created_at": datetime.utcnow().isoformat()
        }
        
        return await self.set(
            response_key,
            precomputed_data,
            ttl,
            self.keys["precomputed"]
        )
    
    # Utility Methods
    
    async def warm_cache(self, cache_warmers: List[Callable]) -> None:
        """Warm cache with precomputed data."""
        logger.info("Starting cache warming process...")
        
        for warmer in cache_warmers:
            try:
                await warmer(self)
            except Exception as e:
                logger.error(f"Cache warmer failed: {e}")
        
        logger.info("Cache warming completed")
    
    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        if self.is_connected and not self.mock_mode:
            try:
                info = await self.redis.info()
                self.stats.total_entries = info.get('db0', {}).get('keys', 0)
                self.stats.total_size_bytes = info.get('used_memory', 0)
            except Exception as e:
                logger.error(f"Error getting Redis stats: {e}")
        
        return self.stats
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        stats = await self.get_stats()
        return {
            "total_entries": stats.total_entries,
            "total_size_bytes": stats.total_size_bytes,
            "hit_count": stats.hit_count,
            "miss_count": stats.miss_count,
            "hit_rate": stats.hit_count / (stats.hit_count + stats.miss_count) if (stats.hit_count + stats.miss_count) > 0 else 0,
            "eviction_count": stats.eviction_count,
            "mock_mode": self.mock_mode,
            "namespace": self.namespace,
            "ttl_settings": {
                "conversation": self.TTL_CONVERSATION,
                "customer": self.TTL_CUSTOMER,
                "prediction": self.TTL_PREDICTION,
                "response": self.TTL_RESPONSE
            }
        }
    
    async def health_check(self) -> bool:
        """Check cache service health."""
        if self.mock_mode:
            return True
        
        if not self.is_connected:
            return False
        
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close cache service connections."""
        if self.redis and not self.mock_mode:
            await self.redis.close()
        
        self.is_connected = False
        logger.info("Cache service closed")


# Global cache instance
_cache_instance: Optional[CacheService] = None


async def create_cache_instance() -> CacheService:
    """Create a new cache instance based on configuration."""
    global _cache_instance
    
    if hasattr(settings, 'redis_mock_enabled') and settings.redis_mock_enabled:
        logger.info("Using mock cache service")
        _cache_instance = CacheService(namespace="ngx_test")
        _cache_instance.mock_mode = True
    else:
        logger.info("Using real Redis cache service")
        _cache_instance = CacheService(
            host=getattr(settings, 'redis_host', 'localhost'),
            port=getattr(settings, 'redis_port', 6379),
            password=getattr(settings, 'redis_password', None),
            db=getattr(settings, 'redis_db', 0),
            ssl=getattr(settings, 'redis_ssl', False),
            decode_responses=True,
            pool_size=10
        )
    
    # Initialize the cache
    await _cache_instance.initialize()
    
    return _cache_instance


async def get_cache_instance() -> Optional[CacheService]:
    """Get the global cache instance, creating it if necessary."""
    global _cache_instance
    
    if _cache_instance is None:
        try:
            _cache_instance = await create_cache_instance()
        except Exception as e:
            logger.error(f"Failed to create cache instance: {e}")
            return None
    
    return _cache_instance


# Decorator for caching function results
def cached(ttl: int = 3600, prefix: str = "", tags: Optional[List[str]] = None):
    """Decorator to cache function results."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            cache = await get_cache_instance()
            if not cache:
                return await func(*args, **kwargs)
            
            # Generate cache key from function name and arguments
            key_data = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Try to get from cache
            cached_result = await cache.get(cache_key, prefix)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl, prefix, tags)
            
            return result
        
        return wrapper
    return decorator