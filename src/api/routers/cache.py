"""
Cache management API endpoints.

This module provides endpoints for cache monitoring and management.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from src.core.dependencies import get_cache_dependency, get_redis_dependency
from src.services.ngx_cache_manager import NGXCacheManager
from src.services.redis_cache_service import RedisCacheService
from src.auth.auth_dependencies import has_admin_role
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/cache",
    tags=["cache"],
    dependencies=[Depends(has_admin_role)]  # Admin only endpoints
)


@router.get("/health", response_model=Dict[str, Any])
async def cache_health(
    redis: Optional[RedisCacheService] = Depends(get_redis_dependency)
) -> Dict[str, Any]:
    """
    Get cache service health status.
    
    Returns:
        Health status including connection info and metrics
    """
    if not redis:
        return {
            "status": "unavailable",
            "healthy": False,
            "message": "Redis cache not configured"
        }
    
    try:
        health = await redis.health_check()
        return health
    except Exception as e:
        logger.error(f"Error checking cache health: {e}")
        return {
            "status": "error",
            "healthy": False,
            "error": str(e)
        }


@router.get("/stats", response_model=Dict[str, Any])
async def cache_stats(
    redis: Optional[RedisCacheService] = Depends(get_redis_dependency),
    cache: Optional[NGXCacheManager] = Depends(get_cache_dependency)
) -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Cache statistics including hit rate and usage
    """
    stats = {
        "redis": None,
        "ngx_cache": None
    }
    
    if redis:
        stats["redis"] = redis.get_stats()
    
    if cache:
        stats["ngx_cache"] = await cache.get_cache_stats()
    
    if not redis and not cache:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service not available"
        )
    
    return stats


@router.post("/warm", response_model=Dict[str, Any])
async def warm_cache(
    cache: Optional[NGXCacheManager] = Depends(get_cache_dependency)
) -> Dict[str, Any]:
    """
    Warm up cache with frequently accessed data.
    
    Returns:
        Statistics of warmed entries
    """
    if not cache:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service not available"
        )
    
    try:
        stats = await cache.warm_cache()
        return {
            "status": "success",
            "warmed_entries": stats
        }
    except Exception as e:
        logger.error(f"Error warming cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to warm cache: {str(e)}"
        )


@router.delete("/clear/{namespace}", response_model=Dict[str, Any])
async def clear_cache_namespace(
    namespace: str,
    redis: Optional[RedisCacheService] = Depends(get_redis_dependency)
) -> Dict[str, Any]:
    """
    Clear all keys in a specific namespace.
    
    Args:
        namespace: Cache namespace to clear
        
    Returns:
        Number of keys deleted
    """
    if not redis:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service not available"
        )
    
    # Only allow clearing specific namespaces
    allowed_namespaces = ["test", "temp", "staging"]
    if namespace not in allowed_namespaces:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Clearing namespace '{namespace}' is not allowed"
        )
    
    try:
        # Temporarily change namespace
        original_namespace = redis.namespace
        redis.namespace = namespace
        
        deleted = await redis.clear_namespace()
        
        # Restore original namespace
        redis.namespace = original_namespace
        
        return {
            "status": "success",
            "namespace": namespace,
            "keys_deleted": deleted
        }
    except Exception as e:
        logger.error(f"Error clearing cache namespace {namespace}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.get("/key/{key}", response_model=Dict[str, Any])
async def get_cache_key(
    key: str,
    redis: Optional[RedisCacheService] = Depends(get_redis_dependency)
) -> Dict[str, Any]:
    """
    Get value for a specific cache key (debugging).
    
    Args:
        key: Cache key to retrieve
        
    Returns:
        Cached value and metadata
    """
    if not redis:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service not available"
        )
    
    try:
        value = await redis.get(key)
        exists = await redis.exists(key)
        
        return {
            "key": key,
            "exists": exists,
            "value": value,
            "type": type(value).__name__ if value else None
        }
    except Exception as e:
        logger.error(f"Error getting cache key {key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache key: {str(e)}"
        )


@router.delete("/key/{key}", response_model=Dict[str, Any])
async def delete_cache_key(
    key: str,
    redis: Optional[RedisCacheService] = Depends(get_redis_dependency)
) -> Dict[str, Any]:
    """
    Delete a specific cache key.
    
    Args:
        key: Cache key to delete
        
    Returns:
        Deletion status
    """
    if not redis:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service not available"
        )
    
    try:
        deleted = await redis.delete(key)
        
        return {
            "key": key,
            "deleted": deleted,
            "status": "success" if deleted else "key_not_found"
        }
    except Exception as e:
        logger.error(f"Error deleting cache key {key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete cache key: {str(e)}"
        )


@router.post("/invalidate/conversation/{conversation_id}", response_model=Dict[str, Any])
async def invalidate_conversation_cache(
    conversation_id: str,
    cache: Optional[NGXCacheManager] = Depends(get_cache_dependency)
) -> Dict[str, Any]:
    """
    Invalidate cache for a specific conversation.
    
    Args:
        conversation_id: Conversation ID to invalidate
        
    Returns:
        Invalidation status
    """
    if not cache:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service not available"
        )
    
    try:
        deleted = await cache.delete_conversation(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "invalidated": deleted,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error invalidating conversation cache {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate cache: {str(e)}"
        )


@router.post("/invalidate/customer/{customer_id}", response_model=Dict[str, Any])
async def invalidate_customer_cache(
    customer_id: str,
    cache: Optional[NGXCacheManager] = Depends(get_cache_dependency)
) -> Dict[str, Any]:
    """
    Invalidate cache for a specific customer.
    
    Args:
        customer_id: Customer ID to invalidate
        
    Returns:
        Invalidation status
    """
    if not cache:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service not available"
        )
    
    try:
        # Invalidate customer data
        deleted_customer = await cache.cache.delete(f"{cache.keys['customer']}:{customer_id}")
        
        # Also invalidate related tier detections
        # This would need to scan for related keys in production
        
        return {
            "customer_id": customer_id,
            "invalidated": deleted_customer,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error invalidating customer cache {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate cache: {str(e)}"
        )