"""
HTTP Response Cache Middleware.

Implements intelligent caching for API responses to improve performance:
- Cache key generation based on request parameters
- TTL-based expiration
- Cache invalidation strategies
- Conditional requests (ETag/Last-Modified)
- Cache warming capabilities
"""

import hashlib
import json
import time
import logging
from typing import Optional, Dict, Any, Callable, List, Set
from datetime import datetime, timedelta
import asyncio
from functools import wraps

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from src.services.ngx_cache_manager import NGXCacheManager
from src.core.dependencies import get_ngx_cache_manager
from src.core.constants import TimeConstants, CacheConstants, APIConstants

logger = logging.getLogger(__name__)


class CacheConfig:
    """Cache configuration for different endpoint patterns."""
    
    def __init__(
        self,
        ttl_seconds: int = TimeConstants.CACHE_DEFAULT_TTL,  # 5 minutes default
        cache_control: str = f"public, max-age={TimeConstants.CACHE_DEFAULT_TTL}",
        vary_headers: List[str] = None,
        invalidation_patterns: List[str] = None,
        conditional_requests: bool = True,
        warm_cache: bool = False
    ):
        self.ttl_seconds = ttl_seconds
        self.cache_control = cache_control
        self.vary_headers = vary_headers or ["Accept", "Accept-Encoding"]
        self.invalidation_patterns = invalidation_patterns or []
        self.conditional_requests = conditional_requests
        self.warm_cache = warm_cache


class HTTPCacheMiddleware(BaseHTTPMiddleware):
    """
    HTTP caching middleware with intelligent cache management.
    
    Features:
    - Automatic cache key generation
    - Configurable TTL per endpoint
    - ETag and Last-Modified support
    - Cache invalidation on writes
    - Performance metrics
    """
    
    def __init__(self, app, cache_configs: Optional[Dict[str, CacheConfig]] = None):
        super().__init__(app)
        self._cache_manager: Optional[NGXCacheManager] = None
        self._cache_namespace = "http_response"
        
        # Default cache configurations by endpoint pattern
        self.cache_configs = cache_configs or self._get_default_configs()
        
        # Cache invalidation tracking
        self.invalidation_rules = self._build_invalidation_rules()
        
        # Performance metrics
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0,
            "errors": 0
        }
        
        # Initialize cache manager asynchronously
        asyncio.create_task(self._initialize_cache())
        
        logger.info("HTTPCacheMiddleware initialized")
    
    async def _initialize_cache(self):
        """Initialize cache manager asynchronously."""
        try:
            self._cache_manager = await get_ngx_cache_manager()
            if self._cache_manager:
                logger.info("HTTP cache manager initialized successfully")
                
                # Warm cache if configured
                await self._warm_cache_if_needed()
        except Exception as e:
            logger.error(f"Failed to initialize HTTP cache manager: {e}")
    
    def _get_default_configs(self) -> Dict[str, CacheConfig]:
        """Get default cache configurations for common endpoints."""
        return {
            # Analytics endpoints - cache for 5 minutes
            r"/api/analytics/.*": CacheConfig(
                ttl_seconds=TimeConstants.CACHE_DEFAULT_TTL,
                cache_control=f"public, max-age={TimeConstants.CACHE_DEFAULT_TTL}",
                invalidation_patterns=["/api/conversation/.*"]
            ),
            
            # Model status endpoints - cache for 1 minute
            r"/api/ml/drift/status/.*": CacheConfig(
                ttl_seconds=TimeConstants.CACHE_SHORT_TTL,
                cache_control=f"public, max-age={TimeConstants.CACHE_SHORT_TTL}"
            ),
            
            # Summary endpoints - cache for 10 minutes
            r"/api/.*/summary.*": CacheConfig(
                ttl_seconds=TimeConstants.CACHE_LONG_TTL,
                cache_control=f"public, max-age={TimeConstants.CACHE_LONG_TTL}"
            ),
            
            # List endpoints - cache for 2 minutes
            r"/api/.*/list.*": CacheConfig(
                ttl_seconds=TimeConstants.MINUTE * 2,
                cache_control=f"public, max-age={TimeConstants.MINUTE * 2}"
            ),
            
            # Health checks - cache for 30 seconds
            r"/api/health.*": CacheConfig(
                ttl_seconds=TimeConstants.HEALTH_CHECK_INTERVAL,
                cache_control=f"public, max-age={TimeConstants.HEALTH_CHECK_INTERVAL}"
            ),
            
            # Predictions - don't cache
            r"/api/predictive/.*": None,
            
            # Conversations - selective caching for performance
            r"/api/conversation/.*/message": None,  # Don't cache actual messages
            r"/api/conversation/start": CacheConfig(
                ttl_seconds=TimeConstants.CACHE_SHORT_TTL,  # 1 minute for session starts
                cache_control=f"private, max-age={TimeConstants.CACHE_SHORT_TTL}",
                invalidation_patterns=[r"/api/conversation/.*/end"]
            ),
            r"/api/conversation/.*/context": CacheConfig(
                ttl_seconds=TimeConstants.CACHE_DEFAULT_TTL,  # 5 minutes for context
                cache_control=f"private, max-age={TimeConstants.CACHE_DEFAULT_TTL}"
            ),
            r"/api/conversation/.*/history": CacheConfig(
                ttl_seconds=TimeConstants.CACHE_LONG_TTL,  # 10 minutes for history
                cache_control=f"private, max-age={TimeConstants.CACHE_LONG_TTL}"
            )
        }
    
    def _build_invalidation_rules(self) -> Dict[str, Set[str]]:
        """Build invalidation rules from cache configs."""
        rules = {}
        
        for pattern, config in self.cache_configs.items():
            if config and config.invalidation_patterns:
                for inv_pattern in config.invalidation_patterns:
                    if inv_pattern not in rules:
                        rules[inv_pattern] = set()
                    rules[inv_pattern].add(pattern)
        
        return rules
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with caching logic."""
        # Only cache GET requests
        if request.method != "GET":
            response = await call_next(request)
            
            # Check for cache invalidation on write operations
            if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
                await self._handle_invalidation(request.url.path)
            
            return response
        
        # Get cache configuration for this endpoint
        cache_config = self._get_cache_config(request.url.path)
        if not cache_config:
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request, cache_config)
        
        # Check conditional request headers
        if cache_config.conditional_requests:
            cached_response = await self._check_conditional_request(request, cache_key)
            if cached_response:
                self.metrics["hits"] += 1
                return cached_response
        
        # Try to get from cache
        cached_data = await self._get_cached_response(cache_key)
        if cached_data:
            self.metrics["hits"] += 1
            return self._build_cached_response(cached_data, cache_config)
        
        # Cache miss - get fresh response
        self.metrics["misses"] += 1
        response = await call_next(request)
        
        # Cache successful responses
        if response.status_code == 200:
            await self._cache_response(cache_key, response, cache_config)
        
        return response
    
    def _get_cache_config(self, path: str) -> Optional[CacheConfig]:
        """Get cache configuration for the given path."""
        import re
        
        for pattern, config in self.cache_configs.items():
            if re.match(pattern, path):
                return config
        
        return None
    
    def _generate_cache_key(self, request: Request, config: CacheConfig) -> str:
        """Generate cache key from request."""
        # Base key components
        components = [
            self._cache_namespace,
            request.method,
            str(request.url.path),
            str(sorted(request.query_params.items()))
        ]
        
        # Add vary headers
        for header in config.vary_headers:
            header_value = request.headers.get(header, "")
            components.append(f"{header}:{header_value}")
        
        # Add user context if authenticated
        if hasattr(request.state, "user") and request.state.user:
            components.append(f"user:{request.state.user.get('id', 'anonymous')}")
        
        # Generate hash
        key_string = "|".join(components)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        
        return f"{self._cache_namespace}:{request.url.path}:{key_hash}"
    
    async def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response data."""
        if not self._cache_manager:
            return None
        
        try:
            cached = await self._cache_manager.get(cache_key)
            if cached:
                # Check if still valid
                if cached.get("expires_at", 0) > time.time():
                    return cached
                else:
                    # Expired - remove from cache
                    await self._cache_manager.delete(cache_key)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached response: {e}")
            self.metrics["errors"] += 1
            return None
    
    async def _cache_response(
        self,
        cache_key: str,
        response: Response,
        config: CacheConfig
    ):
        """Cache the response."""
        if not self._cache_manager:
            return
        
        try:
            # Read response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            # Parse response data
            try:
                response_data = json.loads(body.decode())
            except json.JSONDecodeError:
                # Don't cache non-JSON responses
                return
            
            # Prepare cache data
            cache_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_data,
                "cached_at": time.time(),
                "expires_at": time.time() + config.ttl_seconds,
                "etag": self._generate_etag(body),
                "last_modified": datetime.utcnow().isoformat()
            }
            
            # Store in cache
            await self._cache_manager.set(
                cache_key,
                cache_data,
                ttl=config.ttl_seconds
            )
            
            # Update response headers
            response.headers["X-Cache"] = "MISS"
            response.headers["Cache-Control"] = config.cache_control
            if config.conditional_requests:
                response.headers["ETag"] = cache_data["etag"]
                response.headers["Last-Modified"] = cache_data["last_modified"]
            
            # Recreate response with body
            response = Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            
        except Exception as e:
            logger.error(f"Error caching response: {e}")
            self.metrics["errors"] += 1
    
    def _build_cached_response(
        self,
        cached_data: Dict[str, Any],
        config: CacheConfig
    ) -> Response:
        """Build response from cached data."""
        # Create response
        response = JSONResponse(
            content=cached_data["body"],
            status_code=cached_data["status_code"],
            headers=cached_data.get("headers", {})
        )
        
        # Add cache headers
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Age"] = str(int(time.time() - cached_data["cached_at"]))
        response.headers["Cache-Control"] = config.cache_control
        
        if config.conditional_requests:
            response.headers["ETag"] = cached_data.get("etag", "")
            response.headers["Last-Modified"] = cached_data.get("last_modified", "")
        
        return response
    
    async def _check_conditional_request(
        self,
        request: Request,
        cache_key: str
    ) -> Optional[Response]:
        """Check for conditional request headers."""
        # Get cached data
        cached_data = await self._get_cached_response(cache_key)
        if not cached_data:
            return None
        
        # Check If-None-Match (ETag)
        if_none_match = request.headers.get("If-None-Match")
        if if_none_match and if_none_match == cached_data.get("etag"):
            return Response(status_code=APIConstants.HTTP_NOT_MODIFIED, headers={
                "ETag": cached_data["etag"],
                "Cache-Control": "public, max-age=0",
                "X-Cache": "HIT"
            })
        
        # Check If-Modified-Since
        if_modified_since = request.headers.get("If-Modified-Since")
        if if_modified_since:
            try:
                # Parse dates and compare
                modified_since = datetime.fromisoformat(if_modified_since.replace('Z', '+00:00'))
                last_modified = datetime.fromisoformat(cached_data.get("last_modified", ""))
                
                if last_modified <= modified_since:
                    return Response(status_code=APIConstants.HTTP_NOT_MODIFIED, headers={
                        "Last-Modified": cached_data["last_modified"],
                        "Cache-Control": "public, max-age=0",
                        "X-Cache": "HIT"
                    })
            except Exception:
                pass
        
        return None
    
    def _generate_etag(self, content: bytes) -> str:
        """Generate ETag from content."""
        return f'"{hashlib.md5(content).hexdigest()}"'
    
    async def _handle_invalidation(self, path: str):
        """Handle cache invalidation for write operations."""
        if not self._cache_manager:
            return
        
        import re
        
        # Find patterns that should be invalidated
        patterns_to_invalidate = set()
        
        for pattern, invalidation_set in self.invalidation_rules.items():
            if re.match(pattern, path):
                patterns_to_invalidate.update(invalidation_set)
        
        # Invalidate matching cache entries
        if patterns_to_invalidate:
            logger.info(f"Invalidating cache for patterns: {patterns_to_invalidate}")
            self.metrics["invalidations"] += 1
            
            # In a real implementation, we'd need to track keys by pattern
            # For now, we'll clear the namespace
            # TODO: Implement pattern-based invalidation
            await self._cache_manager.clear_namespace(self._cache_namespace)
    
    async def _warm_cache_if_needed(self):
        """Warm cache for configured endpoints."""
        # This would pre-populate cache for critical endpoints
        # Implementation depends on specific requirements
        pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics."""
        total_requests = self.metrics["hits"] + self.metrics["misses"]
        hit_rate = (self.metrics["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "total_requests": total_requests,
            "hits": self.metrics["hits"],
            "misses": self.metrics["misses"],
            "hit_rate": f"{hit_rate:.2f}%",
            "invalidations": self.metrics["invalidations"],
            "errors": self.metrics["errors"]
        }


def cache_response(
    ttl_seconds: int = TimeConstants.CACHE_DEFAULT_TTL,
    cache_key_func: Optional[Callable] = None,
    condition_func: Optional[Callable] = None
):
    """
    Decorator for caching individual endpoint responses.
    
    Args:
        ttl_seconds: Cache TTL in seconds
        cache_key_func: Custom cache key generator
        condition_func: Function to determine if response should be cached
    
    Usage:
        @router.get("/items/{item_id}")
        @cache_response(ttl_seconds=600)
        async def get_item(item_id: str):
            return {"item_id": item_id}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache manager
            cache_manager = await get_ngx_cache_manager()
            if not cache_manager:
                return await func(*args, **kwargs)
            
            # Generate cache key
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__module__, func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached = await cache_manager.get(cache_key)
            if cached:
                return cached
            
            # Get fresh result
            result = await func(*args, **kwargs)
            
            # Check if should cache
            if condition_func is None or condition_func(result):
                await cache_manager.set(cache_key, result, ttl=ttl_seconds)
            
            return result
        
        return wrapper
    return decorator