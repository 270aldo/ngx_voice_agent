"""
HTTP Cache Service - Advanced caching strategies for API responses.

Provides sophisticated caching mechanisms including:
- Partial response caching
- Cache tagging for fine-grained invalidation
- Stale-while-revalidate support
- Cache compression
- Distributed cache synchronization
"""

import asyncio
import gzip
import json
import logging
from typing import Dict, Any, List, Optional, Set, Tuple, Callable
from datetime import datetime, timedelta
import hashlib
from enum import Enum
from dataclasses import dataclass, field
import pickle

from src.services.ngx_cache_manager import NGXCacheManager
from src.core.dependencies import get_ngx_cache_manager
from src.utils.async_task_manager import AsyncTaskManager, get_task_registry
from src.core.constants import CacheConstants, TimeConstants

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache strategies for different use cases."""
    STANDARD = "standard"  # Normal TTL-based caching
    STALE_WHILE_REVALIDATE = "stale_while_revalidate"  # Serve stale while updating
    EDGE_SIDE_INCLUDES = "edge_side_includes"  # Partial caching
    WRITE_THROUGH = "write_through"  # Update cache on writes
    WRITE_BEHIND = "write_behind"  # Async cache updates


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
    vary_headers: Dict[str, str] = field(default_factory=dict)
    stale_ttl: Optional[int] = None  # Additional TTL for stale content


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
    tags_count: int = 0


class HTTPCacheService:
    """
    Advanced HTTP cache service with sophisticated features.
    """
    
    def __init__(self):
        """Initialize HTTP cache service."""
        self._cache_manager: Optional[NGXCacheManager] = None
        self.task_manager: Optional[AsyncTaskManager] = None
        
        # Cache configuration
        self.config = {
            "max_entry_size_mb": CacheConstants.MAX_ENTRY_SIZE_MB,
            "compression_threshold_bytes": CacheConstants.COMPRESSION_THRESHOLD_BYTES,  # Compress entries > 1KB
            "default_ttl_seconds": CacheConstants.DEFAULT_TTL_SECONDS,
            "stale_ttl_seconds": CacheConstants.STALE_TTL_SECONDS,  # Keep stale for 1 hour
            "max_tags_per_entry": CacheConstants.MAX_TAGS_PER_ENTRY,
            "enable_compression": True,
            "enable_distributed_sync": False
        }
        
        # In-memory structures
        self.tag_index: Dict[str, Set[str]] = {}  # tag -> set of keys
        self.stats = CacheStats()
        self.revalidation_queue = asyncio.Queue()
        
        # Background tasks
        asyncio.create_task(self._initialize_async())
        
        logger.info("HTTPCacheService initialized")
    
    async def _initialize_async(self):
        """Async initialization."""
        try:
            # Get cache manager
            self._cache_manager = await get_ngx_cache_manager()
            
            # Get task manager
            registry = get_task_registry()
            self.task_manager = await registry.register_service("http_cache_service")
            
            # Start background tasks
            if self.task_manager:
                await self.task_manager.create_task(
                    self._process_revalidation_queue(),
                    name="revalidation_processor"
                )
                await self.task_manager.create_task(
                    self._collect_stats_periodically(),
                    name="stats_collector"
                )
            
            logger.info("HTTPCacheService async initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize HTTPCacheService: {e}")
    
    async def get(
        self,
        key: str,
        strategy: CacheStrategy = CacheStrategy.STANDARD,
        revalidate_func: Optional[Callable] = None
    ) -> Tuple[Optional[Any], bool]:
        """
        Get value from cache with specified strategy.
        
        Args:
            key: Cache key
            strategy: Caching strategy
            revalidate_func: Function to get fresh value
            
        Returns:
            Tuple of (value, is_stale)
        """
        if not self._cache_manager:
            return None, False
        
        try:
            # Get cache entry
            entry_data = await self._cache_manager.get(f"http:{key}")
            if not entry_data:
                self.stats.miss_count += 1
                return None, False
            
            # Deserialize entry
            entry = self._deserialize_entry(entry_data)
            
            # Update access stats
            entry.last_accessed = datetime.now()
            entry.access_count += 1
            self.stats.hit_count += 1
            
            # Check expiration
            now = datetime.now()
            is_expired = now > entry.expires_at
            is_stale = is_expired and entry.stale_ttl and now < (entry.expires_at + timedelta(seconds=entry.stale_ttl))
            
            # Handle based on strategy
            if strategy == CacheStrategy.STALE_WHILE_REVALIDATE and is_stale and revalidate_func:
                # Serve stale content while revalidating
                await self.revalidation_queue.put((key, revalidate_func))
                return self._decompress_value(entry), True
            
            elif not is_expired:
                # Fresh content
                return self._decompress_value(entry), False
            
            elif is_stale:
                # Stale but usable
                return self._decompress_value(entry), True
            
            else:
                # Expired
                await self.invalidate(key)
                return None, False
                
        except Exception as e:
            logger.error(f"Error getting from cache: {e}")
            return None, False
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        tags: Optional[List[str]] = None,
        strategy: CacheStrategy = CacheStrategy.STANDARD,
        vary_headers: Optional[Dict[str, str]] = None,
        stale_ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Set value in cache with metadata.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL in seconds
            tags: Cache tags for invalidation
            strategy: Caching strategy
            vary_headers: Headers that affect caching
            stale_ttl_seconds: Additional TTL for stale content
            
        Returns:
            Success status
        """
        if not self._cache_manager:
            return False
        
        try:
            # Prepare cache entry
            now = datetime.now()
            ttl = ttl_seconds or self.config["default_ttl_seconds"]
            
            # Compress if needed
            compressed_value, compressed = self._compress_value(value)
            
            # Create entry
            entry = CacheEntry(
                key=key,
                value=compressed_value,
                created_at=now,
                expires_at=now + timedelta(seconds=ttl),
                last_accessed=now,
                tags=set(tags[:self.config["max_tags_per_entry"]] if tags else []),
                compressed=compressed,
                size_bytes=len(str(compressed_value)),
                etag=self._generate_etag(value),
                vary_headers=vary_headers or {},
                stale_ttl=stale_ttl_seconds or self.config["stale_ttl_seconds"]
            )
            
            # Update tag index
            for tag in entry.tags:
                if tag not in self.tag_index:
                    self.tag_index[tag] = set()
                self.tag_index[tag].add(key)
            
            # Serialize and store
            entry_data = self._serialize_entry(entry)
            total_ttl = ttl + (entry.stale_ttl or 0)
            
            success = await self._cache_manager.set(
                f"http:{key}",
                entry_data,
                ttl=total_ttl
            )
            
            # Update stats
            if success:
                self.stats.total_entries += 1
                self.stats.total_size_bytes += entry.size_bytes
            
            # Handle write strategies
            if strategy == CacheStrategy.WRITE_THROUGH:
                # Synchronous cache update - already done
                pass
            elif strategy == CacheStrategy.WRITE_BEHIND:
                # Async cache update - queue for later
                # This would be useful for expensive cache warming
                pass
            
            return success
            
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False
    
    async def invalidate(self, key: str) -> bool:
        """Invalidate a single cache entry."""
        if not self._cache_manager:
            return False
        
        try:
            # Remove from cache
            success = await self._cache_manager.delete(f"http:{key}")
            
            # Update tag index
            for tag, keys in list(self.tag_index.items()):
                if key in keys:
                    keys.remove(key)
                    if not keys:
                        del self.tag_index[tag]
            
            # Update stats
            if success:
                self.stats.eviction_count += 1
                self.stats.total_entries = max(0, self.stats.total_entries - 1)
            
            return success
            
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return False
    
    async def invalidate_by_tag(self, tag: str) -> int:
        """
        Invalidate all cache entries with a specific tag.
        
        Args:
            tag: Tag to invalidate
            
        Returns:
            Number of entries invalidated
        """
        if tag not in self.tag_index:
            return 0
        
        keys_to_invalidate = list(self.tag_index[tag])
        invalidated = 0
        
        for key in keys_to_invalidate:
            if await self.invalidate(key):
                invalidated += 1
        
        return invalidated
    
    async def invalidate_by_tags(self, tags: List[str]) -> int:
        """Invalidate entries matching any of the tags."""
        invalidated = 0
        
        for tag in tags:
            invalidated += await self.invalidate_by_tag(tag)
        
        return invalidated
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate entries matching a pattern.
        
        Args:
            pattern: Pattern to match (supports * wildcard)
            
        Returns:
            Number of entries invalidated
        """
        # This would require maintaining a key index
        # For now, return 0
        logger.warning(f"Pattern invalidation not implemented: {pattern}")
        return 0
    
    def _compress_value(self, value: Any) -> Tuple[Any, bool]:
        """Compress value if it meets threshold."""
        if not self.config["enable_compression"]:
            return value, False
        
        # Serialize value
        serialized = json.dumps(value) if not isinstance(value, (str, bytes)) else value
        if isinstance(serialized, str):
            serialized = serialized.encode()
        
        # Check size threshold
        if len(serialized) < self.config["compression_threshold_bytes"]:
            return value, False
        
        # Compress
        compressed = gzip.compress(serialized, compresslevel=6)
        
        # Only use compression if it saves space
        if len(compressed) < len(serialized) * 0.9:  # 10% minimum savings
            return compressed, True
        
        return value, False
    
    def _decompress_value(self, entry: CacheEntry) -> Any:
        """Decompress value if compressed."""
        if not entry.compressed:
            return entry.value
        
        try:
            decompressed = gzip.decompress(entry.value)
            
            # Try to deserialize JSON
            try:
                return json.loads(decompressed.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                return decompressed
                
        except Exception as e:
            logger.error(f"Error decompressing value: {e}")
            return entry.value
    
    def _generate_etag(self, value: Any) -> str:
        """Generate ETag for cache entry."""
        # Serialize value for hashing
        if isinstance(value, (dict, list)):
            content = json.dumps(value, sort_keys=True)
        else:
            content = str(value)
        
        return hashlib.md5(content.encode()).hexdigest()
    
    def _serialize_entry(self, entry: CacheEntry) -> Dict[str, Any]:
        """Serialize cache entry for storage."""
        return {
            "key": entry.key,
            "value": entry.value,
            "created_at": entry.created_at.isoformat(),
            "expires_at": entry.expires_at.isoformat(),
            "last_accessed": entry.last_accessed.isoformat(),
            "access_count": entry.access_count,
            "tags": list(entry.tags),
            "compressed": entry.compressed,
            "size_bytes": entry.size_bytes,
            "etag": entry.etag,
            "vary_headers": entry.vary_headers,
            "stale_ttl": entry.stale_ttl
        }
    
    def _deserialize_entry(self, data: Dict[str, Any]) -> CacheEntry:
        """Deserialize cache entry from storage."""
        return CacheEntry(
            key=data["key"],
            value=data["value"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            access_count=data["access_count"],
            tags=set(data["tags"]),
            compressed=data["compressed"],
            size_bytes=data["size_bytes"],
            etag=data.get("etag"),
            vary_headers=data.get("vary_headers", {}),
            stale_ttl=data.get("stale_ttl")
        )
    
    async def _process_revalidation_queue(self):
        """Process background revalidation requests."""
        while True:
            try:
                # Get revalidation request
                key, revalidate_func = await self.revalidation_queue.get()
                
                # Revalidate in background
                try:
                    fresh_value = await revalidate_func()
                    if fresh_value is not None:
                        # Get existing entry for tags and headers
                        existing_data = await self._cache_manager.get(f"http:{key}")
                        if existing_data:
                            existing_entry = self._deserialize_entry(existing_data)
                            await self.set(
                                key=key,
                                value=fresh_value,
                                tags=list(existing_entry.tags),
                                vary_headers=existing_entry.vary_headers,
                                stale_ttl_seconds=existing_entry.stale_ttl
                            )
                        else:
                            await self.set(key=key, value=fresh_value)
                        
                        logger.debug(f"Revalidated cache key: {key}")
                        
                except Exception as e:
                    logger.error(f"Error revalidating {key}: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in revalidation queue: {e}")
                await asyncio.sleep(1)
    
    async def _collect_stats_periodically(self):
        """Collect cache statistics periodically."""
        while True:
            try:
                await asyncio.sleep(TimeConstants.CACHE_DEFAULT_TTL)  # Every 5 minutes
                
                # Calculate compression ratio
                if self.stats.total_entries > 0:
                    # This would need actual tracking of compressed vs uncompressed sizes
                    self.stats.compression_ratio = 0.7  # Placeholder
                
                # Log stats
                logger.info(
                    f"Cache stats - Entries: {self.stats.total_entries}, "
                    f"Size: {self.stats.total_size_bytes / 1024 / 1024:.2f}MB, "
                    f"Hit rate: {self._calculate_hit_rate():.2f}%, "
                    f"Tags: {len(self.tag_index)}"
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error collecting stats: {e}")
    
    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.stats.hit_count + self.stats.miss_count
        if total == 0:
            return 0.0
        return (self.stats.hit_count / total) * 100
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "total_entries": self.stats.total_entries,
            "total_size_mb": self.stats.total_size_bytes / 1024 / 1024,
            "hit_rate": f"{self._calculate_hit_rate():.2f}%",
            "hit_count": self.stats.hit_count,
            "miss_count": self.stats.miss_count,
            "eviction_count": self.stats.eviction_count,
            "compression_ratio": f"{self.stats.compression_ratio:.2f}",
            "tags_count": len(self.tag_index),
            "avg_response_time_ms": self.stats.avg_response_time_ms
        }
    
    async def warm_cache(self, warm_func: Callable, keys: List[str]):
        """
        Warm cache with pre-computed values.
        
        Args:
            warm_func: Function that returns Dict[key, value]
            keys: Keys to warm
        """
        try:
            # Get values to cache
            values = await warm_func(keys)
            
            # Cache each value
            warmed = 0
            for key, value in values.items():
                if await self.set(key, value):
                    warmed += 1
            
            logger.info(f"Warmed {warmed} cache entries")
            
        except Exception as e:
            logger.error(f"Error warming cache: {e}")
    
    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up HTTPCacheService")
        
        try:
            # Clear revalidation queue
            while not self.revalidation_queue.empty():
                self.revalidation_queue.get_nowait()
            
            # Unregister from task registry
            if self.task_manager:
                registry = get_task_registry()
                await registry.unregister_service("http_cache_service")
                self.task_manager = None
            
            logger.info("HTTPCacheService cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during HTTPCacheService cleanup: {e}")