"""
Deprecation warnings for legacy cache services.

This module adds deprecation warnings to legacy cache services during the migration
to the consolidated CacheService.
"""

import warnings
import functools
from typing import Any, Callable

def deprecated_service(service_name: str, replacement: str = "CacheService", version: str = "v2.0.0"):
    """
    Decorator to mark cache services as deprecated.
    
    Args:
        service_name: Name of the deprecated service
        replacement: Name of the replacement service
        version: Version when the service will be removed
    """
    def decorator(cls):
        original_init = cls.__init__
        
        @functools.wraps(original_init)
        def new_init(self, *args, **kwargs):
            warnings.warn(
                f"{service_name} is deprecated and will be removed in {version}. "
                f"Please migrate to {replacement}. Set USE_CONSOLIDATED_CACHE=True "
                f"to use the new consolidated cache system.",
                DeprecationWarning,
                stacklevel=2
            )
            original_init(self, *args, **kwargs)
        
        cls.__init__ = new_init
        
        # Add deprecation notice to docstring
        if cls.__doc__:
            cls.__doc__ = f"""⚠️  DEPRECATED: {cls.__doc__}
            
This class is deprecated and will be removed in {version}.
Please migrate to {replacement}."""
        
        return cls
    return decorator


def deprecated_function(func_name: str, replacement: str = "consolidated cache function", version: str = "v2.0.0"):
    """
    Decorator to mark functions as deprecated.
    
    Args:
        func_name: Name of the deprecated function
        replacement: Name of the replacement function
        version: Version when the function will be removed
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func_name} is deprecated and will be removed in {version}. "
                f"Please migrate to {replacement}.",
                DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Apply deprecation warnings to existing services
def apply_deprecation_warnings():
    """Apply deprecation warnings to legacy cache services."""
    try:
        # Mark RedisCacheService as deprecated
        from src.services.redis_cache_service import RedisCacheService
        RedisCacheService = deprecated_service("RedisCacheService")(RedisCacheService)
    except ImportError:
        pass
    
    try:
        # Mark NGXCacheManager as deprecated
        from src.services.ngx_cache_manager import NGXCacheManager
        NGXCacheManager = deprecated_service("NGXCacheManager")(NGXCacheManager)
    except ImportError:
        pass
    
    try:
        # Mark HTTPCacheService as deprecated
        from src.services.http_cache_service import HTTPCacheService
        HTTPCacheService = deprecated_service("HTTPCacheService")(HTTPCacheService)
    except ImportError:
        pass
    
    try:
        # Mark ResponsePrecomputationService as deprecated
        from src.services.response_precomputation_service import ResponsePrecomputationService
        ResponsePrecomputationService = deprecated_service("ResponsePrecomputationService")(ResponsePrecomputationService)
    except ImportError:
        pass
    
    try:
        # Mark cache factory functions as deprecated
        from src.services.cache_factory import get_cache_instance as legacy_get_cache_instance
        legacy_get_cache_instance = deprecated_function("cache_factory.get_cache_instance")(legacy_get_cache_instance)
    except ImportError:
        pass