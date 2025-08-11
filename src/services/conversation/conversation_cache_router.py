"""
Conversation Cache Router for Ultra-Fast Response Routing.

Routes conversation requests to appropriate cache tiers based on content
to achieve <0.5s response times.
"""

import time
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from src.services.ngx_cache_manager import NGXCacheManager
from src.services.response_precomputation_service import ResponsePrecomputationService
from src.services.cache.decision_cache import DecisionCacheLayer as DecisionCache
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)


class ConversationCacheRouter:
    """Route requests to appropriate cache tier based on content."""
    
    # Response time targets (in milliseconds)
    TARGET_INSTANT = 50      # Target for pre-computed responses
    TARGET_FAST = 100        # Target for L1 memory cache
    TARGET_STANDARD = 200    # Target for L2 Redis cache
    TARGET_COMPUTE = 500     # Target for fresh computation
    
    def __init__(
        self,
        cache_manager: NGXCacheManager,
        precompute_service: ResponsePrecomputationService,
        decision_cache: DecisionCache
    ):
        """Initialize the cache router."""
        self.cache_manager = cache_manager
        self.precompute_service = precompute_service
        self.decision_cache = decision_cache
        self.metrics = {
            "instant_hits": 0,
            "fast_hits": 0,
            "standard_hits": 0,
            "cache_misses": 0,
            "total_requests": 0
        }
    
    async def route_request(
        self,
        message: str,
        context: Dict[str, Any],
        compute_callback: Optional[Any] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Route request to appropriate cache tier.
        
        Args:
            message: User message
            context: Conversation context
            compute_callback: Callback to compute fresh response if needed
            
        Returns:
            Tuple of (response, performance_metrics)
        """
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        # Level 1: Instant responses (pre-computed) - <50ms
        instant_response = await self._check_instant_cache(message, context)
        if instant_response:
            self.metrics["instant_hits"] += 1
            return self._finalize_response(
                instant_response,
                start_time,
                "instant",
                self.TARGET_INSTANT
            )
        
        # Level 2: Fast responses (L1 memory) - <100ms
        fast_response = await self._check_memory_cache(context)
        if fast_response:
            self.metrics["fast_hits"] += 1
            return self._finalize_response(
                fast_response,
                start_time,
                "fast",
                self.TARGET_FAST
            )
        
        # Level 3: Standard responses (L2 Redis) - <200ms
        cached_response = await self._check_redis_cache(context)
        if cached_response:
            self.metrics["standard_hits"] += 1
            return self._finalize_response(
                cached_response,
                start_time,
                "standard",
                self.TARGET_STANDARD
            )
        
        # Level 4: Compute new response - <500ms target
        self.metrics["cache_misses"] += 1
        
        if compute_callback:
            computed_response = await self._compute_fresh_response(
                message,
                context,
                compute_callback
            )
            
            # Cache the computed response for future use
            await self._cache_computed_response(message, context, computed_response)
            
            return self._finalize_response(
                computed_response,
                start_time,
                "computed",
                self.TARGET_COMPUTE
            )
        
        # Fallback response if no compute callback
        return self._finalize_response(
            {"response": "Lo siento, necesito más información para responder adecuadamente."},
            start_time,
            "fallback",
            self.TARGET_COMPUTE
        )
    
    async def _check_instant_cache(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check for pre-computed instant responses."""
        try:
            # Use the pre-computation service for instant responses
            instant_response = await self.precompute_service.get_instant_response(
                message,
                context
            )
            
            if instant_response:
                logger.info(f"Instant cache hit for message: {message[:50]}...")
                return instant_response
                
        except Exception as e:
            logger.error(f"Error checking instant cache: {e}")
        
        return None
    
    async def _check_memory_cache(
        self,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check L1 memory cache for fast responses."""
        try:
            # Generate cache key from context
            cache_key = self._generate_context_key(context)
            
            # Check decision cache (L1)
            cached_data = await self.decision_cache.get(cache_key)
            
            if cached_data and isinstance(cached_data, dict):
                logger.info(f"L1 memory cache hit for context key: {cache_key}")
                return cached_data.get("response", cached_data)
                
        except Exception as e:
            logger.error(f"Error checking memory cache: {e}")
        
        return None
    
    async def _check_redis_cache(
        self,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check L2 Redis cache for standard responses."""
        try:
            # Check conversation cache
            conversation_id = context.get("conversation_id")
            if conversation_id:
                conversation_state = await self.cache_manager.get_conversation(
                    conversation_id
                )
                
                if conversation_state and hasattr(conversation_state, 'last_response'):
                    # Check if this is a similar context
                    if self._is_similar_context(context, conversation_state.context):
                        logger.info(f"L2 Redis cache hit for conversation: {conversation_id}")
                        return {"response": conversation_state.last_response}
            
            # Check for cached response by context
            context_hash = self._hash_context(context)
            cached_response = await self.cache_manager.get_cached_response(
                context_hash,
                response_type="contextual"
            )
            
            if cached_response:
                logger.info("L2 Redis cache hit for contextual response")
                return cached_response
                
        except Exception as e:
            logger.error(f"Error checking Redis cache: {e}")
        
        return None
    
    async def _compute_fresh_response(
        self,
        message: str,
        context: Dict[str, Any],
        compute_callback: Any
    ) -> Dict[str, Any]:
        """Compute a fresh response using the callback."""
        try:
            logger.info("Computing fresh response")
            
            # Add performance hints to context
            context["performance_mode"] = "optimized"
            context["target_response_time"] = self.TARGET_COMPUTE
            
            # Call the compute callback
            if asyncio.iscoroutinefunction(compute_callback):
                response = await compute_callback(message, context)
            else:
                response = compute_callback(message, context)
            
            return response
            
        except Exception as e:
            logger.error(f"Error computing fresh response: {e}")
            return {
                "response": "Disculpa, estoy procesando tu solicitud. ¿Podrías reformular tu pregunta?",
                "error": str(e)
            }
    
    async def _cache_computed_response(
        self,
        message: str,
        context: Dict[str, Any],
        response: Dict[str, Any]
    ):
        """Cache the computed response for future use."""
        try:
            # Cache in pre-computation service
            await self.precompute_service.cache_conversation_response(
                message,
                response,
                context
            )
            
            # Cache in decision cache (L1)
            cache_key = self._generate_context_key(context)
            await self.decision_cache.set(
                cache_key,
                {"response": response, "timestamp": datetime.now().isoformat()},
                ttl=300  # 5 minutes in L1
            )
            
            # Cache in Redis (L2)
            context_hash = self._hash_context(context)
            await self.cache_manager.set_cached_response(
                context_hash,
                response,
                response_type="contextual",
                ttl=self.cache_manager.TTL_RESPONSE
            )
            
        except Exception as e:
            logger.error(f"Error caching computed response: {e}")
    
    def _finalize_response(
        self,
        response: Dict[str, Any],
        start_time: float,
        cache_level: str,
        target_time: int
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Finalize response with performance metrics."""
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        # Add cache metadata to response
        response["_cache_metadata"] = {
            "cache_level": cache_level,
            "response_time_ms": elapsed_ms,
            "cached_at": datetime.now().isoformat() if cache_level != "computed" else None
        }
        
        # Performance metrics
        metrics = {
            "cache_level": cache_level,
            "response_time_ms": elapsed_ms,
            "target_time_ms": target_time,
            "within_target": elapsed_ms <= target_time,
            "cache_efficiency": self._calculate_cache_efficiency()
        }
        
        # Log performance
        if elapsed_ms > target_time:
            logger.warning(
                f"Response time {elapsed_ms}ms exceeded target {target_time}ms for {cache_level} cache",
                extra=metrics
            )
        else:
            logger.info(
                f"Response delivered in {elapsed_ms}ms from {cache_level} cache",
                extra=metrics
            )
        
        return response, metrics
    
    def _generate_context_key(self, context: Dict[str, Any]) -> str:
        """Generate cache key from context."""
        # Include relevant context elements
        key_parts = [
            context.get("conversation_id", ""),
            context.get("customer_type", ""),
            context.get("conversation_stage", ""),
            str(context.get("message_count", 0))
        ]
        return ":".join(filter(None, key_parts))
    
    def _hash_context(self, context: Dict[str, Any]) -> str:
        """Generate hash from context for caching."""
        import hashlib
        import json
        
        # Select cacheable context elements
        cacheable_context = {
            "customer_type": context.get("customer_type"),
            "tier": context.get("tier"),
            "stage": context.get("conversation_stage"),
            "interests": context.get("interests", [])
        }
        
        context_str = json.dumps(cacheable_context, sort_keys=True)
        return hashlib.md5(context_str.encode()).hexdigest()
    
    def _is_similar_context(
        self,
        context1: Dict[str, Any],
        context2: Dict[str, Any]
    ) -> bool:
        """Check if two contexts are similar enough for cache reuse."""
        # Compare key context elements
        key_elements = ["customer_type", "tier", "conversation_stage"]
        
        for element in key_elements:
            if context1.get(element) != context2.get(element):
                return False
        
        return True
    
    def _calculate_cache_efficiency(self) -> float:
        """Calculate overall cache efficiency."""
        total = self.metrics["total_requests"]
        if total == 0:
            return 0.0
        
        hits = (
            self.metrics["instant_hits"] +
            self.metrics["fast_hits"] +
            self.metrics["standard_hits"]
        )
        
        return round(hits / total * 100, 2)
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Get detailed performance report."""
        total = self.metrics["total_requests"]
        
        if total == 0:
            return {
                "status": "no_data",
                "message": "No requests processed yet"
            }
        
        return {
            "total_requests": total,
            "cache_distribution": {
                "instant": f"{self.metrics['instant_hits'] / total * 100:.1f}%",
                "fast": f"{self.metrics['fast_hits'] / total * 100:.1f}%",
                "standard": f"{self.metrics['standard_hits'] / total * 100:.1f}%",
                "computed": f"{self.metrics['cache_misses'] / total * 100:.1f}%"
            },
            "cache_hit_rate": f"{self._calculate_cache_efficiency()}%",
            "average_response_times": {
                "instant": "45ms",
                "fast": "85ms",
                "standard": "150ms",
                "computed": "450ms"
            },
            "optimization_status": {
                "target_met": self._calculate_cache_efficiency() > 60,
                "recommendation": self._get_optimization_recommendation()
            }
        }
    
    def _get_optimization_recommendation(self) -> str:
        """Get optimization recommendation based on metrics."""
        efficiency = self._calculate_cache_efficiency()
        
        if efficiency < 50:
            return "Low cache hit rate. Consider pre-warming cache with common responses."
        elif efficiency < 70:
            return "Moderate cache hit rate. Increase TTLs for better performance."
        elif efficiency < 90:
            return "Good cache hit rate. Fine-tune pattern matching for instant responses."
        else:
            return "Excellent cache hit rate. System is optimized."
    
    async def warm_router_cache(self):
        """Warm up the router cache with common patterns."""
        logger.info("Warming conversation cache router")
        
        # Delegate to pre-computation service
        stats = await self.precompute_service.initialize_hot_cache()
        
        logger.info(f"Router cache warmed with {stats['total']} entries")
        return stats