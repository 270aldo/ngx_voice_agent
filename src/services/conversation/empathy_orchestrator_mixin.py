"""
Empathy Orchestrator Mixin for NGX Voice Sales Agent.

This mixin integrates the consolidated empathy intelligence service
into the conversation orchestrator with feature flag support.

Features:
- Smart routing between consolidated and legacy services
- Performance monitoring and fallback
- A/B testing integration
- Seamless empathy orchestration
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import time

from src.services.consolidated_empathy_intelligence_service import (
    ConsolidatedEmpathyIntelligenceService,
    EmotionalProfile,
    EmpathyResponse,
    EmotionalState
)
from src.services.empathy_compatibility import get_consolidated_service
from src.config.empathy_feature_flags import (
    get_empathy_flags,
    EmpathyFeature,
    EmpathyMetrics,
    use_consolidated_service,
    is_feature_enabled,
    track_empathy_performance
)
from src.models.conversation import CustomerData, ConversationState
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)


class EmpathyOrchestratorMixin:
    """
    Mixin for integrating consolidated empathy intelligence into the orchestrator.
    
    This mixin provides:
    - Smart routing between consolidated and legacy empathy services
    - Performance monitoring and automatic fallback
    - Feature flag controlled rollout
    - A/B testing for empathy strategies
    - Comprehensive empathy orchestration
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize empathy orchestrator mixin."""
        super().__init__(*args, **kwargs)
        
        # Initialize consolidated service
        self._consolidated_empathy = None
        self._empathy_flags = get_empathy_flags()
        
        # Performance tracking
        self._empathy_performance_metrics = {}
        self._empathy_fallback_count = 0
        
        # A/B testing configuration
        self._empathy_ab_tests = {}
        
        logger.info("EmpathyOrchestratorMixin initialized with feature flag support")
    
    @property
    def consolidated_empathy(self) -> ConsolidatedEmpathyIntelligenceService:
        """Get consolidated empathy service instance."""
        if self._consolidated_empathy is None:
            self._consolidated_empathy = get_consolidated_service()
        return self._consolidated_empathy
    
    def should_use_consolidated_empathy(self, customer_id: Optional[str] = None) -> bool:
        """
        Determine if consolidated empathy service should be used.
        
        Args:
            customer_id: Customer identifier for consistent routing
            
        Returns:
            True if consolidated service should be used
        """
        try:
            # Check global feature flag
            if not use_consolidated_service(customer_id):
                return False
            
            # Check consolidated service feature specifically
            if not is_feature_enabled(EmpathyFeature.CONSOLIDATED_SERVICE, customer_id):
                return False
            
            # Check if we're in emergency fallback mode
            if self._empathy_fallback_count > 10:  # Too many failures
                logger.warning("Empathy service in fallback mode due to failures")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking empathy service routing: {e}")
            return False
    
    async def analyze_customer_emotion(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[CustomerData] = None,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[EmotionalProfile, Dict[str, Any]]:
        """
        Analyze customer emotional state with smart routing.
        
        Args:
            messages: Conversation messages
            customer_profile: Customer profile data
            conversation_context: Additional context
            
        Returns:
            Tuple of (EmotionalProfile, analysis_metadata)
        """
        customer_id = customer_profile.customer_id if customer_profile else None
        start_time = time.time()
        
        try:
            if self.should_use_consolidated_empathy(customer_id):
                # Use consolidated service
                logger.info("Using consolidated empathy service for emotional analysis")
                
                profile = await self.consolidated_empathy.analyze_emotional_state(
                    messages=messages,
                    customer_profile=customer_profile
                )
                
                processing_time = (time.time() - start_time) * 1000
                
                # Track performance
                metrics = EmpathyMetrics(
                    response_time_ms=processing_time,
                    empathy_score=8.0,  # Default good score
                    error_rate=0.0,
                    user_satisfaction=profile.confidence * 10
                )
                
                track_empathy_performance(EmpathyFeature.CONSOLIDATED_SERVICE, metrics)
                
                analysis_metadata = {
                    "service_used": "consolidated",
                    "processing_time_ms": processing_time,
                    "confidence": profile.confidence,
                    "features_enabled": {
                        "advanced_sentiment": is_feature_enabled(EmpathyFeature.ADVANCED_SENTIMENT, customer_id),
                        "personality_detection": is_feature_enabled(EmpathyFeature.PERSONALITY_DETECTION, customer_id),
                        "pattern_recognition": is_feature_enabled(EmpathyFeature.PATTERN_RECOGNITION, customer_id)
                    }
                }
                
                return profile, analysis_metadata
            
            else:
                # Fall back to legacy service
                return await self._analyze_emotion_legacy(messages, customer_profile, conversation_context)
                
        except Exception as e:
            logger.error(f"Error in emotional analysis: {e}")
            self._empathy_fallback_count += 1
            
            # Emergency fallback to legacy
            return await self._analyze_emotion_legacy(messages, customer_profile, conversation_context)
    
    async def _analyze_emotion_legacy(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[CustomerData],
        conversation_context: Optional[Dict[str, Any]]
    ) -> Tuple[EmotionalProfile, Dict[str, Any]]:
        """Legacy emotional analysis fallback."""
        try:
            # Use existing emotional processing from the mixin
            if hasattr(self, 'analyze_emotional_context'):
                emotional_context = await self.analyze_emotional_context(messages[-1]["content"] if messages else "")
                
                # Convert legacy format to EmotionalProfile
                profile = EmotionalProfile(
                    primary_state=EmotionalState(emotional_context.get("primary_emotion", "neutral")),
                    intensity=emotional_context.get("intensity", 0.5),
                    confidence=emotional_context.get("confidence", 0.7),
                    triggers=emotional_context.get("triggers", []),
                    patterns=emotional_context.get("emotional_patterns", {})
                )
                
                metadata = {
                    "service_used": "legacy",
                    "processing_time_ms": 50.0,  # Estimated
                    "confidence": profile.confidence,
                    "fallback_reason": "feature_flag_disabled_or_error"
                }
                
                return profile, metadata
            else:
                # Absolute fallback - create basic profile
                profile = EmotionalProfile(
                    primary_state=EmotionalState.NEUTRAL,
                    intensity=0.5,
                    confidence=0.6
                )
                
                metadata = {
                    "service_used": "fallback",
                    "processing_time_ms": 10.0,
                    "confidence": 0.6,
                    "fallback_reason": "no_legacy_service_available"
                }
                
                return profile, metadata
                
        except Exception as e:
            logger.error(f"Error in legacy emotional analysis: {e}")
            # Ultimate fallback
            return EmotionalProfile(primary_state=EmotionalState.NEUTRAL, intensity=0.5, confidence=0.5), {
                "service_used": "emergency_fallback",
                "error": str(e)
            }
    
    async def generate_empathetic_response(
        self,
        message: str,
        emotional_profile: EmotionalProfile,
        conversation_history: List[Dict[str, Any]],
        customer_profile: Optional[CustomerData] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate empathetic response with smart routing.
        
        Args:
            message: Customer message
            emotional_profile: Customer emotional state
            conversation_history: Conversation history
            customer_profile: Customer profile
            context: Additional context
            
        Returns:
            Empathetic response with metadata
        """
        customer_id = customer_profile.customer_id if customer_profile else None
        start_time = time.time()
        
        try:
            if self.should_use_consolidated_empathy(customer_id):
                # Use consolidated service
                logger.info("Using consolidated empathy service for response generation")
                
                result = await self.consolidated_empathy.generate_comprehensive_empathy_response(
                    message=message,
                    conversation_history=conversation_history,
                    customer_profile=customer_profile,
                    context=context or {}
                )
                
                processing_time = (time.time() - start_time) * 1000
                
                # Track performance
                metrics = EmpathyMetrics(
                    response_time_ms=processing_time,
                    empathy_score=result.get("empathy_score", 8.0),
                    error_rate=0.0,
                    user_satisfaction=8.5
                )
                
                track_empathy_performance(EmpathyFeature.CONSOLIDATED_SERVICE, metrics)
                
                # Format response for orchestrator
                return {
                    "empathy_response": result["empathy_response"],
                    "empathy_score": result["empathy_score"],
                    "service_used": "consolidated",
                    "processing_time_ms": processing_time,
                    "emotional_analysis": result.get("sentiment_analysis", {}),
                    "personality_insights": result.get("personality_style", {}),
                    "conversation_patterns": result.get("conversation_patterns", {}),
                    "alerts": result.get("alerts", {}),
                    "recommendations": result.get("recommendations", [])
                }
            
            else:
                # Fall back to legacy empathy processing
                return await self._generate_empathy_response_legacy(
                    message, emotional_profile, conversation_history, customer_profile, context
                )
                
        except Exception as e:
            logger.error(f"Error generating empathetic response: {e}")
            self._empathy_fallback_count += 1
            
            return await self._generate_empathy_response_legacy(
                message, emotional_profile, conversation_history, customer_profile, context
            )
    
    async def _generate_empathy_response_legacy(
        self,
        message: str,
        emotional_profile: EmotionalProfile,
        conversation_history: List[Dict[str, Any]],
        customer_profile: Optional[CustomerData],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Legacy empathy response generation."""
        try:
            # Use existing empathy engine if available
            if hasattr(self, 'empathy_engine'):
                response = await self.empathy_engine.generate_intelligent_empathy({
                    "last_message": message,
                    "customer_profile": customer_profile,
                    "emotional_state": emotional_profile.primary_state.value,
                    "conversation_history": conversation_history
                })
                
                return {
                    "empathy_response": response,
                    "empathy_score": 7.5,  # Default legacy score
                    "service_used": "legacy",
                    "processing_time_ms": 75.0,
                    "fallback_reason": "feature_flag_disabled_or_error"
                }
            else:
                # Basic empathy response
                empathy_phrases = {
                    EmotionalState.FRUSTRATED: "Entiendo tu frustración, es totalmente válida.",
                    EmotionalState.ANXIOUS: "Comprendo tu preocupación, es normal sentirse así.",
                    EmotionalState.CONFUSED: "Permíteme aclararte esto de manera más simple.",
                    EmotionalState.EXCITED: "¡Comparto tu entusiasmo! Es genial verte tan emocionado.",
                    EmotionalState.SKEPTICAL: "Entiendo tu escepticismo, es una reacción inteligente."
                }
                
                intro_phrase = empathy_phrases.get(
                    emotional_profile.primary_state, 
                    "Entiendo tu punto de vista."
                )
                
                return {
                    "empathy_response": {
                        "intro_phrase": intro_phrase,
                        "core_message": "Estoy aquí para ayudarte de la mejor manera.",
                        "closing_phrase": "¿En qué más puedo asistirte?",
                        "empathy_score": 6.5
                    },
                    "empathy_score": 6.5,
                    "service_used": "basic_fallback",
                    "processing_time_ms": 15.0
                }
                
        except Exception as e:
            logger.error(f"Error in legacy empathy response: {e}")
            return {
                "empathy_response": {
                    "intro_phrase": "Entiendo tu situación",
                    "core_message": "Permíteme ayudarte",
                    "closing_phrase": "¿Cómo puedo asistirte mejor?",
                    "empathy_score": 6.0
                },
                "empathy_score": 6.0,
                "service_used": "emergency_fallback",
                "processing_time_ms": 5.0,
                "error": str(e)
            }
    
    async def generate_empathy_greeting(
        self,
        customer_profile: CustomerData,
        time_context: Optional[str] = None,
        initial_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate empathetic greeting with smart routing.
        
        Args:
            customer_profile: Customer profile
            time_context: Time of day context
            initial_message: Customer's initial message
            
        Returns:
            Empathetic greeting with metadata
        """
        customer_id = customer_profile.customer_id if customer_profile else None
        
        try:
            if (self.should_use_consolidated_empathy(customer_id) and 
                is_feature_enabled(EmpathyFeature.ULTRA_EMPATHY_GREETINGS, customer_id)):
                
                # Use consolidated service
                greeting = self.consolidated_empathy.generate_ultra_empathy_greeting(
                    customer_name=customer_profile.name or "Cliente",
                    initial_message=initial_message,
                    customer_profile=customer_profile
                )
                
                return {
                    "greeting": greeting,
                    "empathy_score": 10,
                    "service_used": "consolidated",
                    "personalized": True
                }
            
            else:
                # Legacy greeting generation
                return await self._generate_greeting_legacy(customer_profile, time_context, initial_message)
                
        except Exception as e:
            logger.error(f"Error generating empathy greeting: {e}")
            return await self._generate_greeting_legacy(customer_profile, time_context, initial_message)
    
    async def _generate_greeting_legacy(
        self,
        customer_profile: CustomerData,
        time_context: Optional[str],
        initial_message: Optional[str]
    ) -> Dict[str, Any]:
        """Legacy greeting generation."""
        try:
            # Use existing greeting engine if available
            if hasattr(self, 'greeting_engine'):
                context = {
                    "customer_name": customer_profile.name or "Cliente",
                    "initial_message": initial_message
                }
                greeting = self.greeting_engine.generate_ultra_empathetic_greeting(context)
                
                return {
                    "greeting": greeting,
                    "empathy_score": 8.5,
                    "service_used": "legacy",
                    "personalized": True
                }
            else:
                # Basic greeting
                name = customer_profile.name or "Cliente"
                greeting = f"¡Hola {name}! Me da mucho gusto poder ayudarte hoy. ¿En qué puedo asistirte?"
                
                return {
                    "greeting": greeting,
                    "empathy_score": 6.0,
                    "service_used": "basic_fallback",
                    "personalized": False
                }
                
        except Exception as e:
            logger.error(f"Error in legacy greeting generation: {e}")
            return {
                "greeting": "¡Hola! ¿Cómo puedo ayudarte hoy?",
                "empathy_score": 5.0,
                "service_used": "emergency_fallback",
                "personalized": False,
                "error": str(e)
            }
    
    async def handle_price_objection_empathetically(
        self,
        objection_message: str,
        customer_profile: CustomerData,
        tier_mentioned: str = "pro"
    ) -> Dict[str, Any]:
        """
        Handle price objections with empathy using smart routing.
        
        Args:
            objection_message: Customer's price objection
            customer_profile: Customer profile
            tier_mentioned: Tier being discussed
            
        Returns:
            Empathetic price objection response
        """
        customer_id = customer_profile.customer_id if customer_profile else None
        
        try:
            if (self.should_use_consolidated_empathy(customer_id) and 
                is_feature_enabled(EmpathyFeature.PRICE_OBJECTION_HANDLER, customer_id)):
                
                # Use consolidated service
                result = self.consolidated_empathy.handle_price_objection_with_ultra_empathy(
                    objection_message=objection_message,
                    customer_name=customer_profile.name or "Cliente",
                    tier_mentioned=tier_mentioned,
                    customer_profile=customer_profile
                )
                
                return {
                    **result,
                    "service_used": "consolidated"
                }
            
            else:
                # Legacy price objection handling
                return await self._handle_price_objection_legacy(
                    objection_message, customer_profile, tier_mentioned
                )
                
        except Exception as e:
            logger.error(f"Error handling price objection: {e}")
            return await self._handle_price_objection_legacy(
                objection_message, customer_profile, tier_mentioned
            )
    
    async def _handle_price_objection_legacy(
        self,
        objection_message: str,
        customer_profile: CustomerData,
        tier_mentioned: str
    ) -> Dict[str, Any]:
        """Legacy price objection handling."""
        try:
            # Use existing price handler if available
            if hasattr(self, 'price_handler'):
                context = {
                    "objection_text": objection_message,
                    "customer_name": customer_profile.name or "Cliente",
                    "tier_mentioned": tier_mentioned
                }
                result = self.price_handler.generate_ultra_empathetic_response(context)
                
                return {
                    **result,
                    "service_used": "legacy"
                }
            else:
                # Basic price objection response
                name = customer_profile.name or "Cliente"
                response = f"Entiendo tu preocupación sobre el precio, {name}. Déjame mostrarte el valor que recibes con NGX."
                
                return {
                    "response": response,
                    "empathy_score": 6.0,
                    "service_used": "basic_fallback",
                    "objection_type": "price_concern",
                    "follow_up_question": "¿Qué aspecto del valor te gustaría que aclaremos?",
                    "flexibility_options": ["¿Te ayudaría un plan de pago?"]
                }
                
        except Exception as e:
            logger.error(f"Error in legacy price objection handling: {e}")
            return {
                "response": "Comprendo tu preocupación. Permíteme explicarte mejor el valor.",
                "empathy_score": 5.0,
                "service_used": "emergency_fallback",
                "error": str(e)
            }
    
    async def monitor_conversation_empathy(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Monitor conversation for empathy-related alerts.
        
        Args:
            conversation_id: Conversation identifier
            messages: Conversation messages
            
        Returns:
            Monitoring results with alerts
        """
        try:
            if is_feature_enabled(EmpathyFeature.SENTIMENT_ALERTS):
                # Use consolidated service for monitoring
                alerts = self.consolidated_empathy.monitor_conversation_sentiment(
                    conversation_id, messages
                )
                
                return {
                    **alerts,
                    "service_used": "consolidated",
                    "monitoring_active": True
                }
            else:
                # Basic monitoring
                return {
                    "conversation_id": conversation_id,
                    "has_alerts": False,
                    "service_used": "legacy",
                    "monitoring_active": False,
                    "message": "Advanced monitoring disabled"
                }
                
        except Exception as e:
            logger.error(f"Error monitoring conversation empathy: {e}")
            return {
                "conversation_id": conversation_id,
                "has_alerts": False,
                "service_used": "error_fallback",
                "monitoring_active": False,
                "error": str(e)
            }
    
    async def get_empathy_performance_report(self) -> Dict[str, Any]:
        """Get empathy performance report."""
        try:
            # Get feature flags status
            flags_report = self._empathy_flags.get_feature_status_report()
            
            # Get consolidated service stats
            if self._consolidated_empathy:
                service_stats = await self._consolidated_empathy.get_service_stats()
            else:
                service_stats = {}
            
            return {
                "timestamp": datetime.now().isoformat(),
                "service_routing": {
                    "consolidated_enabled": use_consolidated_service(),
                    "fallback_count": self._empathy_fallback_count,
                    "performance_metrics": self._empathy_performance_metrics
                },
                "feature_flags": flags_report,
                "service_statistics": service_stats,
                "health_status": "healthy" if self._empathy_fallback_count < 5 else "degraded"
            }
            
        except Exception as e:
            logger.error(f"Error generating empathy performance report: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "health_status": "error"
            }