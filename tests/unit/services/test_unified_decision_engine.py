"""
Unit tests for Unified Decision Engine.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import timedelta

from src.services.unified_decision_engine import (
    UnifiedDecisionEngine,
    DecisionConfig,
    OptimizationMode
)


class MockPredictor:
    """Mock predictor for testing."""
    
    def __init__(self, name, default_result):
        self.name = name
        self.default_result = default_result
        self.call_count = 0
    
    async def predict_conversion(self, **kwargs):
        self.call_count += 1
        return {"probability": self.default_result.get("conversion", 0.5)}
    
    async def predict_objections(self, **kwargs):
        self.call_count += 1
        return {"objections": self.default_result.get("objections", [])}
    
    async def predict_needs(self, **kwargs):
        self.call_count += 1
        return {"needs": self.default_result.get("needs", [])}


class TestDecisionConfig:
    """Test DecisionConfig settings."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = DecisionConfig()
        assert config.enable_cache is True
        assert config.cache_ttl == 300
        assert config.enable_circuit_breaker is True
        assert config.optimization_mode == OptimizationMode.STANDARD
        assert config.timeout_seconds == 2.0
        assert config.enable_advanced_strategies is True
        assert config.parallel_processing is True
        assert config.max_retries == 3
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = DecisionConfig(
            enable_cache=False,
            optimization_mode=OptimizationMode.FAST,
            timeout_seconds=1.0
        )
        assert config.enable_cache is False
        assert config.optimization_mode == OptimizationMode.FAST
        assert config.timeout_seconds == 1.0


class TestUnifiedDecisionEngine:
    """Test UnifiedDecisionEngine functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock predictors
        self.conversion_predictor = MockPredictor(
            "conversion",
            {"conversion": 0.75}
        )
        self.objection_predictor = MockPredictor(
            "objection",
            {"objections": ["price_high"]}
        )
        self.needs_predictor = MockPredictor(
            "needs",
            {"needs": ["automation", "cost_savings"]}
        )
        
        # Default config
        self.config = DecisionConfig(
            enable_cache=False,  # Disable cache for tests
            enable_circuit_breaker=False  # Disable circuit breaker for tests
        )
        
        # Create engine
        self.engine = UnifiedDecisionEngine(
            conversion_predictor=self.conversion_predictor,
            objection_predictor=self.objection_predictor,
            needs_predictor=self.needs_predictor,
            config=self.config
        )
    
    @pytest.mark.asyncio
    async def test_standard_decision(self):
        """Test standard decision making."""
        messages = [
            {"role": "user", "content": "I'm interested in your services"},
            {"role": "assistant", "content": "Great! Let me tell you more"}
        ]
        customer_profile = {
            "name": "Test Customer",
            "business_type": "gym"
        }
        
        result = await self.engine.make_decision(messages, customer_profile)
        
        # Check result structure
        assert "action" in result
        assert "confidence" in result
        assert "urgency_level" in result
        assert "reasoning" in result
        assert "predictions" in result
        assert result["optimization_mode"] == "standard"
        
        # Check predictions
        predictions = result["predictions"]
        assert predictions["conversion_probability"] == 0.75
        assert predictions["objections"] == ["price_high"]
        assert predictions["needs"] == ["automation", "cost_savings"]
        
        # Check decision based on high conversion
        assert result["action"] in ["present_offer", "address_objections"]
    
    @pytest.mark.asyncio
    async def test_fast_decision(self):
        """Test fast decision mode."""
        self.engine.config.optimization_mode = OptimizationMode.FAST
        
        messages = [{"role": "user", "content": "Tell me about pricing"}]
        
        result = await self.engine.make_decision(messages, {})
        
        # Fast mode should only use conversion probability
        assert result["optimization_mode"] == "fast"
        assert result["confidence"] == 0.7  # Lower confidence for fast
        assert "conversion_probability" in result
        
        # Should not have called other predictors
        assert self.objection_predictor.call_count == 0
        assert self.needs_predictor.call_count == 0
    
    @pytest.mark.asyncio
    async def test_accurate_decision(self):
        """Test accurate decision mode."""
        self.engine.config.optimization_mode = OptimizationMode.ACCURATE
        
        messages = [{"role": "user", "content": "I need help with automation"}]
        customer_profile = {"business_type": "fitness_studio"}
        
        result = await self.engine.make_decision(messages, customer_profile)
        
        # Accurate mode should provide comprehensive analysis
        assert result["optimization_mode"] == "accurate"
        assert result["analysis_depth"] == "comprehensive"
        assert "alternative_actions" in result
        
        # All predictors should be called
        assert self.conversion_predictor.call_count > 0
        assert self.objection_predictor.call_count > 0
        assert self.needs_predictor.call_count > 0
    
    @pytest.mark.asyncio
    async def test_decision_logic_high_conversion(self):
        """Test decision logic for high conversion probability."""
        # Set high conversion, no objections
        self.conversion_predictor.default_result = {"conversion": 0.85}
        self.objection_predictor.default_result = {"objections": []}
        
        result = await self.engine.make_decision([], {})
        
        assert result["action"] == "close_deal"
        assert result["confidence"] == 0.9
        assert result["urgency_level"] == 9
        assert "High conversion probability with no objections" in result["reasoning"]
    
    @pytest.mark.asyncio
    async def test_decision_logic_with_objections(self):
        """Test decision logic when objections present."""
        # Medium conversion with objections
        self.conversion_predictor.default_result = {"conversion": 0.65}
        self.objection_predictor.default_result = {"objections": ["pricing_concern"]}
        
        result = await self.engine.make_decision([], {})
        
        assert result["action"] == "address_objections"
        assert "pricing_concern" in result["reasoning"]
    
    @pytest.mark.asyncio
    async def test_decision_logic_explore_needs(self):
        """Test decision logic for needs exploration."""
        # Low conversion but identified needs
        self.conversion_predictor.default_result = {"conversion": 0.3}
        self.needs_predictor.default_result = {"needs": ["efficiency", "automation"]}
        
        result = await self.engine.make_decision([], {})
        
        assert result["action"] == "explore_needs"
        assert "efficiency" in result["reasoning"] or "automation" in result["reasoning"]
    
    @pytest.mark.asyncio
    async def test_caching_functionality(self):
        """Test caching when enabled."""
        # Enable caching
        config = DecisionConfig(enable_cache=True, cache_ttl=60)
        engine = UnifiedDecisionEngine(
            conversion_predictor=self.conversion_predictor,
            config=config
        )
        
        messages = [{"role": "user", "content": "test"}]
        profile = {"id": "123"}
        
        # First call
        result1 = await engine.make_decision(messages, profile)
        initial_calls = self.conversion_predictor.call_count
        
        # Second call with same inputs should hit cache
        result2 = await engine.make_decision(messages, profile)
        
        # Check cache hit
        assert engine._cache_hits == 1
        assert engine._cache_misses == 1
        assert self.conversion_predictor.call_count == initial_calls  # No new calls
        
        # Results should be identical
        assert result1["action"] == result2["action"]
    
    @pytest.mark.asyncio
    async def test_parallel_vs_sequential_predictions(self):
        """Test parallel processing of predictions."""
        # Test parallel processing
        self.engine.config.parallel_processing = True
        
        start_time = asyncio.get_event_loop().time()
        await self.engine.make_decision([], {})
        parallel_duration = asyncio.get_event_loop().time() - start_time
        
        # Test sequential processing
        self.engine.config.parallel_processing = False
        
        start_time = asyncio.get_event_loop().time()
        await self.engine.make_decision([], {})
        sequential_duration = asyncio.get_event_loop().time() - start_time
        
        # Parallel should be faster (or at least not significantly slower)
        # Note: In unit tests with mocks, the difference might be minimal
        assert parallel_duration <= sequential_duration * 1.5
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling in fast mode."""
        # Create slow predictor
        async def slow_predict(**kwargs):
            await asyncio.sleep(5)
            return {"probability": 0.9}
        
        self.conversion_predictor.predict_conversion = slow_predict
        self.engine.config.optimization_mode = OptimizationMode.FAST
        self.engine.config.timeout_seconds = 0.1
        
        result = await self.engine.make_decision([], {})
        
        # Should fall back to default
        assert result["conversion_probability"] == 0.5  # Default fallback
    
    @pytest.mark.asyncio
    async def test_error_fallback(self):
        """Test error handling and fallback."""
        # Make predictor raise error
        async def failing_predict(**kwargs):
            raise RuntimeError("Predictor failed")
        
        self.conversion_predictor.predict_conversion = failing_predict
        
        result = await self.engine.make_decision([], {})
        
        # Should return error fallback
        assert result["fallback"] is True
        assert result["error"] == "processing_error"
        assert result["action"] == "build_rapport"
        assert result["confidence"] == 0.4
    
    def test_sentiment_calculation(self):
        """Test sentiment calculation from messages."""
        messages = [
            {"role": "user", "content": "Esto es genial y perfecto!"},
            {"role": "user", "content": "Gracias, muy bien"},
            {"role": "user", "content": "Tengo un problema, es muy caro"}
        ]
        
        sentiment = self.engine._calculate_sentiment(messages)
        
        # Should be slightly positive (more positive than negative words)
        assert -1 <= sentiment <= 1
        assert sentiment > 0  # Net positive
    
    def test_engagement_calculation(self):
        """Test engagement score calculation."""
        messages = [
            {"role": "user", "content": "Hola"},
            {"role": "user", "content": "¿Cómo funciona esto? Me interesa saber más"},
            {"role": "user", "content": "¿Cuál es el precio? ¿Hay descuentos?"}
        ]
        
        engagement = self.engine._calculate_engagement(messages)
        
        # Should have moderate to high engagement
        assert 0 <= engagement <= 1
        assert engagement > 0.3  # Questions indicate engagement
    
    def test_get_metrics(self):
        """Test metrics reporting."""
        metrics = self.engine.get_metrics()
        
        assert metrics["total_calls"] == 0
        assert metrics["cache_hits"] == 0
        assert metrics["cache_misses"] == 0
        assert metrics["optimization_mode"] == "standard"
        assert metrics["features"]["caching"] is False
        assert metrics["features"]["parallel_processing"] is True
    
    @pytest.mark.asyncio
    async def test_advanced_strategies_integration(self):
        """Test integration with advanced strategies when enabled."""
        # Mock advanced strategies
        with patch.object(self.engine, 'strategies') as mock_strategies:
            mock_strategy = Mock()
            mock_decision = Mock(
                recommended_action="create_urgency",
                confidence=0.85,
                reasoning="Time-limited offer",
                urgency_level=8
            )
            
            mock_strategies.select_optimal_strategy.return_value = mock_strategy
            mock_strategies.execute_strategy.return_value = mock_decision
            
            result = await self.engine.make_decision([], {})
            
            # Should use strategy recommendation
            assert "strategy" in result["predictions"]
            strategy_info = result["predictions"]["strategy"]
            assert strategy_info["action"] == "create_urgency"
            assert strategy_info["confidence"] == 0.85
    
    @pytest.mark.asyncio
    async def test_comprehensive_action_determination(self):
        """Test comprehensive action determination in accurate mode."""
        self.engine.config.optimization_mode = OptimizationMode.ACCURATE
        
        # Set up mixed signals
        self.conversion_predictor.default_result = {"conversion": 0.65}
        self.objection_predictor.default_result = {"objections": ["price", "timing"]}
        self.needs_predictor.default_result = {"needs": ["efficiency"]}
        
        result = await self.engine.make_decision([], {})
        
        # Should have alternative actions
        assert "alternative_actions" in result
        alternatives = result["alternative_actions"]
        assert len(alternatives) > 0
        assert all("action" in alt and "score" in alt for alt in alternatives)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])