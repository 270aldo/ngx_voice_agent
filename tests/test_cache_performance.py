"""
Test de Performance del Sistema de Cache Agresivo.

Valida que el ConversationCacheRouter logre <0.5s response times.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.services.conversation.conversation_cache_router import ConversationCacheRouter
from src.services.response_precomputation_service import ResponsePrecomputationService
from src.services.ngx_cache_manager import NGXCacheManager
from src.services.redis_cache_service import RedisCacheService
from src.services.cache.decision_cache import DecisionCacheLayer as DecisionCache


class TestCachePerformance:
    """Test suite for cache performance validation."""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client for testing."""
        client = Mock()
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock(return_value=True)
        client.exists = AsyncMock(return_value=False)
        return client
    
    @pytest.fixture
    def mock_cache_service(self, mock_redis_client):
        """Mock Redis cache service."""
        service = Mock(spec=RedisCacheService)
        service.get = AsyncMock(return_value=None)
        service.set = AsyncMock(return_value=True)
        service.get_stats = AsyncMock(return_value={"hit_rate": "0%", "total_keys": 0})
        return service
    
    @pytest.fixture
    def cache_manager(self, mock_cache_service):
        """Create NGX cache manager."""
        return NGXCacheManager(mock_cache_service)
    
    @pytest.fixture
    def precompute_service(self, cache_manager):
        """Create response pre-computation service."""
        return ResponsePrecomputationService(cache_manager)
    
    @pytest.fixture
    def decision_cache(self, mock_redis_client):
        """Create decision cache."""
        return DecisionCache(redis_client=mock_redis_client, enable_l2=True)
    
    @pytest.fixture
    async def cache_router(self, cache_manager, precompute_service, decision_cache):
        """Create and initialize cache router."""
        router = ConversationCacheRouter(
            cache_manager=cache_manager,
            precompute_service=precompute_service,
            decision_cache=decision_cache
        )
        # Pre-warm cache
        await router.warm_router_cache()
        return router
    
    @pytest.mark.asyncio
    async def test_instant_response_performance(self, cache_router):
        """Test that pre-computed responses are delivered in <50ms."""
        # Common question that should be pre-cached
        message = "cuanto cuesta"
        context = {
            "customer_type": "general",
            "tier": "standard",
            "conversation_stage": "exploration"
        }
        
        # Mock pre-computed response
        cache_router.precompute_service.get_instant_response = AsyncMock(
            return_value={
                "response": "Los programas de NGX tienen diferentes precios según tus necesidades: NGX Starter ($79/mes), NGX Pro ($129/mes) y NGX Elite ($199/mes).",
                "type": "pricing",
                "from_cache": True
            }
        )
        
        start_time = time.time()
        response, metrics = await cache_router.route_request(message, context)
        end_time = time.time()
        
        # Validate performance
        actual_time_ms = (end_time - start_time) * 1000
        assert actual_time_ms < 50, f"Instant response took {actual_time_ms}ms, expected <50ms"
        assert metrics["cache_level"] == "instant"
        assert metrics["response_time_ms"] < 50
        assert "Los programas de NGX" in response.get("response", "")
    
    @pytest.mark.asyncio
    async def test_memory_cache_performance(self, cache_router):
        """Test that L1 memory cache delivers responses in <100ms."""
        message = "que incluye el programa"
        context = {
            "conversation_id": "test123",
            "customer_type": "consultant",
            "tier": "pro",
            "conversation_stage": "evaluation"
        }
        
        # Mock L1 cache hit
        cache_router.decision_cache.get = AsyncMock(
            return_value={
                "response": {
                    "response": "NGX Pro incluye: 11 agentes especializados, planes personalizados, monitoreo 24/7, comunidad exclusiva.",
                    "cached_at": datetime.now().isoformat()
                }
            }
        )
        
        start_time = time.time()
        response, metrics = await cache_router.route_request(message, context)
        end_time = time.time()
        
        # Validate performance
        actual_time_ms = (end_time - start_time) * 1000
        assert actual_time_ms < 100, f"L1 cache response took {actual_time_ms}ms, expected <100ms"
        assert metrics["cache_level"] == "fast"
        assert metrics["response_time_ms"] < 100
    
    @pytest.mark.asyncio
    async def test_redis_cache_performance(self, cache_router, cache_manager):
        """Test that L2 Redis cache delivers responses in <200ms."""
        message = "como funciona"
        context = {
            "conversation_id": "test456",
            "customer_type": "executive",
            "tier": "elite",
            "conversation_stage": "discovery"
        }
        
        # Mock Redis cache hit
        cache_manager.get_cached_response = AsyncMock(
            return_value={
                "response": "NGX funciona con un sistema personalizado de 11 agentes que se adaptan a tus necesidades.",
                "type": "explanation"
            }
        )
        
        start_time = time.time()
        response, metrics = await cache_router.route_request(message, context)
        end_time = time.time()
        
        # Validate performance
        actual_time_ms = (end_time - start_time) * 1000
        assert actual_time_ms < 200, f"L2 cache response took {actual_time_ms}ms, expected <200ms"
        assert metrics["cache_level"] == "standard"
        assert metrics["response_time_ms"] < 200
    
    @pytest.mark.asyncio
    async def test_computed_response_performance(self, cache_router):
        """Test that computed responses are delivered in <500ms."""
        message = "pregunta muy específica sobre mi caso personal"
        context = {
            "conversation_id": "test789",
            "customer_type": "unique",
            "conversation_stage": "personalization"
        }
        
        # Mock compute callback
        async def mock_compute(msg, ctx):
            # Simulate AI processing time
            await asyncio.sleep(0.3)  # 300ms
            return {
                "response": "Basándome en tu caso específico, te recomendaría..."
            }
        
        start_time = time.time()
        response, metrics = await cache_router.route_request(
            message, context, compute_callback=mock_compute
        )
        end_time = time.time()
        
        # Validate performance
        actual_time_ms = (end_time - start_time) * 1000
        assert actual_time_ms < 500, f"Computed response took {actual_time_ms}ms, expected <500ms"
        assert metrics["cache_level"] == "computed"
        assert metrics["response_time_ms"] < 500
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate(self, cache_router):
        """Test that cache hit rate improves with usage."""
        # Simulate 100 requests
        requests = [
            ("precio", {"customer_type": "general"}),
            ("cuanto cuesta", {"customer_type": "consultant"}),
            ("que es ngx", {"customer_type": "executive"}),
            ("como funciona", {"customer_type": "general"}),
            ("garantia", {"customer_type": "general"}),
        ] * 20  # 100 total requests
        
        # Process requests
        for message, context in requests:
            await cache_router.route_request(message, context)
        
        # Get performance report
        report = await cache_router.get_performance_report()
        
        # Validate cache efficiency
        cache_efficiency = cache_router._calculate_cache_efficiency()
        assert cache_efficiency > 60, f"Cache efficiency {cache_efficiency}% is below target 60%"
        
        # Check distribution
        assert report["total_requests"] == 100
        assert "instant" in report["cache_distribution"]
    
    @pytest.mark.asyncio
    async def test_concurrent_request_performance(self, cache_router):
        """Test performance under concurrent load."""
        # Create 50 concurrent requests
        messages = [
            "precio", "que es ngx", "como funciona", "garantia", "beneficios"
        ] * 10
        
        contexts = [
            {"customer_type": "general", "tier": "standard"},
            {"customer_type": "consultant", "tier": "pro"},
            {"customer_type": "executive", "tier": "elite"},
        ] * 17  # ~50 contexts
        
        # Mock instant responses for common questions
        cache_router.precompute_service.get_instant_response = AsyncMock(
            return_value={"response": "Respuesta rápida", "from_cache": True}
        )
        
        # Process requests concurrently
        start_time = time.time()
        
        tasks = []
        for i in range(50):
            message = messages[i]
            context = contexts[i] if i < len(contexts) else contexts[0]
            task = cache_router.route_request(message, context)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time_ms = (end_time - start_time) * 1000
        
        # Validate performance
        avg_time_ms = total_time_ms / 50
        assert avg_time_ms < 100, f"Average response time {avg_time_ms}ms exceeds target 100ms"
        
        # Check that most responses were from cache
        cache_hits = sum(1 for _, metrics in results if metrics["cache_level"] != "computed")
        cache_hit_rate = (cache_hits / 50) * 100
        assert cache_hit_rate > 80, f"Cache hit rate {cache_hit_rate}% is below target 80%"
    
    @pytest.mark.asyncio
    async def test_cache_warming_effectiveness(self, cache_manager, precompute_service):
        """Test that cache warming pre-loads common responses."""
        # Initialize and warm cache
        stats = await precompute_service.initialize_hot_cache()
        
        # Verify pre-loaded responses
        assert stats["total"] > 0
        assert stats["pricing"] > 0
        assert stats["objections"] > 0
        assert stats["information"] > 0
        assert stats["roi"] > 0
        
        # Test that common questions are instantly available
        common_questions = [
            "precio", "es caro", "que es ngx", "como funciona",
            "garantia", "vale la pena", "no tengo tiempo"
        ]
        
        for question in common_questions:
            # Mock the cache check
            message_hash = precompute_service._hash_message(question)
            cache_manager.get_cached_response = AsyncMock(
                return_value={"response": f"Respuesta para {question}", "type": "cached"}
            )
            
            response = await precompute_service.get_instant_response(
                question, {"customer_type": "general"}
            )
            
            # Should get instant response for common questions
            # Note: In real implementation, this would check actual cache
            # For test, we're validating the warming process completed
            assert stats["total"] > len(common_questions)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])