"""
Mock Redis implementation for testing without actual Redis server.
"""

import json
import time
from typing import Any, Dict, Optional, List
import asyncio
from datetime import datetime

class MockRedis:
    """In-memory Redis mock for testing."""
    
    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.expiry: Dict[str, float] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        async with self._lock:
            # Check if key exists and not expired
            if key in self.expiry and time.time() > self.expiry[key]:
                del self.data[key]
                del self.expiry[key]
                return None
            
            return self.data.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set key-value with optional expiry."""
        async with self._lock:
            self.data[key] = value
            
            if ex:
                self.expiry[key] = time.time() + ex
            
            return True
    
    async def delete(self, key: str) -> int:
        """Delete key."""
        async with self._lock:
            if key in self.data:
                del self.data[key]
                if key in self.expiry:
                    del self.expiry[key]
                return 1
            return 0
    
    async def exists(self, key: str) -> int:
        """Check if key exists."""
        async with self._lock:
            if key in self.expiry and time.time() > self.expiry[key]:
                del self.data[key]
                del self.expiry[key]
                return 0
            
            return 1 if key in self.data else 0
    
    async def expire(self, key: str, seconds: int) -> int:
        """Set expiry for key."""
        async with self._lock:
            if key in self.data:
                self.expiry[key] = time.time() + seconds
                return 1
            return 0
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key."""
        async with self._lock:
            if key not in self.expiry:
                return -1 if key in self.data else -2
            
            ttl = int(self.expiry[key] - time.time())
            return max(ttl, 0)
    
    async def hset(self, name: str, key: str, value: str) -> int:
        """Set hash field."""
        async with self._lock:
            if name not in self.data:
                self.data[name] = {}
            
            is_new = key not in self.data[name]
            self.data[name][key] = value
            return 1 if is_new else 0
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field."""
        async with self._lock:
            if name in self.data and isinstance(self.data[name], dict):
                return self.data[name].get(key)
            return None
    
    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields."""
        async with self._lock:
            if name in self.data and isinstance(self.data[name], dict):
                return self.data[name].copy()
            return {}
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        async with self._lock:
            if name not in self.data or not isinstance(self.data[name], dict):
                return 0
            
            deleted = 0
            for key in keys:
                if key in self.data[name]:
                    del self.data[name][key]
                    deleted += 1
            
            if not self.data[name]:
                del self.data[name]
            
            return deleted
    
    async def ping(self) -> bool:
        """Check connection."""
        return True
    
    async def flushdb(self) -> bool:
        """Clear all data."""
        async with self._lock:
            self.data.clear()
            self.expiry.clear()
            return True
    
    async def close(self):
        """Close connection (no-op for mock)."""
        pass


class MockRedisCacheService:
    """Mock Redis cache service for testing."""
    
    def __init__(self):
        self.redis = MockRedis()
        self.connected = True
    
    async def initialize(self) -> bool:
        """Initialize mock cache."""
        return True
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        value = await self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError) as e:
                logger.debug(f"Failed to parse JSON for key {key}: {e}")
                return value
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set cached value."""
        try:
            if not isinstance(value, str):
                value = json.dumps(value)
            return await self.redis.set(key, value, ex=ttl)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to set value for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        result = await self.redis.delete(key)
        return result > 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        result = await self.redis.exists(key)
        return result > 0
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern."""
        # Simple pattern matching for mock
        deleted = 0
        keys_to_delete = []
        
        for key in list(self.redis.data.keys()):
            if pattern.replace("*", "") in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            if await self.redis.delete(key):
                deleted += 1
        
        return deleted
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "connected": self.connected,
            "keys": len(self.redis.data),
            "memory_usage": "N/A (mock)",
            "hit_rate": 0.0,
            "type": "mock"
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check cache health."""
        return {
            "status": "healthy",
            "latency_ms": 0.1,
            "connected": self.connected,
            "type": "mock"
        }
    
    def is_connected(self) -> bool:
        """Check if connected."""
        return self.connected
    
    async def close(self):
        """Close mock connection."""
        await self.redis.close()
        self.connected = False