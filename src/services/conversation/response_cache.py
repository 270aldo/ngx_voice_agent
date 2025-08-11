"""
Simple response cache for GPT-4o responses.

Caches responses based on message content and context to reduce API calls.
"""
import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ResponseCache:
    """
    In-memory cache for GPT responses.
    
    Uses message content and emotional context as cache key.
    TTL: 30 minutes for responses.
    """
    
    def __init__(self, ttl_minutes: int = 30):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        
    def _generate_key(self, message: str, context: Dict[str, Any]) -> str:
        """Generate cache key from message and context."""
        # Include only relevant context fields
        cache_context = {
            "emotional_state": context.get("emotional_state", "neutral"),
            "has_price_concern": context.get("has_price_concern", False),
            "conversation_phase": context.get("conversation_phase", "exploration"),
        }
        
        # Create deterministic key
        key_data = f"{message.lower().strip()}:{json.dumps(cache_context, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, message: str, context: Dict[str, Any]) -> Optional[str]:
        """Get cached response if available and not expired."""
        key = self._generate_key(message, context)
        
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() < entry["expires_at"]:
                logger.info(f"Cache hit for message: {message[:30]}...")
                return entry["response"]
            else:
                # Remove expired entry
                del self.cache[key]
                
        return None
    
    def set(self, message: str, context: Dict[str, Any], response: str) -> None:
        """Cache a response."""
        key = self._generate_key(message, context)
        
        self.cache[key] = {
            "response": response,
            "expires_at": datetime.now() + self.ttl,
            "created_at": datetime.now()
        }
        
        logger.info(f"Cached response for message: {message[:30]}...")
        
        # Clean old entries if cache is getting large
        if len(self.cache) > 1000:
            self._cleanup_expired()
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self.cache.items()
            if now >= entry["expires_at"]
        ]
        
        for key in expired_keys:
            del self.cache[key]
            
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def clear(self) -> None:
        """Clear all cached responses."""
        self.cache.clear()
        logger.info("Response cache cleared")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.cache)
        
        if total_entries == 0:
            return {
                "total_entries": 0,
                "expired_entries": 0,
                "active_entries": 0,
                "cache_size_bytes": 0
            }
        
        now = datetime.now()
        expired = sum(1 for entry in self.cache.values() if now >= entry["expires_at"])
        
        # Estimate memory size
        cache_size = sum(
            len(entry["response"]) for entry in self.cache.values()
        )
        
        return {
            "total_entries": total_entries,
            "expired_entries": expired,
            "active_entries": total_entries - expired,
            "cache_size_bytes": cache_size
        }


# Global cache instance
response_cache = ResponseCache()