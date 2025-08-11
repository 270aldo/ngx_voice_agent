"""
Consolidated Conversation Orchestrator

Updated orchestrator using the new consolidated service architecture.
This orchestrator uses 6 core consolidated services instead of 45+ individual services.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime
from io import BytesIO
import uuid

from src.models.conversation import ConversationState, CustomerData, Message
from src.models.platform_context import PlatformContext, PlatformInfo, SourceType, PlatformType
from src.core.agent_factory import agent_factory, AgentInterface
from src.core.platform_config import PlatformConfigManager
from src.integrations.elevenlabs import voice_engine
from src.integrations.supabase.resilient_client import resilient_supabase_client as supabase_client

# Import consolidated services
from src.services.cache_service import CacheService, get_cache_instance
from src.services.empathy_intelligence_service import EmpathyIntelligenceService
from src.services.ml_prediction_service import MLPredictionService, PredictionType
from src.services.nlp_analysis_service import NLPAnalysisService
from src.services.experimentation_service import ExperimentationService, VariantType
from src.services.sales_intelligence_service import SalesIntelligenceService
from src.services.infrastructure_service import InfrastructureService

# Import mixins that are still relevant
from .base import BaseConversationService
from .ml_tracking import MLTrackingMixin
from .tier_management import TierManagementMixin
from .emotional_processing import EmotionalProcessingMixin
from .sales_strategy import SalesStrategyMixin

logger = logging.getLogger(__name__)


class ConsolidatedConversationOrchestrator(
    BaseConversationService,
    MLTrackingMixin,
    TierManagementMixin,
    EmotionalProcessingMixin,
    SalesStrategyMixin
):
    """
    Consolidated conversation orchestrator using 6 core services.
    
    This orchestrator replaces 45+ individual services with:
    1. CacheService - All caching functionality
    2. EmpathyIntelligenceService - Empathy and emotional intelligence
    3. MLPredictionService - All ML predictions
    4. NLPAnalysisService - NLP, intent analysis, entity recognition
    5. ExperimentationService - A/B testing and optimization
    6. SalesIntelligenceService - ROI, tier detection, qualification
    7. InfrastructureService - Security, circuit breakers, utilities
    """
    
    def __init__(self, industry: str = 'salud', platform_context: Optional[PlatformContext] = None):
        """
        Initialize the consolidated conversation orchestrator.
        
        Args:
            industry: Industry for intent analysis customization
            platform_context: Platform context (optional)
        """
        # Initialize parent classes
        BaseConversationService.__init__(self, industry)
        MLTrackingMixin.__init__(self)
        TierManagementMixin.__init__(self)
        EmotionalProcessingMixin.__init__(self)
        SalesStrategyMixin.__init__(self)
        
        self.platform_context = platform_context
        self.industry = industry
        
        # Initialize consolidated services
        self.cache_service: Optional[CacheService] = None
        self.empathy_service = EmpathyIntelligenceService()
        self.ml_prediction_service = MLPredictionService()
        self.nlp_service = NLPAnalysisService()
        self.experimentation_service = ExperimentationService()
        self.sales_intelligence_service = SalesIntelligenceService()
        self.infrastructure_service = InfrastructureService()
        
        # Legacy compatibility - maintain references for existing code
        self._setup_legacy_compatibility()
        
        logger.info(f"ConsolidatedConversationOrchestrator initialized for industry: {industry}")
    
    def _setup_legacy_compatibility(self) -> None:
        """Setup compatibility references for existing code."""
        # Map old service references to new consolidated services
        
        # Intent and NLP services -> NLP Analysis Service
        self.intent_analysis_service = self._create_intent_wrapper()
        self.enhanced_intent_service = self._create_enhanced_intent_wrapper()
        self.entity_recognition_service = self._create_entity_wrapper()
        self.nlp_integration_service = self._create_nlp_wrapper()
        
        # Empathy services -> Empathy Intelligence Service
        self.advanced_empathy_engine = self._create_empathy_wrapper()
        self.emotional_intelligence_service = self._create_emotional_wrapper()
        
        # Prediction services -> ML Prediction Service
        self.objection_predictor = self._create_objection_wrapper()
        self.needs_predictor = self._create_needs_wrapper()
        self.conversion_predictor = self._create_conversion_wrapper()
        
        # Sales services -> Sales Intelligence Service
        self.qualification_service = self._create_qualification_wrapper()
        self.tier_detection_service = self._create_tier_wrapper()
        self.roi_calculator = self._create_roi_wrapper()
        
        # A/B testing -> Experimentation Service
        self.ab_testing_framework = self._create_ab_testing_wrapper()
        
        # Infrastructure services
        self.circuit_breaker_service = self._create_circuit_breaker_wrapper()
        self.encryption_service = self._create_encryption_wrapper()
        
        # Cache services -> Cache Service
        self.cache_manager = None  # Will be set in initialize()
        self.response_cache = self._create_response_cache_wrapper()
    
    async def initialize(self) -> None:
        """Initialize all consolidated services."""
        if self._initialized:
            return
        
        try:
            # Initialize cache service first (needed by others)
            self.cache_service = await get_cache_instance()
            self.cache_manager = self.cache_service  # Legacy compatibility
            
            # Initialize ML prediction service
            await self.ml_prediction_service.initialize_models()
            
            # Initialize experimentation service with default experiments
            await self._setup_default_experiments()
            
            # Initialize infrastructure service components
            await self._setup_circuit_breakers()
            
            # Initialize parent mixins
            if hasattr(super(), 'initialize'):
                await super().initialize()
            
            self._initialized = True
            logger.info("ConsolidatedConversationOrchestrator fully initialized")
            
        except Exception as e:
            logger.error(f"Error initializing ConsolidatedConversationOrchestrator: {e}")
            raise
    
    async def _setup_default_experiments(self) -> None:
        """Setup default A/B testing experiments."""
        try:
            # Create greeting optimization experiment
            greeting_experiment = await self.experimentation_service.create_experiment_from_template(
                VariantType.GREETING
            )
            await self.experimentation_service.start_experiment(greeting_experiment)
            
            # Create pricing presentation experiment
            pricing_experiment = await self.experimentation_service.create_experiment_from_template(
                VariantType.PRICING_PRESENTATION
            )
            await self.experimentation_service.start_experiment(pricing_experiment)
            
            logger.info("Default A/B testing experiments initialized")
            
        except Exception as e:
            logger.warning(f"Could not setup default experiments: {e}")
    
    async def _setup_circuit_breakers(self) -> None:
        """Setup circuit breakers for critical services."""
        # Example circuit breakers for external services
        @self.infrastructure_service.circuit_breaker("supabase", failure_threshold=3, recovery_timeout=30)
        async def protected_supabase_call(*args, **kwargs):
            # This would be used for Supabase calls
            pass
        
        @self.infrastructure_service.circuit_breaker("openai", failure_threshold=5, recovery_timeout=60)
        async def protected_openai_call(*args, **kwargs):
            # This would be used for OpenAI calls
            pass
        
        logger.info("Circuit breakers configured")
    
    async def process_message(
        self,
        message: str,
        conversation_id: str,
        customer_data: Optional[CustomerData] = None,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message using consolidated services.
        
        Args:
            message: Customer's message
            conversation_id: Conversation identifier
            customer_data: Customer data
            conversation_context: Current conversation context
            
        Returns:
            Complete response with analysis and recommendations
        """
        await self._ensure_initialized()
        
        try:
            # 1. NLP Analysis - comprehensive text understanding
            nlp_result = await self.nlp_service.analyze_text(
                text=message,
                conversation_context=conversation_context,
                customer_id=customer_data.id if customer_data else None
            )
            
            # 2. Emotional Analysis - understand customer's emotional state
            emotional_profile = await self.empathy_service.analyze_emotional_state(
                message=message,
                conversation_history=conversation_context.get('message_history', []) if conversation_context else None,
                customer_profile=customer_data
            )
            
            # 3. ML Predictions - predict customer behavior and needs
            prediction_tasks = [
                (PredictionType.CONVERSION, self._extract_conversion_features(nlp_result, emotional_profile)),
                (PredictionType.OBJECTION, self._extract_objection_features(nlp_result, conversation_context)),
                (PredictionType.NEEDS, self._extract_needs_features(customer_data, conversation_context))
            ]
            
            ml_predictions = await self.ml_prediction_service.predict_multiple(prediction_tasks)
            
            # 4. Sales Intelligence - business analysis and recommendations
            business_profile = None
            if customer_data:
                business_profile = await self.sales_intelligence_service.create_business_profile(
                    customer_data, conversation_context
                )
                
                # Get tier recommendation
                tier_recommendation = await self.sales_intelligence_service.detect_optimal_tier(
                    business_profile
                )
                
                # Calculate ROI for recommended tier
                roi_analysis = await self.sales_intelligence_service.calculate_roi(
                    business_profile, tier_recommendation.recommended_tier
                )
                
                # Qualify lead
                lead_score = await self.sales_intelligence_service.qualify_lead(
                    business_profile, conversation_context
                )
            
            # 5. Generate Empathetic Response
            empathy_strategy = await self.empathy_service.generate_empathy_strategy(
                emotional_profile, conversation_context or {}, customer_data
            )
            
            empathy_response = await self.empathy_service.generate_empathy_response(
                message, emotional_profile, empathy_strategy, conversation_context or {}
            )
            
            # 6. A/B Testing - get variant for response optimization
            greeting_variant = await self.experimentation_service.get_variant(
                VariantType.GREETING, conversation_context
            )
            
            # 7. Cache the results for faster future responses
            if self.cache_service:
                cache_key = f"analysis:{conversation_id}:{hash(message)}"
                await self.cache_service.set(
                    cache_key,
                    {
                        "nlp_result": nlp_result.__dict__,
                        "emotional_profile": emotional_profile.__dict__,
                        "ml_predictions": {k.value: v.__dict__ for k, v in ml_predictions.items()},
                        "empathy_response": empathy_response.__dict__
                    },
                    ttl=1800  # 30 minutes
                )
            
            # Compile comprehensive response
            response = {
                "analysis": {
                    "intent": nlp_result.intent_result.intent.value,
                    "confidence": nlp_result.intent_result.confidence,
                    "emotional_state": emotional_profile.primary_state.value,
                    "emotional_intensity": emotional_profile.intensity,
                    "entities": [entity.__dict__ for entity in nlp_result.entities],
                    "keywords": [keyword.__dict__ for keyword in nlp_result.keywords]
                },
                "predictions": {
                    "conversion_probability": ml_predictions.get(PredictionType.CONVERSION, {}).probability if ml_predictions.get(PredictionType.CONVERSION) else 0.5,
                    "objection_likelihood": ml_predictions.get(PredictionType.OBJECTION, {}).probability if ml_predictions.get(PredictionType.OBJECTION) else 0.3,
                    "needs_assessment": ml_predictions.get(PredictionType.NEEDS, {}).metadata if ml_predictions.get(PredictionType.NEEDS) else {}
                },
                "empathy": {
                    "response_intro": empathy_response.intro_phrase,
                    "core_message": empathy_response.core_message,
                    "closing": empathy_response.closing_phrase,
                    "technique": empathy_response.technique_used.value,
                    "voice_persona": empathy_response.voice_persona.value
                },
                "recommendations": {
                    "action_items": lead_score.action_recommendations if business_profile else [],
                    "priority_level": lead_score.priority_level if business_profile else 3,
                    "recommended_tier": tier_recommendation.recommended_tier.value if business_profile else "PROFESSIONAL",
                    "roi_summary": {
                        "monthly_roi": roi_analysis.monthly_roi if business_profile else 0,
                        "breakeven_months": roi_analysis.breakeven_months if business_profile else 12
                    } if business_profile else {}
                },
                "ab_testing": {
                    "greeting_variant": greeting_variant
                },
                "processing_time_ms": nlp_result.processing_time_ms,
                "conversation_id": conversation_id
            }
            
            # Record A/B testing impression if variant was served
            if greeting_variant:
                await self.experimentation_service._record_impression(
                    greeting_variant["experiment_id"],
                    greeting_variant["variant_id"]
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Return fallback response
            return {
                "analysis": {"intent": "information_seeking", "confidence": 0.3, "emotional_state": "neutral"},
                "empathy": {"response_intro": "Entiendo", "core_message": "Déjame ayudarte", "closing": "¿En qué más puedo asistirte?"},
                "error": str(e),
                "conversation_id": conversation_id
            }
    
    def _extract_conversion_features(self, nlp_result, emotional_profile) -> Dict[str, Any]:
        """Extract features for conversion prediction."""
        return {
            "engagement_score": emotional_profile.intensity,
            "intent_confidence": nlp_result.intent_result.confidence,
            "positive_sentiment": max(0, nlp_result.sentiment_score),
            "question_asked": nlp_result.question_analysis is not None,
            "entities_mentioned": len(nlp_result.entities)
        }
    
    def _extract_objection_features(self, nlp_result, conversation_context) -> Dict[str, Any]:
        """Extract features for objection prediction."""
        return {
            "current_message": nlp_result.intent_result.intent.value,
            "conversation_stage": conversation_context.get("stage", "discovery") if conversation_context else "discovery",
            "sentiment_negative": nlp_result.sentiment_score < 0,
            "entities_price_mentioned": any(e.entity_type.value == "price" for e in nlp_result.entities)
        }
    
    def _extract_needs_features(self, customer_data, conversation_context) -> Dict[str, Any]:
        """Extract features for needs prediction."""
        features = {
            "industry": customer_data.industry if customer_data else "fitness",
            "company_size": "medium"  # default
        }
        
        if conversation_context:
            features.update({
                "monthly_revenue": conversation_context.get("monthly_revenue", 10000),
                "member_count": conversation_context.get("member_count", 200),
                "staff_count": conversation_context.get("staff_count", 3)
            })
        
        return features
    
    # Legacy compatibility wrapper methods
    
    def _create_intent_wrapper(self):
        """Create wrapper for legacy intent analysis service."""
        class IntentAnalysisWrapper:
            def __init__(self, nlp_service):
                self.nlp_service = nlp_service
            
            async def analyze_intent(self, message: str) -> Dict[str, Any]:
                result = await self.nlp_service.analyze_text(message)
                return {
                    "intent": result.intent_result.intent.value,
                    "confidence": result.intent_result.confidence,
                    "reasoning": result.intent_result.reasoning
                }
        
        return IntentAnalysisWrapper(self.nlp_service)
    
    def _create_enhanced_intent_wrapper(self):
        """Create wrapper for enhanced intent analysis."""
        class EnhancedIntentWrapper:
            def __init__(self, nlp_service):
                self.nlp_service = nlp_service
            
            async def analyze_enhanced_intent(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
                result = await self.nlp_service.analyze_text(message, context)
                return {
                    "intent": result.intent_result.intent.value,
                    "confidence": result.intent_result.confidence,
                    "sub_intents": [si.value for si in result.intent_result.sub_intents],
                    "entities": [e.__dict__ for e in result.entities]
                }
        
        return EnhancedIntentWrapper(self.nlp_service)
    
    def _create_empathy_wrapper(self):
        """Create wrapper for advanced empathy engine."""
        class EmpathyWrapper:
            def __init__(self, empathy_service):
                self.empathy_service = empathy_service
            
            async def generate_empathetic_response(self, message: str, context: Dict[str, Any]) -> str:
                emotional_profile = await self.empathy_service.analyze_emotional_state(message)
                strategy = await self.empathy_service.generate_empathy_strategy(emotional_profile, context)
                response = await self.empathy_service.generate_empathy_response(message, emotional_profile, strategy, context)
                return f"{response.intro_phrase} {response.core_message} {response.closing_phrase}"
        
        return EmpathyWrapper(self.empathy_service)
    
    def _create_qualification_wrapper(self):
        """Create wrapper for qualification service."""
        class QualificationWrapper:
            def __init__(self, sales_service):
                self.sales_service = sales_service
            
            async def qualify_lead(self, customer_data: CustomerData) -> Dict[str, Any]:
                profile = await self.sales_service.create_business_profile(customer_data)
                score = await self.sales_service.qualify_lead(profile)
                return {
                    "score": score.overall_score,
                    "quality": score.quality.value,
                    "recommendations": score.action_recommendations
                }
            
            async def _check_cooldown(self, customer_id: str) -> Dict[str, Any]:
                # Simplified cooldown check
                return {"in_cooldown": False, "hours_remaining": 0}
        
        return QualificationWrapper(self.sales_intelligence_service)
    
    def _create_roi_wrapper(self):
        """Create wrapper for ROI calculator."""
        class ROIWrapper:
            def __init__(self, sales_service):
                self.sales_service = sales_service
            
            async def calculate_roi(self, customer_data: CustomerData, tier: str) -> Dict[str, Any]:
                from src.services.sales_intelligence_service import NGXTier
                profile = await self.sales_service.create_business_profile(customer_data)
                roi = await self.sales_service.calculate_roi(profile, NGXTier(tier))
                return {
                    "monthly_roi": roi.monthly_roi,
                    "annual_roi": roi.annual_roi,
                    "payback_days": roi.payback_period_days
                }
        
        return ROIWrapper(self.sales_intelligence_service)
    
    # Additional wrapper methods for other legacy services...
    def _create_entity_wrapper(self): return self.nlp_service
    def _create_nlp_wrapper(self): return self.nlp_service
    def _create_emotional_wrapper(self): return self.empathy_service
    def _create_objection_wrapper(self): return self.ml_prediction_service
    def _create_needs_wrapper(self): return self.ml_prediction_service
    def _create_conversion_wrapper(self): return self.ml_prediction_service
    def _create_tier_wrapper(self): return self.sales_intelligence_service
    def _create_ab_testing_wrapper(self): return self.experimentation_service
    def _create_circuit_breaker_wrapper(self): return self.infrastructure_service
    def _create_encryption_wrapper(self): return self.infrastructure_service
    def _create_response_cache_wrapper(self): return self.cache_service
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all consolidated services."""
        stats = {
            "orchestrator": {
                "initialized": self._initialized,
                "industry": self.industry,
                "platform_context": self.platform_context is not None
            }
        }
        
        # Get stats from each consolidated service
        if self.cache_service:
            stats["cache"] = await self.cache_service.get_service_stats()
        
        stats["empathy"] = await self.empathy_service.get_service_stats()
        stats["ml_prediction"] = await self.ml_prediction_service.get_service_stats()
        stats["nlp"] = await self.nlp_service.get_service_stats()
        stats["experimentation"] = await self.experimentation_service.get_service_stats()
        stats["sales_intelligence"] = await self.sales_intelligence_service.get_service_stats()
        stats["infrastructure"] = await self.infrastructure_service.get_service_stats()
        
        return stats