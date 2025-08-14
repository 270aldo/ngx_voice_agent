"""
Tests for ML/NLP Service Consolidation.

This test suite validates the consolidated ML and NLP services,
compatibility layers, and migration functionality.

Test Categories:
- ML Prediction Service functionality
- NLP Analysis Service functionality  
- Compatibility layer behavior
- Performance benchmarks
- Migration validation
- Error handling and fallbacks
"""

import asyncio
import pytest
import time
from typing import Dict, List, Any
from unittest.mock import AsyncMock, Mock, patch
from dataclasses import asdict

# Test imports
from src.services.consolidated_ml_prediction_service import (
    ConsolidatedMLPredictionService,
    PredictionType,
    MLPredictionResult,
    BatchPredictionRequest,
    ModelMetrics
)

from src.services.consolidated_nlp_analysis_service import (
    ConsolidatedNLPAnalysisService,
    IntentType,
    SentimentType,
    EntityType,
    NLPAnalysisResult
)

from src.services.ml_compatibility import (
    ConversionPredictionServiceCompat,
    NeedsPredictionServiceCompat,
    ObjectionPredictionServiceCompat,
    MLMigrationManager
)

from src.services.nlp_compatibility import (
    NLPIntegrationServiceCompat,
    EntityRecognitionServiceCompat,
    KeywordExtractionServiceCompat,
    NLPMigrationManager
)

from src.config.settings import get_settings

settings = get_settings()


class TestConsolidatedMLPredictionService:
    """Test the consolidated ML prediction service."""
    
    @pytest.fixture
    async def ml_service(self):
        """Create ML service instance for testing."""
        service = ConsolidatedMLPredictionService()
        try:
            await service.initialize()
            yield service
        finally:
            await service.cleanup()
    
    @pytest.fixture
    def sample_features(self):
        """Sample features for testing predictions."""
        return {
            "engagement_score": 0.8,
            "questions_asked": 3,
            "objections_raised": 1,
            "price_discussed": True,
            "demo_requested": True,
            "avg_response_time": 25.0,
            "conversation_duration": 15,
            "positive_sentiment": 0.7,
            "buying_signals": 2,
            "decision_maker_present": True
        }
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, ml_service):
        """Test ML service initializes correctly."""
        assert ml_service._initialized
        assert len(ml_service.models) > 0
        assert PredictionType.CONVERSION in ml_service.models
        assert PredictionType.NEEDS in ml_service.models
        assert PredictionType.OBJECTION in ml_service.models
    
    @pytest.mark.asyncio
    async def test_conversion_prediction(self, ml_service, sample_features):
        """Test conversion prediction functionality."""
        result = await ml_service.predict_single(
            prediction_type=PredictionType.CONVERSION,
            features=sample_features,
            conversation_id="test_conv_123"
        )
        
        assert isinstance(result, MLPredictionResult)
        assert result.prediction_type == PredictionType.CONVERSION
        assert 0.0 <= result.probability <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.reasoning) > 0
        assert len(result.features_used) > 0
        assert result.model_version is not None
    
    @pytest.mark.asyncio
    async def test_needs_prediction(self, ml_service, sample_features):
        """Test needs prediction functionality."""
        needs_features = {
            "industry_match": 0.9,
            "company_size": 50,
            "pain_points_mentioned": 2,
            "budget_range_discussed": True,
            "timeline_urgency": 0.8,
            "feature_interest_score": 0.7,
            "competitive_mentions": 1,
            "specific_requirements": 3,
            "stakeholder_count": 3,
            "current_solution_mentioned": True
        }
        
        result = await ml_service.predict_single(
            prediction_type=PredictionType.NEEDS,
            features=needs_features,
            conversation_id="test_conv_124"
        )
        
        assert isinstance(result, MLPredictionResult)
        assert result.prediction_type == PredictionType.NEEDS
        assert 0.0 <= result.probability <= 1.0
        assert result.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_objection_prediction(self, ml_service, sample_features):
        """Test objection prediction functionality."""
        objection_features = {
            "negative_sentiment": 2,
            "hesitation_words": 1,
            "comparison_requests": 1,
            "price_concerns": 2,
            "implementation_concerns": 1,
            "authority_questions": 1,
            "delay_indicators": 0,
            "skeptical_tone": 1,
            "competitor_mentions": 1,
            "budget_constraints": 1
        }
        
        result = await ml_service.predict_single(
            prediction_type=PredictionType.OBJECTION,
            features=objection_features,
            conversation_id="test_conv_125"
        )
        
        assert isinstance(result, MLPredictionResult)
        assert result.prediction_type == PredictionType.OBJECTION
        assert 0.0 <= result.probability <= 1.0
    
    @pytest.mark.asyncio
    async def test_batch_prediction(self, ml_service, sample_features):
        """Test batch prediction functionality."""
        batch_request = BatchPredictionRequest(
            conversation_ids=["conv_1", "conv_2", "conv_3"],
            prediction_types=[PredictionType.CONVERSION, PredictionType.NEEDS],
            features_batch=[sample_features, sample_features, sample_features]
        )
        
        results = await ml_service.predict_batch(batch_request)
        
        assert isinstance(results, dict)
        assert "conversion" in results
        assert "needs" in results
        assert len(results["conversion"]) == 3
        assert len(results["needs"]) == 3
        
        for result in results["conversion"]:
            assert isinstance(result, MLPredictionResult)
            assert result.prediction_type == PredictionType.CONVERSION
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self, ml_service, sample_features):
        """Test prediction caching works correctly."""
        # First prediction
        start_time = time.time()
        result1 = await ml_service.predict_single(
            prediction_type=PredictionType.CONVERSION,
            features=sample_features
        )
        first_duration = time.time() - start_time
        
        # Second prediction (should be cached)
        start_time = time.time()
        result2 = await ml_service.predict_single(
            prediction_type=PredictionType.CONVERSION,
            features=sample_features
        )
        second_duration = time.time() - start_time
        
        # Results should be identical
        assert result1.probability == result2.probability
        assert result1.confidence == result2.confidence
        
        # Second call should be faster (cached)
        assert second_duration < first_duration
    
    @pytest.mark.asyncio
    async def test_model_metrics_tracking(self, ml_service, sample_features):
        """Test model performance metrics are tracked."""
        # Make some predictions
        await ml_service.predict_single(PredictionType.CONVERSION, sample_features)
        await ml_service.predict_single(PredictionType.NEEDS, sample_features)
        
        metrics = await ml_service.get_model_metrics()
        
        assert isinstance(metrics, dict)
        assert "conversion" in metrics
        assert "needs" in metrics
        
        for metric in metrics.values():
            assert isinstance(metric, ModelMetrics)
            assert metric.prediction_count >= 0
            assert metric.avg_response_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_drift_detection(self, ml_service):
        """Test model drift detection functionality."""
        drift_result = await ml_service.detect_model_drift(
            prediction_type=PredictionType.CONVERSION,
            threshold=0.1
        )
        
        assert isinstance(drift_result, dict)
        assert "drift_detected" in drift_result
        assert isinstance(drift_result["drift_detected"], bool)
        
        if drift_result["drift_detected"]:
            assert "reason" in drift_result
            assert "recommendation" in drift_result
    
    @pytest.mark.asyncio
    async def test_health_check(self, ml_service):
        """Test service health check."""
        health = await ml_service.health_check()
        
        assert isinstance(health, dict)
        assert "status" in health
        assert "initialized" in health
        assert "models_loaded" in health
        assert "timestamp" in health
        
        assert health["initialized"] is True
        assert health["models_loaded"] > 0
        assert health["status"] in ["healthy", "degraded", "unhealthy"]


class TestConsolidatedNLPAnalysisService:
    """Test the consolidated NLP analysis service."""
    
    @pytest.fixture
    async def nlp_service(self):
        """Create NLP service instance for testing."""
        service = ConsolidatedNLPAnalysisService()
        try:
            await service.initialize()
            yield service
        finally:
            await service.cleanup()
    
    @pytest.fixture
    def sample_texts(self):
        """Sample texts for NLP testing."""
        return [
            "Hi, I'm interested in learning more about your pricing plans.",
            "Can you show me a demo of the product? I'd like to see the features.",
            "I'm not sure if this is right for us. What makes you different from competitors?",
            "We're looking for a solution to help with lead generation. Our current system isn't working well.",
            "How much does the premium plan cost? Is there a discount for annual billing?"
        ]
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, nlp_service):
        """Test NLP service initializes correctly."""
        assert nlp_service._initialized
        assert nlp_service.intent_patterns is not None
        assert nlp_service.entity_patterns is not None
    
    @pytest.mark.asyncio
    async def test_intent_analysis(self, nlp_service, sample_texts):
        """Test intent analysis functionality."""
        pricing_text = "How much does your premium plan cost?"
        
        result = await nlp_service.analyze_text(
            text=pricing_text,
            conversation_id="test_conv_intent"
        )
        
        assert isinstance(result, NLPAnalysisResult)
        assert result.intent.intent == IntentType.PRICING_INQUIRY
        assert result.intent.confidence > 0.0
        assert len(result.intent.reasoning) > 0
    
    @pytest.mark.asyncio
    async def test_entity_extraction(self, nlp_service):
        """Test entity extraction functionality."""
        text = "Contact me at john.doe@example.com or call (555) 123-4567. Our budget is $50,000."
        
        result = await nlp_service.analyze_text(text)
        
        assert len(result.entities) > 0
        
        # Check for expected entities
        entity_types = [e.entity_type for e in result.entities]
        assert EntityType.EMAIL in entity_types
        assert EntityType.PHONE in entity_types or EntityType.PRICE in entity_types
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis(self, nlp_service):
        """Test sentiment analysis functionality."""
        positive_text = "This looks amazing! I love the features and the interface is perfect."
        negative_text = "This is terrible and way too expensive. I hate the interface."
        neutral_text = "Can you provide more information about the pricing?"
        
        # Test positive sentiment
        result_pos = await nlp_service.analyze_text(positive_text)
        assert result_pos.sentiment.sentiment == SentimentType.POSITIVE
        assert result_pos.sentiment.polarity > 0
        
        # Test negative sentiment
        result_neg = await nlp_service.analyze_text(negative_text)
        assert result_neg.sentiment.sentiment == SentimentType.NEGATIVE
        assert result_neg.sentiment.polarity < 0
        
        # Test neutral sentiment
        result_neu = await nlp_service.analyze_text(neutral_text)
        assert result_neu.sentiment.sentiment == SentimentType.NEUTRAL
        assert abs(result_neu.sentiment.polarity) <= 0.1
    
    @pytest.mark.asyncio
    async def test_keyword_extraction(self, nlp_service):
        """Test keyword extraction functionality."""
        text = "We need a CRM solution with advanced analytics and API integration for our sales team."
        
        result = await nlp_service.analyze_text(text)
        
        assert len(result.keywords) > 0
        
        # Check for relevant keywords
        extracted_keywords = [kw.keyword for kw in result.keywords]
        business_keywords = ["crm", "analytics", "integration", "sales"]
        
        # At least some business keywords should be extracted
        assert any(keyword in " ".join(extracted_keywords) for keyword in business_keywords)
    
    @pytest.mark.asyncio
    async def test_question_classification(self, nlp_service):
        """Test question classification functionality."""
        question_text = "What features are included? How much does it cost? When can we start?"
        
        result = await nlp_service.analyze_text(question_text)
        
        assert len(result.questions) > 0
        
        # Check for different question types
        question_types = [q.question_type for q in result.questions]
        expected_types = ["what", "how_much", "when"]
        
        # Should detect multiple question types
        assert len(set(question_types)) >= 2
    
    @pytest.mark.asyncio
    async def test_batch_analysis(self, nlp_service, sample_texts):
        """Test batch NLP analysis functionality."""
        results = await nlp_service.analyze_batch(sample_texts)
        
        assert len(results) == len(sample_texts)
        
        for result in results:
            assert isinstance(result, NLPAnalysisResult)
            assert result.intent.intent is not None
            assert result.sentiment.sentiment is not None
    
    @pytest.mark.asyncio
    async def test_analysis_caching(self, nlp_service):
        """Test NLP analysis caching."""
        text = "How much does the premium plan cost?"
        
        # First analysis
        start_time = time.time()
        result1 = await nlp_service.analyze_text(text)
        first_duration = time.time() - start_time
        
        # Second analysis (should be cached)
        start_time = time.time()
        result2 = await nlp_service.analyze_text(text)
        second_duration = time.time() - start_time
        
        # Results should be identical
        assert result1.intent.intent == result2.intent.intent
        assert result1.sentiment.sentiment == result2.sentiment.sentiment
        
        # Second call should be faster
        assert second_duration < first_duration
    
    @pytest.mark.asyncio
    async def test_health_check(self, nlp_service):
        """Test NLP service health check."""
        health = await nlp_service.health_check()
        
        assert isinstance(health, dict)
        assert "status" in health
        assert "initialized" in health
        assert "performance" in health
        
        assert health["initialized"] is True
        assert health["status"] in ["healthy", "degraded", "unhealthy"]


class TestCompatibilityLayers:
    """Test compatibility layers for seamless migration."""
    
    @pytest.mark.asyncio
    async def test_ml_compatibility_service(self):
        """Test ML compatibility layer."""
        # Test with consolidated service enabled
        with patch.object(settings, 'use_consolidated_ml_service', True):
            conv_service = ConversionPredictionServiceCompat()
            await conv_service.initialize()
            
            sample_messages = [
                {"role": "user", "content": "I'm interested in your pricing"},
                {"role": "assistant", "content": "Our plans start at $99/month"},
                {"role": "user", "content": "Can I see a demo?"}
            ]
            
            result = await conv_service.predict_conversion(
                conversation_id="test_compat",
                messages=sample_messages
            )
            
            assert isinstance(result, dict)
            assert "conversion_probability" in result
            assert "confidence" in result
            assert "recommendation" in result
            assert 0.0 <= result["conversion_probability"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_nlp_compatibility_service(self):
        """Test NLP compatibility layer."""
        # Test with consolidated service enabled
        with patch.object(settings, 'use_consolidated_nlp_service', True):
            nlp_service = NLPIntegrationServiceCompat()
            await nlp_service.initialize()
            
            text = "How much does your premium plan cost?"
            
            result = await nlp_service.analyze_intent(text)
            
            assert isinstance(result, dict)
            assert "intent" in result
            assert "confidence" in result
            assert "sentiment" in result
            assert result["intent"] == "pricing_inquiry"
    
    @pytest.mark.asyncio
    async def test_compatibility_fallback(self):
        """Test fallback behavior when consolidated services fail."""
        # Test with consolidated service disabled
        with patch.object(settings, 'use_consolidated_ml_service', False):
            conv_service = ConversionPredictionServiceCompat()
            await conv_service.initialize()
            
            sample_messages = [{"role": "user", "content": "I want to buy your product"}]
            
            result = await conv_service.predict_conversion(
                conversation_id="test_fallback",
                messages=sample_messages
            )
            
            # Should still return valid result using fallback
            assert isinstance(result, dict)
            assert "conversion_probability" in result
            assert result["confidence"] == 0.6  # Fallback confidence


class TestPerformanceBenchmarks:
    """Performance benchmarks for consolidated services."""
    
    @pytest.fixture
    async def services(self):
        """Initialize services for benchmarking."""
        ml_service = ConsolidatedMLPredictionService()
        nlp_service = ConsolidatedNLPAnalysisService()
        
        await ml_service.initialize()
        await nlp_service.initialize()
        
        yield {"ml": ml_service, "nlp": nlp_service}
        
        await ml_service.cleanup()
        await nlp_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_ml_prediction_performance(self, services):
        """Benchmark ML prediction performance."""
        ml_service = services["ml"]
        features = {
            "engagement_score": 0.8,
            "questions_asked": 3,
            "buying_signals": 2,
            "demo_requested": True,
            "price_discussed": True
        }
        
        # Warm up
        await ml_service.predict_single(PredictionType.CONVERSION, features)
        
        # Benchmark single predictions
        iterations = 50
        start_time = time.time()
        
        for i in range(iterations):
            await ml_service.predict_single(PredictionType.CONVERSION, features)
        
        total_time = time.time() - start_time
        avg_time_ms = (total_time / iterations) * 1000
        
        print(f"ML Prediction Performance: {avg_time_ms:.2f}ms per prediction")
        
        # Assert performance requirements
        assert avg_time_ms < 100  # Should be under 100ms per prediction
    
    @pytest.mark.asyncio
    async def test_nlp_analysis_performance(self, services):
        """Benchmark NLP analysis performance."""
        nlp_service = services["nlp"]
        text = "I'm interested in your premium plan pricing. Can you show me a demo?"
        
        # Warm up
        await nlp_service.analyze_text(text)
        
        # Benchmark analysis
        iterations = 30
        start_time = time.time()
        
        for i in range(iterations):
            await nlp_service.analyze_text(text)
        
        total_time = time.time() - start_time
        avg_time_ms = (total_time / iterations) * 1000
        
        print(f"NLP Analysis Performance: {avg_time_ms:.2f}ms per analysis")
        
        # Assert performance requirements
        assert avg_time_ms < 200  # Should be under 200ms per analysis
    
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, services):
        """Benchmark batch processing performance."""
        ml_service = services["ml"]
        
        # Create batch request
        features = {"engagement_score": 0.7, "buying_signals": 1}
        batch_request = BatchPredictionRequest(
            conversation_ids=[f"conv_{i}" for i in range(20)],
            prediction_types=[PredictionType.CONVERSION],
            features_batch=[features] * 20
        )
        
        # Benchmark batch processing
        start_time = time.time()
        results = await ml_service.predict_batch(batch_request)
        batch_time = time.time() - start_time
        
        # Compare with individual processing
        start_time = time.time()
        for i in range(20):
            await ml_service.predict_single(PredictionType.CONVERSION, features)
        individual_time = time.time() - start_time
        
        print(f"Batch processing: {batch_time:.2f}s")
        print(f"Individual processing: {individual_time:.2f}s")
        print(f"Batch efficiency: {(1 - batch_time/individual_time)*100:.1f}% faster")
        
        # Batch should be more efficient
        assert batch_time < individual_time


class TestMigrationValidation:
    """Validate migration functionality and data consistency."""
    
    @pytest.mark.asyncio
    async def test_ml_migration_manager(self):
        """Test ML migration manager functionality."""
        manager = MLMigrationManager()
        await manager.initialize_services()
        
        # Test migration status
        status = manager.get_migration_status()
        
        assert isinstance(status, dict)
        assert "consolidated_ml_enabled" in status
        assert "services_initialized" in status
        assert status["services_initialized"] > 0
        
        # Test health check
        health = await manager.health_check()
        
        assert isinstance(health, dict)
        assert "status" in health
        assert "services" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
    
    @pytest.mark.asyncio
    async def test_nlp_migration_manager(self):
        """Test NLP migration manager functionality."""
        manager = NLPMigrationManager()
        await manager.initialize_services()
        
        # Test migration status
        status = manager.get_migration_status()
        
        assert isinstance(status, dict)
        assert "consolidated_nlp_enabled" in status
        assert "services_initialized" in status
        
        # Test health check
        health = await manager.health_check()
        
        assert isinstance(health, dict)
        assert "status" in health
        assert "services" in health
    
    @pytest.mark.asyncio
    async def test_feature_flag_behavior(self):
        """Test behavior with different feature flag configurations."""
        # Test ML service with flag enabled
        with patch.object(settings, 'use_consolidated_ml_service', True):
            conv_service = ConversionPredictionServiceCompat()
            await conv_service.initialize()
            assert conv_service.consolidated_service is not None
        
        # Test ML service with flag disabled
        with patch.object(settings, 'use_consolidated_ml_service', False):
            conv_service = ConversionPredictionServiceCompat()
            await conv_service.initialize()
            assert conv_service.consolidated_service is None
        
        # Test NLP service with flag enabled
        with patch.object(settings, 'use_consolidated_nlp_service', True):
            nlp_service = NLPIntegrationServiceCompat()
            await nlp_service.initialize()
            assert nlp_service.consolidated_service is not None
        
        # Test NLP service with flag disabled
        with patch.object(settings, 'use_consolidated_nlp_service', False):
            nlp_service = NLPIntegrationServiceCompat()
            await nlp_service.initialize()
            assert nlp_service.consolidated_service is None


class TestErrorHandlingAndFallbacks:
    """Test error handling and fallback mechanisms."""
    
    @pytest.mark.asyncio
    async def test_ml_service_error_handling(self):
        """Test ML service handles errors gracefully."""
        ml_service = ConsolidatedMLPredictionService()
        await ml_service.initialize()
        
        # Test with invalid features
        try:
            await ml_service.predict_single(
                prediction_type=PredictionType.CONVERSION,
                features={}  # Empty features
            )
        except Exception as e:
            # Should handle gracefully without crashing
            assert isinstance(e, Exception)
    
    @pytest.mark.asyncio
    async def test_nlp_service_error_handling(self):
        """Test NLP service handles errors gracefully."""
        nlp_service = ConsolidatedNLPAnalysisService()
        await nlp_service.initialize()
        
        # Test with empty text
        result = await nlp_service.analyze_text("")
        
        # Should return valid result even with empty input
        assert isinstance(result, NLPAnalysisResult)
        assert result.intent.intent == IntentType.UNKNOWN
    
    @pytest.mark.asyncio
    async def test_compatibility_layer_fallbacks(self):
        """Test compatibility layer fallback mechanisms."""
        # Mock consolidated service failure
        with patch.object(ConsolidatedMLPredictionService, 'predict_single', 
                         side_effect=Exception("Service unavailable")):
            conv_service = ConversionPredictionServiceCompat()
            await conv_service.initialize()
            
            result = await conv_service.predict_conversion(
                conversation_id="test_error",
                messages=[{"role": "user", "content": "I want to buy"}]
            )
            
            # Should fallback and still return a result
            assert isinstance(result, dict)
            assert "conversion_probability" in result
            assert result["confidence"] == 0.6  # Fallback confidence


if __name__ == "__main__":
    # Run performance benchmarks
    import asyncio
    
    async def run_benchmarks():
        """Run performance benchmarks."""
        print("🚀 Running ML/NLP Consolidation Benchmarks...")
        
        # Initialize services
        ml_service = ConsolidatedMLPredictionService()
        nlp_service = ConsolidatedNLPAnalysisService()
        
        await ml_service.initialize()
        await nlp_service.initialize()
        
        try:
            # ML Performance Test
            features = {
                "engagement_score": 0.8,
                "questions_asked": 3,
                "buying_signals": 2
            }
            
            iterations = 100
            start_time = time.time()
            
            for i in range(iterations):
                await ml_service.predict_single(PredictionType.CONVERSION, features)
            
            ml_time = (time.time() - start_time) / iterations * 1000
            print(f"✅ ML Prediction: {ml_time:.2f}ms per prediction")
            
            # NLP Performance Test
            text = "I'm interested in pricing and would like to see a demo"
            
            start_time = time.time()
            
            for i in range(50):
                await nlp_service.analyze_text(text)
            
            nlp_time = (time.time() - start_time) / 50 * 1000
            print(f"✅ NLP Analysis: {nlp_time:.2f}ms per analysis")
            
            # Health Checks
            ml_health = await ml_service.health_check()
            nlp_health = await nlp_service.health_check()
            
            print(f"✅ ML Service Health: {ml_health['status']}")
            print(f"✅ NLP Service Health: {nlp_health['status']}")
            
            print("\n🎉 All benchmarks completed successfully!")
            
        finally:
            await ml_service.cleanup()
            await nlp_service.cleanup()
    
    # Run if executed directly
    asyncio.run(run_benchmarks())