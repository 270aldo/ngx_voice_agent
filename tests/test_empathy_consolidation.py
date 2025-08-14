"""
Comprehensive tests for empathy services consolidation.

This test suite validates:
1. Consolidated service functionality
2. Legacy compatibility
3. Feature flags behavior
4. Performance requirements
5. Integration with orchestrator
"""

import asyncio
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import consolidated services
from src.services.consolidated_empathy_intelligence_service import (
    ConsolidatedEmpathyIntelligenceService,
    EmotionalState,
    EmpathyTechnique,
    EmotionalProfile,
    EmpathyResponse,
    EmpathyStrategy
)

# Import compatibility layer
from src.services.empathy_compatibility import (
    AdvancedEmpathyEngine,
    EmotionalIntelligenceService,
    EmpathyEngineService,
    UltraEmpathyGreetingEngine,
    UltraEmpathyPriceHandler,
    AdvancedSentimentService,
    SentimentAlertService,
    AdaptivePersonalityService,
    get_consolidated_service
)

# Import feature flags
from src.config.empathy_feature_flags import (
    EmpathyFeatureFlags,
    EmpathyFeature,
    RolloutStage,
    EmpathyMetrics,
    use_consolidated_service,
    is_feature_enabled
)

from src.models.conversation import CustomerData
from src.integrations.elevenlabs.advanced_voice import VoicePersona


class TestConsolidatedEmpathyIntelligenceService:
    """Test suite for ConsolidatedEmpathyIntelligenceService."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.service = ConsolidatedEmpathyIntelligenceService()
        self.sample_customer = CustomerData(
            name="Test Customer",
            preferred_language="spanish"
        )
        self.sample_messages = [
            {"role": "customer", "content": "Estoy muy frustrado con mi situación actual"},
            {"role": "assistant", "content": "Entiendo tu frustración"},
            {"role": "customer", "content": "No sé si esto va a funcionar para mí"}
        ]
    
    @pytest.mark.asyncio
    async def test_emotional_state_analysis(self):
        """Test emotional state analysis functionality."""
        messages = [{"role": "customer", "content": "Estoy muy confundido y no entiendo nada"}]
        
        profile = await self.service.analyze_emotional_state(
            messages=messages,
            customer_profile=self.sample_customer
        )
        
        assert isinstance(profile, EmotionalProfile)
        assert profile.primary_state == EmotionalState.CONFUSED
        assert profile.intensity > 0.5
        assert profile.confidence > 0.0
        assert "confundido" in str(profile.triggers)
    
    @pytest.mark.asyncio
    async def test_empathy_strategy_generation(self):
        """Test empathy strategy generation."""
        emotional_profile = EmotionalProfile(
            primary_state=EmotionalState.FRUSTRATED,
            intensity=0.8,
            confidence=0.9
        )
        
        strategy = await self.service.generate_empathy_strategy(
            emotional_profile=emotional_profile,
            conversation_context={"phase": "discovery"},
            customer_profile=self.sample_customer
        )
        
        assert isinstance(strategy, EmpathyStrategy)
        assert strategy.primary_technique in [EmpathyTechnique.ACKNOWLEDGMENT, EmpathyTechnique.REFRAMING]
        assert strategy.voice_persona in [VoicePersona.CONSULTANT, VoicePersona.SUPPORTER]
        assert strategy.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_empathy_response_generation(self):
        """Test empathy response generation."""
        emotional_profile = EmotionalProfile(
            primary_state=EmotionalState.ANXIOUS,
            intensity=0.7,
            confidence=0.8
        )
        
        strategy = EmpathyStrategy(
            primary_technique=EmpathyTechnique.VALIDATION,
            secondary_techniques=[EmpathyTechnique.REASSURANCE],
            voice_persona=VoicePersona.SUPPORTER,
            tone_adjustments={"warmth": 0.8},
            cultural_adaptations=["spanish"],
            confidence=0.9
        )
        
        response = await self.service.generate_empathy_response(
            message="Estoy preocupado por mi futuro",
            emotional_profile=emotional_profile,
            empathy_strategy=strategy,
            conversation_context={"phase": "trust_building"}
        )
        
        assert isinstance(response, EmpathyResponse)
        assert len(response.intro_phrase) > 0
        assert len(response.core_message) > 0
        assert len(response.closing_phrase) > 0
        assert response.technique_used == EmpathyTechnique.VALIDATION
        assert response.confidence > 0.0
    
    def test_advanced_sentiment_analysis(self):
        """Test advanced sentiment analysis."""
        # Test positive sentiment
        positive_result = self.service.analyze_advanced_sentiment("Me encanta esta idea, es genial")
        assert positive_result["sentiment"] == "positive"
        assert positive_result["emotions"]["enthusiasm"] > 0.5
        
        # Test negative sentiment
        negative_result = self.service.analyze_advanced_sentiment("Esto es terrible y muy frustrante")
        assert negative_result["sentiment"] == "negative"
        assert negative_result["emotions"]["frustration"] > 0.5
        
        # Test neutral sentiment
        neutral_result = self.service.analyze_advanced_sentiment("Está bien, es normal")
        assert neutral_result["sentiment"] == "neutral"
    
    def test_personality_detection(self):
        """Test personality style detection."""
        # Test analytical style
        analytical_messages = [
            "Necesito ver los números exactos y datos específicos",
            "¿Puedes proporcionar evidencia y métricas detalladas?",
            "Quiero analizar esto cuidadosamente"
        ]
        
        result = self.service.detect_personality_style(analytical_messages)
        assert result["dominant_style"] == "analytical"
        assert result["confidence"] > 0.5
        
        # Test expressive style
        expressive_messages = [
            "¡Esto es increíble y emocionante!",
            "Me encanta la experiencia que describes",
            "¡Qué genial, esto es fantástico!"
        ]
        
        result = self.service.detect_personality_style(expressive_messages)
        assert result["dominant_style"] == "expressive"
    
    def test_sentiment_monitoring_and_alerts(self):
        """Test sentiment monitoring and alert generation."""
        conversation_id = "test_conv_123"
        messages = [
            {"role": "customer", "content": "Esto está bien hasta ahora"},
            {"role": "assistant", "content": "Me alegra escuchar eso"},
            {"role": "customer", "content": "Pero ahora estoy muy frustrado y molesto"},
            {"role": "assistant", "content": "Entiendo tu frustración"},
            {"role": "customer", "content": "Esto es terrible, no funciona nada"}
        ]
        
        alerts = self.service.monitor_conversation_sentiment(conversation_id, messages)
        
        assert alerts["conversation_id"] == conversation_id
        assert alerts["has_alerts"] == True
        assert len(alerts["alerts"]) > 0
        assert len(alerts["recommendations"]) > 0
        assert any(alert["type"] == "high_frustration" for alert in alerts["alerts"])
    
    def test_ultra_empathy_greeting_generation(self):
        """Test ultra-empathy greeting generation."""
        greeting = self.service.generate_ultra_empathy_greeting(
            customer_name="María",
            initial_message="Estoy muy cansada y necesito ayuda",
            customer_profile=self.sample_customer
        )
        
        assert "María" in greeting
        assert len(greeting) > 100  # Should be substantial
        assert "?" in greeting  # Should include questions
        assert any(word in greeting.lower() for word in ["privilegio", "alegra", "gusto"])
    
    def test_price_objection_handling(self):
        """Test empathetic price objection handling."""
        result = self.service.handle_price_objection_with_ultra_empathy(
            objection_message="$149 es muy caro para mí",
            customer_name="Carlos",
            tier_mentioned="pro"
        )
        
        assert result["empathy_score"] == 10
        assert "Carlos" in result["response"]
        assert result["objection_type"] == "sticker_shock"
        assert "comprendo" in result["response"].lower()
        assert len(result["flexibility_options"]) > 0
    
    def test_pattern_recognition(self):
        """Test conversation pattern recognition."""
        messages = [
            {"role": "customer", "content": "¿Cuándo puedo empezar con esto?"},
            {"role": "customer", "content": "Me interesa mucho, suena bien"},
            {"role": "customer", "content": "Estoy listo para el siguiente paso"}
        ]
        
        emotional_history = [
            EmotionalProfile(primary_state=EmotionalState.CURIOUS, intensity=0.6, confidence=0.8),
            EmotionalProfile(primary_state=EmotionalState.INTERESTED, intensity=0.8, confidence=0.9),
            EmotionalProfile(primary_state=EmotionalState.DECISIVE, intensity=0.9, confidence=0.9)
        ]
        
        patterns = self.service.recognize_conversation_patterns(messages, emotional_history)
        
        assert patterns["conversation_phase"] == "closing"
        assert patterns["patterns"]["buying_signals"] > 0
        assert "closing" in [rec.lower() for rec in patterns["recommendations"] if "closing" in rec.lower()]
    
    @pytest.mark.asyncio
    async def test_comprehensive_empathy_response(self):
        """Test the main comprehensive empathy response method."""
        message = "Estoy realmente confundido sobre si esto es lo correcto para mí"
        conversation_history = self.sample_messages
        context = {"conversation_id": "test_123", "phase": "discovery"}
        
        result = await self.service.generate_comprehensive_empathy_response(
            message=message,
            conversation_history=conversation_history,
            customer_profile=self.sample_customer,
            context=context
        )
        
        assert "empathy_response" in result
        assert "sentiment_analysis" in result
        assert "emotional_profile" in result
        assert "personality_style" in result
        assert "conversation_patterns" in result
        assert "alerts" in result
        assert result["empathy_score"] >= 6.0
        assert len(result["recommendations"]) >= 0
    
    @pytest.mark.asyncio
    async def test_learning_system(self):
        """Test the learning and adaptation system."""
        customer_id = "test_customer_456"
        emotional_profile = EmotionalProfile(
            primary_state=EmotionalState.SKEPTICAL,
            intensity=0.7,
            confidence=0.8
        )
        
        strategy = EmpathyStrategy(
            primary_technique=EmpathyTechnique.VALIDATION,
            secondary_techniques=[],
            voice_persona=VoicePersona.CONSULTANT,
            tone_adjustments={"warmth": 0.7},
            cultural_adaptations=[],
            confidence=0.8
        )
        
        # Learn from positive interaction
        await self.service.learn_from_interaction(
            customer_id=customer_id,
            emotional_profile=emotional_profile,
            empathy_strategy=strategy,
            customer_response="Eso tiene sentido, gracias por explicar",
            outcome_positive=True
        )
        
        # Get personalized strategy
        personalized_strategy = await self.service.get_personalized_strategy(
            customer_id=customer_id,
            current_emotional_profile=emotional_profile
        )
        
        assert personalized_strategy is not None
        assert personalized_strategy.primary_technique == EmpathyTechnique.VALIDATION
        assert personalized_strategy.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_performance_requirements(self):
        """Test that performance requirements are met."""
        import time
        
        message = "Estoy ansioso por tomar la decisión correcta"
        start_time = time.time()
        
        # Test emotional analysis performance
        profile = await self.service.analyze_emotional_state([{"role": "customer", "content": message}])
        analysis_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        assert analysis_time < 50  # Should be under 50ms
        assert profile.primary_state == EmotionalState.ANXIOUS
    
    @pytest.mark.asyncio
    async def test_service_statistics(self):
        """Test service statistics and monitoring."""
        stats = await self.service.get_service_stats()
        
        assert "emotional_patterns_count" in stats
        assert "empathy_techniques_count" in stats
        assert "greeting_templates" in stats
        assert "consolidation_status" in stats
        assert stats["consolidation_status"] == "9 services unified successfully"


class TestEmpathyCompatibilityLayer:
    """Test suite for legacy compatibility layer."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.consolidated_service = get_consolidated_service()
    
    @pytest.mark.asyncio
    async def test_advanced_empathy_engine_compatibility(self):
        """Test AdvancedEmpathyEngine legacy compatibility."""
        engine = AdvancedEmpathyEngine()
        
        context = {
            "last_message": "Estoy confundido sobre esto",
            "customer_profile": self.consolidated_service.sample_customer if hasattr(self.consolidated_service, 'sample_customer') else None
        }
        
        result = await engine.generate_intelligent_empathy(context)
        
        assert "surface_layer" in result
        assert "emotional_layer" in result
        assert "cognitive_layer" in result
        assert "behavioral_layer" in result
        assert "meta_layer" in result
        assert "voice_modulation" in result
    
    @pytest.mark.asyncio
    async def test_emotional_intelligence_service_compatibility(self):
        """Test EmotionalIntelligenceService legacy compatibility."""
        service = EmotionalIntelligenceService()
        
        messages = [{"role": "customer", "content": "Estoy preocupado por esta decisión"}]
        
        profile = await service.analyze_emotional_state(messages)
        insights = await service.get_emotional_insights(profile)
        
        assert isinstance(profile, EmotionalProfile)
        assert profile.primary_state == EmotionalState.ANXIOUS
        assert "current_state" in insights
        assert "voice_recommendations" in insights
    
    def test_advanced_sentiment_service_compatibility(self):
        """Test AdvancedSentimentService legacy compatibility."""
        service = AdvancedSentimentService()
        
        # Test sentiment analysis
        result = service.analyze_sentiment("Me siento muy feliz y emocionado")
        assert result["sentiment"] == "positive"
        assert result["confidence"] > 0.0
        
        # Test emotion detection
        emotions = service.detect_emotions("Estoy muy frustrado con esto")
        assert "frustration" in emotions
        assert emotions["frustration"] > 0.0
        
        # Test comprehensive analysis
        comprehensive = service.get_comprehensive_analysis("Este servicio es genial")
        assert "sentiment" in comprehensive
        assert "emotions" in comprehensive
        assert "dominant_emotion" in comprehensive
    
    def test_ultra_empathy_greeting_engine_compatibility(self):
        """Test UltraEmpathyGreetingEngine legacy compatibility."""
        engine = UltraEmpathyGreetingEngine()
        
        context = {
            "customer_name": "Ana",
            "initial_message": "Estoy buscando algo para mejorar mi energía"
        }
        
        greeting = engine.generate_ultra_empathetic_greeting(context)
        
        assert "Ana" in greeting
        assert len(greeting) > 50
        assert any(word in greeting.lower() for word in ["privilegio", "alegra", "gusto"])
    
    def test_ultra_empathy_price_handler_compatibility(self):
        """Test UltraEmpathyPriceHandler legacy compatibility."""
        handler = UltraEmpathyPriceHandler()
        
        context = {
            "objection_text": "El precio me parece muy alto",
            "customer_name": "Luis",
            "tier_mentioned": "pro"
        }
        
        result = handler.generate_ultra_empathetic_response(context)
        
        assert result["empathy_score"] == 10
        assert "Luis" in result["response"]
        assert "comprendo" in result["response"].lower()
    
    def test_sentiment_alert_service_compatibility(self):
        """Test SentimentAlertService legacy compatibility."""
        service = SentimentAlertService()
        
        conversation_id = "legacy_test_123"
        messages = [
            {"role": "customer", "content": "Esto está bien"},
            {"role": "customer", "content": "Ahora estoy muy frustrado"}
        ]
        
        alerts = service.monitor_conversation(conversation_id, messages)
        
        assert alerts["conversation_id"] == conversation_id
        if alerts["has_alerts"]:
            assert len(alerts["alerts"]) > 0
    
    @pytest.mark.asyncio
    async def test_adaptive_personality_service_compatibility(self):
        """Test AdaptivePersonalityService legacy compatibility."""
        service = AdaptivePersonalityService()
        
        messages = [
            {"role": "customer", "content": "Necesito datos específicos y evidencia"},
            {"role": "customer", "content": "¿Cuáles son las métricas exactas?"}
        ]
        
        profile = await service.analyze_personality(messages)
        insights = service.generate_personality_insights(profile)
        
        assert profile["communication_style"] == "analytical"
        assert "key_characteristics" in insights
        assert "do_recommendations" in insights
        assert "closing_strategy" in insights


class TestEmpathyFeatureFlags:
    """Test suite for empathy feature flags."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.flags = EmpathyFeatureFlags()
    
    def test_feature_flag_initialization(self):
        """Test feature flags are properly initialized."""
        assert self.flags.environment is not None
        assert self.flags.rollout_stage is not None
        assert len(self.flags.flags) == len(EmpathyFeature)
        
        # Check that all features are properly configured
        for feature in EmpathyFeature:
            assert feature in self.flags.flags
            config = self.flags.flags[feature]
            assert hasattr(config, 'enabled')
            assert hasattr(config, 'rollout_percentage')
            assert hasattr(config, 'environments')
    
    def test_feature_enablement_logic(self):
        """Test feature enablement logic."""
        # Test basic enablement
        self.flags.update_feature_flag(
            EmpathyFeature.CONSOLIDATED_SERVICE,
            enabled=True,
            rollout_percentage=100.0
        )
        
        assert self.flags.is_enabled(EmpathyFeature.CONSOLIDATED_SERVICE)
        
        # Test emergency disable
        self.flags.update_feature_flag(
            EmpathyFeature.CONSOLIDATED_SERVICE,
            emergency_disable=True
        )
        
        assert not self.flags.is_enabled(EmpathyFeature.CONSOLIDATED_SERVICE)
    
    def test_rollout_percentage_logic(self):
        """Test rollout percentage logic."""
        # Set 50% rollout
        self.flags.update_feature_flag(
            EmpathyFeature.PATTERN_RECOGNITION,
            enabled=True,
            rollout_percentage=50.0
        )
        
        # Test with consistent user IDs
        enabled_count = 0
        for i in range(100):
            if self.flags.is_enabled(EmpathyFeature.PATTERN_RECOGNITION, f"user_{i}"):
                enabled_count += 1
        
        # Should be approximately 50% (allow some variance due to hashing)
        assert 40 <= enabled_count <= 60
    
    def test_dependency_checking(self):
        """Test feature dependency checking."""
        # Disable parent feature
        self.flags.update_feature_flag(
            EmpathyFeature.CONSOLIDATED_SERVICE,
            enabled=False
        )
        
        # Child feature should be disabled even if enabled
        self.flags.update_feature_flag(
            EmpathyFeature.ADVANCED_SENTIMENT,
            enabled=True,
            rollout_percentage=100.0
        )
        
        assert not self.flags.is_enabled(EmpathyFeature.ADVANCED_SENTIMENT)
    
    def test_consolidated_service_decision_logic(self):
        """Test consolidated service decision logic."""
        # Test different rollout stages
        self.flags.rollout_stage = RolloutStage.DISABLED
        assert not self.flags.should_use_consolidated_service()
        
        self.flags.rollout_stage = RolloutStage.FULL
        self.flags.update_feature_flag(
            EmpathyFeature.CONSOLIDATED_SERVICE,
            enabled=True,
            rollout_percentage=100.0
        )
        assert self.flags.should_use_consolidated_service()
    
    def test_performance_tracking(self):
        """Test performance tracking and auto-disable."""
        metrics = EmpathyMetrics(
            response_time_ms=6000.0,  # High response time
            empathy_score=8.5,
            error_rate=15.0,  # High error rate
            user_satisfaction=7.0
        )
        
        # Initially enabled
        self.flags.update_feature_flag(
            EmpathyFeature.LEARNING_SYSTEM,
            enabled=True,
            emergency_disable=False
        )
        
        # Track poor performance
        self.flags.track_performance(EmpathyFeature.LEARNING_SYSTEM, metrics)
        
        # Should be emergency disabled due to high error rate
        config = self.flags.get_feature_config(EmpathyFeature.LEARNING_SYSTEM)
        assert config.emergency_disable == True
    
    def test_a_b_testing_setup(self):
        """Test A/B testing functionality."""
        test_name = "empathy_greeting_test"
        
        self.flags.setup_a_b_test(
            test_name=test_name,
            feature=EmpathyFeature.ULTRA_EMPATHY_GREETINGS,
            control_percentage=50.0,
            variant_percentage=50.0
        )
        
        assert test_name in self.flags.a_b_test_groups
        
        # Test consistent group assignment
        user_id = "test_user_123"
        group1 = self.flags.get_a_b_test_group(test_name, user_id)
        group2 = self.flags.get_a_b_test_group(test_name, user_id)
        
        assert group1 == group2  # Should be consistent
        assert group1 in ["control", "variant"]
    
    def test_configuration_export_import(self):
        """Test configuration export and import."""
        # Modify some settings
        self.flags.update_feature_flag(
            EmpathyFeature.CONSOLIDATED_SERVICE,
            enabled=True,
            rollout_percentage=75.0
        )
        
        # Export configuration
        config = self.flags.export_configuration()
        
        assert "flags" in config
        assert "environment" in config
        assert "rollout_stage" in config
        assert "export_timestamp" in config
        
        # Check specific feature config
        consolidated_config = config["flags"]["consolidated_service"]
        assert consolidated_config["enabled"] == True
        assert consolidated_config["rollout_percentage"] == 75.0
    
    def test_status_report_generation(self):
        """Test status report generation."""
        # Add some metrics
        metrics = EmpathyMetrics(
            response_time_ms=45.0,
            empathy_score=9.2,
            error_rate=1.5,
            user_satisfaction=8.8
        )
        
        self.flags.track_performance(EmpathyFeature.CONSOLIDATED_SERVICE, metrics)
        
        # Generate report
        report = self.flags.get_feature_status_report()
        
        assert "environment" in report
        assert "features" in report
        assert "metrics" in report
        assert len(report["features"]) == len(EmpathyFeature)
        
        # Check metrics are included
        if EmpathyFeature.CONSOLIDATED_SERVICE.value in report["metrics"]:
            metric_data = report["metrics"][EmpathyFeature.CONSOLIDATED_SERVICE.value]
            assert metric_data["response_time_ms"] == 45.0
            assert metric_data["empathy_score"] == 9.2


class TestIntegrationScenarios:
    """Test integration scenarios and end-to-end workflows."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.service = ConsolidatedEmpathyIntelligenceService()
        self.flags = EmpathyFeatureFlags()
    
    @pytest.mark.asyncio
    async def test_complete_empathy_workflow(self):
        """Test complete empathy workflow from analysis to response."""
        # Scenario: Customer expressing frustration about price
        customer_message = "Me parece muy caro, no sé si puedo permitirme $149 al mes"
        conversation_history = [
            {"role": "assistant", "content": "¡Hola! ¿Cómo puedo ayudarte?"},
            {"role": "customer", "content": "Estoy interesado en sus servicios"},
            {"role": "assistant", "content": "Excelente, déjame mostrarte nuestros planes"},
            {"role": "customer", "content": customer_message}
        ]
        
        customer_profile = CustomerData(name="Roberto", preferred_language="spanish")
        context = {"conversation_id": "workflow_test", "phase": "price_discussion"}
        
        # Step 1: Comprehensive empathy analysis
        result = await self.service.generate_comprehensive_empathy_response(
            message=customer_message,
            conversation_history=conversation_history,
            customer_profile=customer_profile,
            context=context
        )
        
        # Validate emotional analysis
        assert result["emotional_profile"].primary_state in [
            EmotionalState.ANXIOUS, EmotionalState.FRUSTRATED, EmotionalState.HESITANT
        ]
        
        # Step 2: Generate price objection response
        price_response = self.service.handle_price_objection_with_ultra_empathy(
            objection_message=customer_message,
            customer_name="Roberto",
            tier_mentioned="pro"
        )
        
        # Validate price objection handling
        assert price_response["empathy_score"] == 10
        assert "Roberto" in price_response["response"]
        assert any(word in price_response["response"].lower() for word in ["comprendo", "entiendo", "valoro"])
        
        # Step 3: Check for alerts
        alerts = result["alerts"]
        if alerts["has_alerts"]:
            assert len(alerts["recommendations"]) > 0
        
        # Step 4: Validate conversation patterns
        patterns = result["conversation_patterns"]
        assert patterns["conversation_phase"] == "price_discussion"
        assert patterns["patterns"]["price_sensitivity"] > 0
    
    def test_feature_flag_controlled_rollout(self):
        """Test feature flag controlled rollout scenario."""
        # Scenario: Gradual rollout of new feature
        self.flags.rollout_stage = RolloutStage.BETA
        self.flags.update_feature_flag(
            EmpathyFeature.PATTERN_RECOGNITION,
            enabled=True,
            rollout_percentage=25.0  # 25% rollout
        )
        
        # Test consistent user assignment
        beta_users = []
        control_users = []
        
        for i in range(100):
            user_id = f"user_{i}"
            if self.flags.is_enabled(EmpathyFeature.PATTERN_RECOGNITION, user_id):
                beta_users.append(user_id)
            else:
                control_users.append(user_id)
        
        # Should be approximately 25% in beta
        assert 20 <= len(beta_users) <= 30
        assert 70 <= len(control_users) <= 80
        
        # Verify consistency (same user should always get same result)
        for user in beta_users[:5]:
            assert self.flags.is_enabled(EmpathyFeature.PATTERN_RECOGNITION, user)
        
        for user in control_users[:5]:
            assert not self.flags.is_enabled(EmpathyFeature.PATTERN_RECOGNITION, user)
    
    @pytest.mark.asyncio
    async def test_legacy_to_consolidated_migration(self):
        """Test migration from legacy services to consolidated service."""
        # Test that both legacy and consolidated produce similar results
        
        # Legacy sentiment analysis
        legacy_sentiment = AdvancedSentimentService()
        legacy_result = legacy_sentiment.analyze_sentiment("Me siento muy feliz hoy")
        
        # Consolidated sentiment analysis
        consolidated_result = self.service.analyze_advanced_sentiment("Me siento muy feliz hoy")
        
        # Results should be compatible
        assert legacy_result["sentiment"] == consolidated_result["sentiment"]
        assert abs(legacy_result["score"] - consolidated_result["score"]) < 0.2
        
        # Test empathy response compatibility
        messages = [{"role": "customer", "content": "Estoy confundido sobre esto"}]
        
        # Legacy emotional analysis
        legacy_emotional = EmotionalIntelligenceService()
        legacy_profile = await legacy_emotional.analyze_emotional_state(messages)
        
        # Consolidated emotional analysis  
        consolidated_profile = await self.service.analyze_emotional_state(messages)
        
        # Should detect similar emotional states
        assert legacy_profile.primary_state == consolidated_profile.primary_state
        assert abs(legacy_profile.intensity - consolidated_profile.intensity) < 0.3
    
    def test_error_handling_and_fallbacks(self):
        """Test error handling and fallback mechanisms."""
        # Test with invalid input
        result = self.service.analyze_advanced_sentiment("")
        assert result["sentiment"] == "neutral"
        assert result["confidence"] >= 0.0
        
        # Test with very long input
        very_long_text = "palabra " * 1000
        result = self.service.analyze_advanced_sentiment(very_long_text)
        assert "sentiment" in result
        assert result["word_count"] == 1000
        
        # Test personality detection with no clear signals
        unclear_messages = ["ok", "bien", "sí"]
        personality_result = self.service.detect_personality_style(unclear_messages)
        assert personality_result["dominant_style"] == "amiable"  # Default
        assert personality_result["confidence"] >= 0.0
    
    @pytest.mark.asyncio 
    async def test_performance_under_load(self):
        """Test performance under simulated load."""
        import asyncio
        import time
        
        async def process_message(i):
            message = f"Test message number {i}"
            start_time = time.time()
            
            result = await self.service.generate_comprehensive_empathy_response(
                message=message,
                conversation_history=[{"role": "customer", "content": message}],
                context={"conversation_id": f"perf_test_{i}"}
            )
            
            end_time = time.time()
            processing_time = (end_time - start_time) * 1000  # milliseconds
            
            return {"processing_time": processing_time, "success": "empathy_response" in result}
        
        # Process 10 messages concurrently
        tasks = [process_message(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Validate performance
        avg_time = sum(r["processing_time"] for r in results) / len(results)
        success_rate = sum(r["success"] for r in results) / len(results)
        
        assert avg_time < 100  # Average under 100ms
        assert success_rate == 1.0  # 100% success rate
        
        # No individual request should take too long
        max_time = max(r["processing_time"] for r in results)
        assert max_time < 200  # No request over 200ms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])