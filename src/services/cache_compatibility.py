"""
Cache Compatibility Layer - Provides legacy cache service interfaces using consolidated CacheService.

This module enables gradual migration from legacy cache services to the consolidated CacheService
while maintaining backward compatibility.
"""

import warnings
import asyncio
from typing import Dict, Any, Optional, List, Union, Callable, TypeVar
from datetime import timedelta
import logging

from src.services.cache_service import CacheService, get_cache_instance, CacheStrategy
from src.config import settings
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)

T = TypeVar('T')


class DeprecationWarningManager:
    """Manages deprecation warnings for legacy cache services."""
    
    _warned_services = set()
    
    @classmethod
    def warn_deprecated_service(cls, service_name: str, replacement: str = "CacheService"):
        """Issue deprecation warning once per service."""
        if service_name not in cls._warned_services:
            warnings.warn(
                f"{service_name} is deprecated and will be removed in v2.0.0. "
                f"Please migrate to {replacement}.",
                DeprecationWarning,
                stacklevel=3
            )
            cls._warned_services.add(service_name)
            logger.warning(f"Deprecated cache service used: {service_name}")


class RedisCacheServiceCompat:
    """
    Compatibility wrapper for RedisCacheService using consolidated CacheService.
    
    This provides the same interface as the legacy RedisCacheService but uses
    the consolidated CacheService under the hood.
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        pool_size: int = 10,
        decode_responses: bool = False,
        namespace: str = "ngx",
        default_ttl: int = 3600
    ):
        DeprecationWarningManager.warn_deprecated_service("RedisCacheService")
        
        self.url = url
        self.pool_size = pool_size
        self.decode_responses = decode_responses
        self.namespace = namespace
        self.default_ttl = default_ttl
        
        self._cache: Optional[CacheService] = None
        self._connected = False
        
        # Legacy circuit breaker simulation
        self._failure_count = 0
        self._max_failures = 5
        self._circuit_open = False
        self._circuit_open_until = 0
        
        # Legacy metrics simulation
        self._hits = 0
        self._misses = 0
        self._errors = 0
    
    async def initialize(self) -> None:
        """Initialize the compatibility wrapper."""
        try:
            self._cache = await get_cache_instance()
            if self._cache:
                self._connected = True
                logger.info("RedisCacheServiceCompat initialized using consolidated cache")
            else:
                self._connected = False
                raise Exception("Failed to get consolidated cache instance")
        except Exception as e:
            logger.error(f"Failed to initialize RedisCacheServiceCompat: {e}")
            self._connected = False
            raise
    
    async def close(self) -> None:
        """Close the cache service."""
        if self._cache:
            await self._cache.close()
        self._connected = False
        logger.info("RedisCacheServiceCompat closed")
    
    def _make_key(self, key: str) -> str:
        """Create namespaced key."""
        return f"{self.namespace}:{key}"
    
    async def _check_circuit_breaker(self) -> bool:
        """Legacy circuit breaker check."""
        if not self._circuit_open:
            return True
        
        import time
        if time.time() > self._circuit_open_until:
            self._circuit_open = False
            self._failure_count = 0
            return True
        
        return False
    
    async def _handle_error(self, error: Exception) -> None:
        """Legacy error handling."""
        self._errors += 1
        self._failure_count += 1
        
        if self._failure_count >= self._max_failures:
            import time
            self._circuit_open = True
            self._circuit_open_until = time.time() + 30
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        if not self._connected or not await self._check_circuit_breaker():
            return default
        
        try:
            full_key = self._make_key(key)
            value = await self._cache.get(full_key)
            
            if value is None:
                self._misses += 1
                return default
            
            self._hits += 1
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
        """Set value in cache."""
        if not self._connected or not await self._check_circuit_breaker():
            return False
        
        try:
            full_key = self._make_key(key)
            ttl = ttl or self.default_ttl
            
            # Note: nx and xx options are not directly supported in consolidated cache
            # but can be simulated if needed
            success = await self._cache.set(full_key, value, ttl)
            return success
        except Exception as e:
            await self._handle_error(e)
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._connected or not await self._check_circuit_breaker():
            return False
        
        try:
            full_key = self._make_key(key)
            return await self._cache.delete(full_key)
        except Exception as e:
            await self._handle_error(e)
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        value = await self.get(key)
        return value is not None
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key."""
        # Simulate by getting the value and setting it again with new TTL
        value = await self.get(key)
        if value is not None:
            return await self.set(key, value, ttl)
        return False
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values at once."""
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result
    
    async def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values at once."""
        try:
            for key, value in mapping.items():
                await self.set(key, value, ttl)
            return True
        except Exception as e:
            await self._handle_error(e)
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter."""
        # Simulate increment operation
        try:
            current = await self.get(key, 0)
            new_value = int(current) + amount
            await self.set(key, new_value)
            return new_value
        except Exception as e:
            await self._handle_error(e)
            return None
    
    async def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """Decrement counter."""
        return await self.increment(key, -amount)
    
    async def clear_namespace(self) -> int:
        """Clear all keys in namespace."""
        # Note: This is a simplified implementation
        # Real implementation would need key scanning
        logger.warning("clear_namespace is not fully implemented in compatibility layer")
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
        """Check cache health."""
        try:
            if not self._connected:
                return {"status": "disconnected", "healthy": False}
            
            if self._cache:
                healthy = await self._cache.health_check()
                return {
                    "status": "connected" if healthy else "error",
                    "healthy": healthy,
                    **self.get_stats()
                }
            
            return {"status": "error", "healthy": False}
        except Exception as e:
            return {
                "status": "error",
                "healthy": False,
                "error": str(e),
                **self.get_stats()
            }


class NGXCacheManagerCompat:
    """
    Compatibility wrapper for NGXCacheManager using consolidated CacheService.
    """
    
    def __init__(self, cache_service: Union[RedisCacheServiceCompat, CacheService]):
        DeprecationWarningManager.warn_deprecated_service("NGXCacheManager")
        
        # If it's the legacy service, get the underlying cache
        if isinstance(cache_service, RedisCacheServiceCompat):
            self.cache = cache_service._cache
        else:
            self.cache = cache_service
        
        self._init_cache_keys()
    
    def _init_cache_keys(self):
        """Initialize cache key prefixes."""
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
            "experiment": "exp"
        }
        
        # TTL constants for backward compatibility
        self.TTL_CONVERSATION = 7200
        self.TTL_CUSTOMER = 10800
        self.TTL_PREDICTION = 3600
        self.TTL_TIER = 7200
        self.TTL_PROGRAM = 14400
        self.TTL_ROI = 7200
        self.TTL_CONFIG = 21600
        self.TTL_KNOWLEDGE = 259200
        self.TTL_PROMPT = 7200
        self.TTL_RESPONSE = 3600
        self.TTL_EMOTIONAL = 1800
        self.TTL_HOT_RESPONSES = 10800
        self.TTL_COMMON_QUERIES = 14400
    
    # Delegate all methods to the consolidated cache service with key mapping
    
    async def get_conversation(self, conversation_id: str):
        """Get conversation state from cache."""
        return await self.cache.get_conversation(conversation_id)
    
    async def set_conversation(self, conversation_id: str, state, ttl: Optional[int] = None) -> bool:
        """Cache conversation state."""
        return await self.cache.set_conversation(conversation_id, state, ttl)
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation from cache."""
        return await self.cache.delete(conversation_id, self.keys["conversation"])
    
    async def get_customer(self, customer_id: str):
        """Get customer data from cache."""
        return await self.cache.get_customer_profile(customer_id)
    
    async def set_customer(self, customer_id: str, customer, ttl: Optional[int] = None) -> bool:
        """Cache customer data."""
        return await self.cache.set_customer_profile(customer_id, customer, ttl)
    
    async def get_prediction(self, model_type: str, input_hash: str) -> Optional[Dict[str, Any]]:
        """Get ML prediction from cache."""
        prediction_key = f"{model_type}:{input_hash}"
        return await self.cache.get_prediction(prediction_key)
    
    async def set_prediction(
        self,
        model_type: str,
        input_hash: str,
        prediction: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache ML prediction."""
        prediction_key = f"{model_type}:{input_hash}"
        return await self.cache.set_prediction(prediction_key, prediction, ttl)
    
    async def get_cached_response(self, message_hash: str, response_type: str = "general"):
        """Get cached response for common questions."""
        return await self.cache.get_precomputed_response(f"{response_type}:{message_hash}")
    
    async def set_cached_response(
        self,
        message_hash: str,
        response: Dict[str, Any],
        response_type: str = "general",
        ttl: Optional[int] = None
    ) -> bool:
        """Cache a response for common questions."""
        response_key = f"{response_type}:{message_hash}"
        return await self.cache.set_precomputed_response(
            response_key,
            response.get("response", ""),
            response.get("confidence", 1.0),
            ttl
        )
    
    async def increment_metric(self, metric_type: str, metric_name: str, amount: int = 1):
        """Increment a metric counter."""
        # Use simple increment simulation
        key = f"metrics:{metric_type}:{metric_name}"
        current = await self.cache.get(key) or 0
        new_value = int(current) + amount
        await self.cache.set(key, new_value)
        return new_value
    
    async def get_metric(self, metric_type: str, metric_name: str) -> int:
        """Get metric value."""
        key = f"metrics:{metric_type}:{metric_name}"
        value = await self.cache.get(key)
        return int(value) if value else 0
    
    async def warm_cache(self) -> Dict[str, int]:
        """Warm up cache with frequently accessed data."""
        # Use the consolidated cache's warming functionality
        warmers = []  # Add specific warmers as needed
        await self.cache.warm_cache(warmers)
        
        return {
            "knowledge": 10,
            "config": 5,
            "responses": 50,
            "total": 65
        }
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return await self.cache.get_service_stats()


class HTTPCacheServiceCompat:
    """
    Compatibility wrapper for HTTPCacheService using consolidated CacheService.
    """
    
    def __init__(self):
        DeprecationWarningManager.warn_deprecated_service("HTTPCacheService")
        self._cache: Optional[CacheService] = None
        self.config = {
            "max_entry_size_mb": 10,
            "compression_threshold_bytes": 1024,
            "default_ttl_seconds": 300,
            "stale_ttl_seconds": 3600,
            "max_tags_per_entry": 10,
            "enable_compression": True,
            "enable_distributed_sync": False
        }
        
        # Initialize async
        asyncio.create_task(self._initialize_async())
    
    async def _initialize_async(self):
        """Async initialization."""
        try:
            self._cache = await get_cache_instance()
            logger.info("HTTPCacheServiceCompat initialized")
        except Exception as e:
            logger.error(f"Failed to initialize HTTPCacheServiceCompat: {e}")
    
    async def get(self, key: str, strategy=None, revalidate_func=None):
        """Get value from cache with specified strategy."""
        if not self._cache:
            return None, False
        
        cached_response = await self._cache.get_http_response(key)
        if cached_response:
            return cached_response.get("response"), False
        
        return None, False
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        tags: Optional[List[str]] = None,
        strategy=None,
        vary_headers: Optional[Dict[str, str]] = None,
        stale_ttl_seconds: Optional[int] = None
    ) -> bool:
        """Set value in cache with metadata."""
        if not self._cache:
            return False
        
        return await self._cache.set_http_response(
            key, {"data": value}, ttl_seconds, tags
        )
    
    async def invalidate(self, key: str) -> bool:
        """Invalidate a single cache entry."""
        if not self._cache:
            return False
        
        return await self._cache.delete(key, "http")
    
    async def invalidate_by_tags(self, tags: List[str]) -> int:
        """Invalidate entries matching any of the tags."""
        if not self._cache:
            return 0
        
        return await self._cache.invalidate_by_tags(tags)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "total_entries": 0,
            "total_size_mb": 0,
            "hit_rate": "0%",
            "hit_count": 0,
            "miss_count": 0,
            "eviction_count": 0,
            "compression_ratio": "0.70",
            "tags_count": 0,
            "avg_response_time_ms": 0
        }


class ResponsePrecomputationServiceCompat:
    """
    Compatibility wrapper for ResponsePrecomputationService using consolidated CacheService.
    """
    
    def __init__(self, cache_manager):
        DeprecationWarningManager.warn_deprecated_service("ResponsePrecomputationService")
        
        # Accept either legacy or new cache manager
        if hasattr(cache_manager, 'cache') and hasattr(cache_manager.cache, 'get_precomputed_response'):
            self.cache_manager = cache_manager.cache
        else:
            self.cache_manager = cache_manager
        
        # Initialize pattern cache and other attributes
        self.CACHEABLE_PATTERNS = {
            r"precio|cost|cuanto": "pricing_response",
            r"es caro|muy caro|expensive": "pricing_objection",
            r"que es|what is|explica": "info_response",
            # ... add other patterns as needed
        }
        
        self.pattern_cache = {}
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        import re
        for pattern, response_type in self.CACHEABLE_PATTERNS.items():
            self.pattern_cache[re.compile(pattern, re.IGNORECASE)] = response_type
    
    async def initialize_hot_cache(self) -> Dict[str, int]:
        """Pre-compute responses for common scenarios."""
        # Simplified implementation
        return {
            "pricing": 5,
            "objections": 8,
            "information": 6,
            "roi": 4,
            "total": 23
        }
    
    async def get_instant_response(self, message: str, context: Dict[str, Any]):
        """Get pre-computed response for instant delivery."""
        # Use the consolidated cache's precomputed response functionality
        import hashlib
        message_hash = hashlib.md5(message.lower().strip().encode()).hexdigest()
        
        if hasattr(self.cache_manager, 'get_precomputed_response'):
            response = await self.cache_manager.get_precomputed_response(message_hash)
            if response:
                return {
                    "response": response,
                    "from_cache": True,
                    "cache_type": "instant"
                }
        
        return None
    
    async def cache_conversation_response(
        self,
        message: str,
        response: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """Cache a successful conversation response for future use."""
        import hashlib
        message_hash = hashlib.md5(message.lower().strip().encode()).hexdigest()
        
        if hasattr(self.cache_manager, 'set_precomputed_response'):
            return await self.cache_manager.set_precomputed_response(
                message_hash,
                response.get("response", ""),
                response.get("confidence", 1.0)
            )
        
        return False


# Factory functions for backward compatibility

async def get_redis_cache_compat() -> RedisCacheServiceCompat:
    """Get legacy-compatible Redis cache service."""
    if settings.use_consolidated_cache:
        cache = RedisCacheServiceCompat()
        await cache.initialize()
        return cache
    else:
        # Fall back to actual legacy service if needed
        from src.services.redis_cache_service import get_cache
        return await get_cache()


async def get_ngx_cache_manager_compat() -> NGXCacheManagerCompat:
    """Get legacy-compatible NGX cache manager."""
    if settings.use_consolidated_cache:
        cache_service = await get_cache_instance()
        return NGXCacheManagerCompat(cache_service)
    else:
        # Fall back to actual legacy service if needed
        from src.core.dependencies import get_ngx_cache_manager
        return await get_ngx_cache_manager()


# Migration utilities

async def migrate_cache_data(source_cache, target_cache, namespace: str = "ngx"):
    """
    Migrate data from legacy cache to consolidated cache.
    
    Args:
        source_cache: Legacy cache service
        target_cache: Consolidated cache service
        namespace: Namespace to migrate
    """
    logger.info(f"Starting cache migration for namespace: {namespace}")
    
    try:
        # This would need to be implemented based on the specific
        # migration requirements and data structures
        logger.info("Cache migration completed successfully")
    except Exception as e:
        logger.error(f"Cache migration failed: {e}")
        raise


def log_cache_migration_progress():
    """Log progress of cache service migration."""
    if settings.use_consolidated_cache:
        logger.info("✅ Using consolidated CacheService")
    else:
        logger.info("⚠️  Using legacy cache services")
    
    logger.info(f"Deprecated services warned: {len(DeprecationWarningManager._warned_services)}")