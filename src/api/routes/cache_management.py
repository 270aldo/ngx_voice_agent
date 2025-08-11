"""
Cache Management API Routes.

Provides endpoints for monitoring and managing HTTP cache:
- View cache statistics
- Invalidate cache entries
- Configure cache settings
- Monitor cache performance
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
import logging

from src.services.http_cache_service import HTTPCacheService
from src.api.dependencies import get_current_user
from src.models.api_models import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["Cache Management"])

# Global cache service instance
_cache_service: Optional[HTTPCacheService] = None


def get_cache_service() -> HTTPCacheService:
    """Get or create cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = HTTPCacheService()
    return _cache_service


@router.get("/stats", response_model=StandardResponse)
async def get_cache_statistics(
    cache_service: HTTPCacheService = Depends(get_cache_service),
    current_user: Dict = Depends(get_current_user)
) -> StandardResponse:
    """
    Get cache statistics and performance metrics.
    
    Requires authentication.
    
    Returns:
        Cache statistics including hit rate, size, etc.
    """
    try:
        stats = cache_service.get_stats()
        
        return StandardResponse(
            success=True,
            data=stats,
            message="Cache statistics retrieved"
        )
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache statistics: {str(e)}"
        )


@router.post("/invalidate/key/{cache_key}", response_model=StandardResponse)
async def invalidate_cache_key(
    cache_key: str,
    cache_service: HTTPCacheService = Depends(get_cache_service),
    current_user: Dict = Depends(get_current_user)
) -> StandardResponse:
    """
    Invalidate a specific cache key.
    
    Requires authentication.
    
    Args:
        cache_key: The cache key to invalidate
        
    Returns:
        Invalidation result
    """
    try:
        success = await cache_service.invalidate(cache_key)
        
        return StandardResponse(
            success=success,
            data={"key": cache_key, "invalidated": success},
            message=f"Cache key {'invalidated' if success else 'not found'}"
        )
        
    except Exception as e:
        logger.error(f"Error invalidating cache key: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate cache key: {str(e)}"
        )


@router.post("/invalidate/tag/{tag}", response_model=StandardResponse)
async def invalidate_cache_by_tag(
    tag: str,
    cache_service: HTTPCacheService = Depends(get_cache_service),
    current_user: Dict = Depends(get_current_user)
) -> StandardResponse:
    """
    Invalidate all cache entries with a specific tag.
    
    Requires authentication.
    
    Args:
        tag: The tag to invalidate
        
    Returns:
        Number of entries invalidated
    """
    try:
        count = await cache_service.invalidate_by_tag(tag)
        
        return StandardResponse(
            success=True,
            data={"tag": tag, "invalidated_count": count},
            message=f"Invalidated {count} cache entries with tag '{tag}'"
        )
        
    except Exception as e:
        logger.error(f"Error invalidating by tag: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate by tag: {str(e)}"
        )


@router.post("/invalidate/tags", response_model=StandardResponse)
async def invalidate_cache_by_tags(
    tags: List[str],
    cache_service: HTTPCacheService = Depends(get_cache_service),
    current_user: Dict = Depends(get_current_user)
) -> StandardResponse:
    """
    Invalidate cache entries matching any of the provided tags.
    
    Requires authentication.
    
    Args:
        tags: List of tags to invalidate
        
    Returns:
        Number of entries invalidated
    """
    try:
        count = await cache_service.invalidate_by_tags(tags)
        
        return StandardResponse(
            success=True,
            data={"tags": tags, "invalidated_count": count},
            message=f"Invalidated {count} cache entries"
        )
        
    except Exception as e:
        logger.error(f"Error invalidating by tags: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate by tags: {str(e)}"
        )


@router.post("/invalidate/pattern", response_model=StandardResponse)
async def invalidate_cache_by_pattern(
    pattern: str,
    cache_service: HTTPCacheService = Depends(get_cache_service),
    current_user: Dict = Depends(get_current_user)
) -> StandardResponse:
    """
    Invalidate cache entries matching a pattern.
    
    Requires authentication.
    
    Args:
        pattern: Pattern to match (supports * wildcard)
        
    Returns:
        Number of entries invalidated
    """
    try:
        count = await cache_service.invalidate_pattern(pattern)
        
        return StandardResponse(
            success=True,
            data={"pattern": pattern, "invalidated_count": count},
            message=f"Invalidated {count} cache entries matching pattern"
        )
        
    except Exception as e:
        logger.error(f"Error invalidating by pattern: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate by pattern: {str(e)}"
        )


@router.get("/config", response_model=StandardResponse)
async def get_cache_configuration(
    cache_service: HTTPCacheService = Depends(get_cache_service),
    current_user: Dict = Depends(get_current_user)
) -> StandardResponse:
    """
    Get current cache configuration.
    
    Requires authentication.
    
    Returns:
        Cache configuration settings
    """
    try:
        config = cache_service.config.copy()
        
        return StandardResponse(
            success=True,
            data=config,
            message="Cache configuration retrieved"
        )
        
    except Exception as e:
        logger.error(f"Error getting cache config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache configuration: {str(e)}"
        )


@router.put("/config", response_model=StandardResponse)
async def update_cache_configuration(
    config_updates: Dict[str, Any],
    cache_service: HTTPCacheService = Depends(get_cache_service),
    current_user: Dict = Depends(get_current_user)
) -> StandardResponse:
    """
    Update cache configuration.
    
    Requires authentication.
    
    Args:
        config_updates: Configuration updates to apply
        
    Returns:
        Updated configuration
    """
    try:
        # Validate configuration keys
        valid_keys = set(cache_service.config.keys())
        invalid_keys = set(config_updates.keys()) - valid_keys
        
        if invalid_keys:
            raise ValueError(f"Invalid configuration keys: {invalid_keys}")
        
        # Update configuration
        for key, value in config_updates.items():
            cache_service.config[key] = value
        
        return StandardResponse(
            success=True,
            data=cache_service.config,
            message="Cache configuration updated"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating cache config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update cache configuration: {str(e)}"
        )


@router.post("/warm", response_model=StandardResponse)
async def warm_cache(
    keys: List[str],
    cache_service: HTTPCacheService = Depends(get_cache_service),
    current_user: Dict = Depends(get_current_user)
) -> StandardResponse:
    """
    Warm cache with specific keys.
    
    Requires authentication.
    
    Args:
        keys: List of cache keys to warm
        
    Returns:
        Warming result
    """
    try:
        # Define a warming function based on the keys
        async def warm_func(keys_to_warm):
            # This would be implemented based on your specific needs
            # For now, return empty dict
            return {}
        
        await cache_service.warm_cache(warm_func, keys)
        
        return StandardResponse(
            success=True,
            data={"keys": keys, "warmed": len(keys)},
            message=f"Cache warming initiated for {len(keys)} keys"
        )
        
    except Exception as e:
        logger.error(f"Error warming cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to warm cache: {str(e)}"
        )


@router.get("/tags", response_model=StandardResponse)
async def list_cache_tags(
    cache_service: HTTPCacheService = Depends(get_cache_service),
    current_user: Dict = Depends(get_current_user)
) -> StandardResponse:
    """
    List all cache tags currently in use.
    
    Requires authentication.
    
    Returns:
        List of tags with entry counts
    """
    try:
        tags_info = []
        
        for tag, keys in cache_service.tag_index.items():
            tags_info.append({
                "tag": tag,
                "entry_count": len(keys)
            })
        
        # Sort by entry count
        tags_info.sort(key=lambda x: x["entry_count"], reverse=True)
        
        return StandardResponse(
            success=True,
            data={
                "total_tags": len(tags_info),
                "tags": tags_info
            },
            message="Cache tags retrieved"
        )
        
    except Exception as e:
        logger.error(f"Error listing cache tags: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list cache tags: {str(e)}"
        )


@router.get("/performance", response_model=StandardResponse)
async def get_cache_performance_metrics(
    cache_service: HTTPCacheService = Depends(get_cache_service),
    current_user: Dict = Depends(get_current_user)
) -> StandardResponse:
    """
    Get detailed cache performance metrics.
    
    Requires authentication.
    
    Returns:
        Detailed performance metrics
    """
    try:
        stats = cache_service.get_stats()
        
        # Add middleware metrics if available
        from src.api.main import app
        middleware_metrics = {}
        
        for middleware in app.middleware:
            if hasattr(middleware, 'cls') and hasattr(middleware.cls, 'get_metrics'):
                if middleware.cls.__name__ == 'HTTPCacheMiddleware':
                    middleware_metrics = middleware.cls.get_metrics()
                    break
        
        return StandardResponse(
            success=True,
            data={
                "service_metrics": stats,
                "middleware_metrics": middleware_metrics,
                "recommendations": [
                    "Consider increasing TTL for stable endpoints",
                    "Use cache tags for related content invalidation",
                    "Enable compression for large responses"
                ] if stats.get("hit_rate", "0%").rstrip("%") < "50" else []
            },
            message="Cache performance metrics retrieved"
        )
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance metrics: {str(e)}"
        )