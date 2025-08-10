"""
Cache interfaces for dependency inversion.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Protocol


class CacheInterface(Protocol):
    """Protocol for cache implementations."""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        ...
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL."""
        ...
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        ...
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        ...
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern."""
        ...
    
    def is_connected(self) -> bool:
        """Check if cache is connected."""
        ...


class CacheableService(ABC):
    """Base class for services that can use caching."""
    
    def __init__(self, cache: Optional[CacheInterface] = None):
        self._cache = cache
    
    @property
    def cache(self) -> Optional[CacheInterface]:
        """Get cache instance."""
        return self._cache
    
    @cache.setter
    def cache(self, value: Optional[CacheInterface]) -> None:
        """Set cache instance."""
        self._cache = value
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments."""
        import hashlib
        import json
        
        # Create deterministic key
        key_data = {
            "args": args,
            "kwargs": kwargs
        }
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"{prefix}:{key_hash}"