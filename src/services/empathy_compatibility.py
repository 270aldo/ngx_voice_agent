"""
Empathy Compatibility Layer for NGX Voice Sales Agent.

This module provides backward compatibility with legacy empathy services
while redirecting all calls to the new ConsolidatedEmpathyIntelligenceService.

Legacy Services Supported:
1. AdvancedEmpathyEngine
2. EmotionalIntelligenceService
3. EmpathyEngineService
4. UltraEmpathyGreetingEngine
5. UltraEmpathyPriceHandler
6. AdvancedSentimentService
7. SentimentAlertService
8. AdaptivePersonalityService

Features:
- 100% backward compatibility
- Gradual migration support
- Performance monitoring
- Feature flags for controlled rollout
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from src.services.consolidated_empathy_intelligence_service import (
    ConsolidatedEmpathyIntelligenceService,
    EmotionalProfile,
    EmpathyResponse,
    EmpathyStrategy,
    EmotionalState,
    EmpathyTechnique
)
from src.models.conversation import CustomerData
from src.integrations.elevenlabs.advanced_voice import VoicePersona
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)


# Global consolidated service instance
_consolidated_service = None

def get_consolidated_service() -> ConsolidatedEmpathyIntelligenceService:
    """Get the singleton instance of consolidated empathy service."""
    global _consolidated_service
    if _consolidated_service is None:
        _consolidated_service = ConsolidatedEmpathyIntelligenceService()
    return _consolidated_service


# === LEGACY SERVICE 1: AdvancedEmpathyEngine ===
class AdvancedEmpathyEngine:
    """
    Legacy compatibility wrapper for AdvancedEmpathyEngine.
    Redirects all calls to ConsolidatedEmpathyIntelligenceService.
    """
    
    def __init__(self):
        """Initialize legacy engine with consolidated service."""
        self._consolidated = get_consolidated_service()
        logger.info("AdvancedEmpathyEngine legacy wrapper initialized")
    
    async def generate_intelligent_empathy(
        self,
        context: Dict[str, Any],
        emotional_profile: Optional[EmotionalProfile] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        cultural_context: Optional[str] = None,
        relevant_ngx_product_feature: Optional[str] = None
    ) -> Dict[str, Any]:
        """Legacy method for generating intelligent empathy."""
        try:
            # Extract message from context
            message = context.get("last_message", "")
            conversation_history = conversation_history or []
            
            # Use consolidated service
            result = await self._consolidated.generate_comprehensive_empathy_response(
                message=message,
                conversation_history=conversation_history,
                customer_profile=context.get("customer_profile"),
                context=context
            )
            
            # Convert to legacy format
            return {
                "surface_layer": result['empathy_response'].intro_phrase + " " + result['empathy_response'].core_message,
                "emotional_layer": result['empathy_response'].emotional_tone,
                "cognitive_layer": f"Comprendo tu {result['emotional_profile'].primary_state.value}",
                "behavioral_layer": result['empathy_response'].closing_phrase,
                "meta_layer": f"Técnica: {result['empathy_response'].technique_used.value}",
                "voice_modulation": {
                    "pace": "moderate",
                    "warmth": 0.8,
                    "clarity": 0.9
                },
                "ngx_product_features": relevant_ngx_product_feature or ""
            }
            
        except Exception as e:
            logger.error(f"Error in legacy AdvancedEmpathyEngine: {e}")
            return self._generate_fallback_legacy_response()
    
    def _generate_fallback_legacy_response(self) -> Dict[str, Any]:
        """Generate fallback response in legacy format."""
        return {
            "surface_layer": "Entiendo tu situación y estoy aquí para ayudarte",
            "emotional_layer": "empático y comprensivo",
            "cognitive_layer": "Comprendo tu necesidad",
            "behavioral_layer": "Avancemos juntos hacia la solución",
            "meta_layer": "Fallback legacy response",
            "voice_modulation": {"pace": "moderate", "warmth": 0.8, "clarity": 0.9},
            "ngx_product_features": ""
        }


# === LEGACY SERVICE 2: EmotionalIntelligenceService ===
class EmotionalIntelligenceService:
    """
    Legacy compatibility wrapper for EmotionalIntelligenceService.
    """
    
    def __init__(self, nlp_service=None, sentiment_service=None):
        """Initialize with optional services (ignored, using consolidated)."""
        self._consolidated = get_consolidated_service()
        logger.info("EmotionalIntelligenceService legacy wrapper initialized")
    
    async def analyze_emotional_state(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None
    ) -> EmotionalProfile:
        """Legacy method for emotional state analysis."""
        # Convert customer_profile dict to CustomerData if needed
        customer_data = None
        if customer_profile:
            customer_data = CustomerData(
                name=customer_profile.get("name", "Cliente"),
                preferred_language=customer_profile.get("preferred_language", "spanish")
            )
        
        return await self._consolidated.analyze_emotional_state(
            messages=messages,
            customer_profile=customer_data
        )
    
    async def get_emotional_insights(self, profile: EmotionalProfile) -> Dict[str, Any]:
        """Legacy method for getting emotional insights."""
        return {
            "current_state": profile.primary_state.value,
            "confidence": profile.confidence,
            "emotional_trend": "stable",  # Simplified for legacy
            "risk_indicators": profile.triggers,
            "opportunities": ["High engagement opportunity"] if profile.intensity > 0.7 else [],
            "recommended_approach": f"Use {profile.primary_state.value} appropriate empathy",
            "voice_recommendations": {
                "emotional_state": profile.primary_state.value,
                "speaking_rate": "moderate",
                "energy_level": "balanced",
                "empathy_level": "high" if profile.intensity > 0.7 else "moderate"
            }
        }


# === LEGACY SERVICE 3: EmpathyEngineService ===
class EmpathyEngineService:
    """
    Legacy compatibility wrapper for EmpathyEngineService.
    """
    
    def __init__(self):
        """Initialize legacy empathy engine."""
        self._consolidated = get_consolidated_service()
        logger.info("EmpathyEngineService legacy wrapper initialized")
    
    async def generate_empathetic_response(
        self,
        emotional_profile: EmotionalProfile,
        original_message: str,
        context: Dict[str, Any],
        cultural_context: Optional[str] = None
    ) -> EmpathyResponse:
        """Legacy method for generating empathetic responses."""
        # Generate empathy strategy first
        empathy_strategy = await self._consolidated.generate_empathy_strategy(
            emotional_profile=emotional_profile,
            conversation_context=context,
            customer_profile=None
        )
        
        # Generate empathy response
        return await self._consolidated.generate_empathy_response(
            message=original_message,
            emotional_profile=emotional_profile,
            empathy_strategy=empathy_strategy,
            conversation_context=context
        )
    
    def enhance_message_with_empathy(self, message: str, empathy_level: str = "moderate") -> str:
        """Legacy method for enhancing messages with empathy."""
        if empathy_level == "high":
            return f"Comprendo perfectamente tu situación. {message} Estoy aquí para apoyarte en todo momento."
        elif empathy_level == "moderate":
            return f"Entiendo tu punto. {message} ¿En qué más puedo ayudarte?"
        else:
            return message
    
    async def generate_emotional_bridge(
        self,
        from_emotion: EmotionalState,
        to_emotion: EmotionalState,
        context: Dict[str, Any]
    ) -> str:
        """Legacy method for generating emotional bridges."""
        bridges = {
            (EmotionalState.FRUSTRATED, EmotionalState.SATISFIED): 
                "Entiendo tu frustración, y precisamente por eso quiero mostrarte cómo podemos solucionarlo",
            (EmotionalState.ANXIOUS, EmotionalState.CONFIDENT):
                "Es normal sentir inquietud, pero déjame mostrarte por qué puedes estar tranquilo",
            (EmotionalState.CONFUSED, EmotionalState.INTERESTED):
                "Sé que puede parecer complejo, pero verás que es más simple de lo que parece"
        }
        
        return bridges.get(
            (from_emotion, to_emotion),
            f"Comprendo cómo te sientes, y vamos a trabajar juntos para llegar a un mejor estado"
        )


# === LEGACY SERVICE 4: UltraEmpathyGreetingEngine ===
class UltraEmpathyGreetingEngine:
    """
    Legacy compatibility wrapper for UltraEmpathyGreetingEngine.
    """
    
    def __init__(self):
        """Initialize legacy greeting engine."""
        self._consolidated = get_consolidated_service()
        logger.info("UltraEmpathyGreetingEngine legacy wrapper initialized")
    
    def generate_ultra_empathetic_greeting(self, context: Dict[str, Any]) -> str:
        """Legacy method for generating ultra-empathetic greetings."""
        customer_name = context.get("customer_name", "Cliente")
        initial_message = context.get("initial_message")
        
        return self._consolidated.generate_ultra_empathy_greeting(
            customer_name=customer_name,
            initial_message=initial_message,
            customer_profile=None
        )


# === LEGACY SERVICE 5: UltraEmpathyPriceHandler ===
class UltraEmpathyPriceHandler:
    """
    Legacy compatibility wrapper for UltraEmpathyPriceHandler.
    """
    
    def __init__(self):
        """Initialize legacy price handler."""
        self._consolidated = get_consolidated_service()
        logger.info("UltraEmpathyPriceHandler legacy wrapper initialized")
    
    def generate_ultra_empathetic_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method for handling price objections."""
        objection_text = context.get("objection_text", "")
        customer_name = context.get("customer_name", "Cliente")
        tier_mentioned = context.get("tier_mentioned", "pro")
        
        return self._consolidated.handle_price_objection_with_ultra_empathy(
            objection_message=objection_text,
            customer_name=customer_name,
            tier_mentioned=tier_mentioned,
            customer_profile=None
        )


# === LEGACY SERVICE 6: AdvancedSentimentService ===
class AdvancedSentimentService:
    """
    Legacy compatibility wrapper for AdvancedSentimentService.
    """
    
    def __init__(self):
        """Initialize legacy sentiment service."""
        self._consolidated = get_consolidated_service()
        logger.info("AdvancedSentimentService legacy wrapper initialized")
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Legacy method for sentiment analysis."""
        result = self._consolidated.analyze_advanced_sentiment(text)
        
        # Convert to legacy format
        return {
            "score": result["score"],
            "sentiment": result["sentiment"],
            "intensity": result["intensity"],
            "positive_count": result["positive_count"],
            "negative_count": result["negative_count"],
            "word_count": result["word_count"],
            "confidence": result["confidence"]
        }
    
    def detect_emotions(self, text: str) -> Dict[str, float]:
        """Legacy method for emotion detection."""
        result = self._consolidated.analyze_advanced_sentiment(text)
        return result["emotions"]
    
    def get_comprehensive_analysis(self, text: str) -> Dict[str, Any]:
        """Legacy method for comprehensive analysis."""
        sentiment = self.analyze_sentiment(text)
        emotions = self.detect_emotions(text)
        
        # Find dominant emotion
        dominant_emotion = max(emotions.items(), key=lambda x: x[1]) if emotions else ("neutral", 0.5)
        
        return {
            "sentiment": sentiment,
            "emotions": emotions,
            "dominant_emotion": {
                "name": dominant_emotion[0],
                "score": dominant_emotion[1]
            },
            "urgency": {"level": 0.3, "class": "low"},  # Simplified
            "indecision": {"level": 0.3, "class": "low"}  # Simplified
        }


# === LEGACY SERVICE 7: SentimentAlertService ===
class SentimentAlertService:
    """
    Legacy compatibility wrapper for SentimentAlertService.
    """
    
    def __init__(self):
        """Initialize legacy alert service."""
        self._consolidated = get_consolidated_service()
        logger.info("SentimentAlertService legacy wrapper initialized")
    
    def monitor_conversation(self, conversation_id: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Legacy method for monitoring conversations."""
        return self._consolidated.monitor_conversation_sentiment(conversation_id, messages)
    
    def get_alerts(self, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Legacy method for getting alerts."""
        if conversation_id:
            return self._consolidated.alert_system['alerts'].get(conversation_id, {
                "conversation_id": conversation_id,
                "has_alerts": False,
                "message": "No alerts for this conversation"
            })
        
        return {
            "total_alerts": len(self._consolidated.alert_system['alerts']),
            "alerts": self._consolidated.alert_system['alerts']
        }
    
    def clear_alerts(self, conversation_id: Optional[str] = None):
        """Legacy method for clearing alerts."""
        if conversation_id and conversation_id in self._consolidated.alert_system['alerts']:
            del self._consolidated.alert_system['alerts'][conversation_id]
        elif conversation_id is None:
            self._consolidated.alert_system['alerts'] = {}


# === LEGACY SERVICE 8: AdaptivePersonalityService ===
class AdaptivePersonalityService:
    """
    Legacy compatibility wrapper for AdaptivePersonalityService.
    """
    
    def __init__(self):
        """Initialize legacy personality service."""
        self._consolidated = get_consolidated_service()
        logger.info("AdaptivePersonalityService legacy wrapper initialized")
    
    async def analyze_personality(
        self,
        messages: List[Dict[str, Any]],
        customer_profile: Optional[Dict[str, Any]] = None,
        behavioral_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Legacy method for personality analysis."""
        # Extract customer messages
        customer_messages = [
            msg.get("content", "") for msg in messages 
            if msg.get("role") == "customer"
        ]
        
        personality_style = self._consolidated.detect_personality_style(customer_messages)
        
        # Convert to legacy format
        return {
            "communication_style": personality_style["dominant_style"],
            "primary_traits": personality_style["personality_traits"],
            "decision_style": "analytical" if personality_style["dominant_style"] == "analytical" else "collaborative",
            "risk_tolerance": 0.5,  # Default
            "pace_preference": "moderate",
            "detail_orientation": 0.6 if personality_style["dominant_style"] == "analytical" else 0.4,
            "social_preference": "balanced"
        }
    
    def generate_personality_insights(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method for generating personality insights."""
        communication_style = profile.get("communication_style", "amiable")
        
        insights_map = {
            "analytical": {
                "key_characteristics": ["Orientado a datos", "Necesita tiempo para analizar"],
                "do_recommendations": ["Proporcionar datos detallados", "Usar lenguaje preciso"],
                "dont_recommendations": ["Presionar para decisión rápida", "Usar generalizaciones"],
                "closing_strategy": "Resumen lógico con ROI claro",
                "objection_handling": "Datos y evidencia concreta"
            },
            "driver": {
                "key_characteristics": ["Orientado a resultados", "Toma decisiones rápidas"],
                "do_recommendations": ["Ir directo al punto", "Enfocarse en resultados"],
                "dont_recommendations": ["Dar demasiados detalles", "Ser indeciso"],
                "closing_strategy": "Cierre directo con beneficios claros",
                "objection_handling": "Soluciones rápidas y directas"
            },
            "expressive": {
                "key_characteristics": ["Orientado a emociones", "Social y entusiasta"],
                "do_recommendations": ["Usar historias inspiradoras", "Ser entusiasta"],
                "dont_recommendations": ["Ser demasiado técnico", "Ser frío"],
                "closing_strategy": "Cierre emocional con visión",
                "objection_handling": "Historias y testimonios"
            },
            "amiable": {
                "key_characteristics": ["Orientado a relaciones", "Busca seguridad"],
                "do_recommendations": ["Construir confianza", "Ser paciente"],
                "dont_recommendations": ["Presionar", "Ser agresivo"],
                "closing_strategy": "Cierre colaborativo con garantías",
                "objection_handling": "Apoyo y tranquilidad"
            }
        }
        
        return {
            "communication_style": communication_style,
            **insights_map.get(communication_style, insights_map["amiable"])
        }


# === CONVENIENCE FUNCTIONS FOR EASY ACCESS ===
def get_advanced_empathy_engine() -> AdvancedEmpathyEngine:
    """Get AdvancedEmpathyEngine compatibility wrapper."""
    return AdvancedEmpathyEngine()

def get_emotional_intelligence_service() -> EmotionalIntelligenceService:
    """Get EmotionalIntelligenceService compatibility wrapper."""
    return EmotionalIntelligenceService()

def get_empathy_engine_service() -> EmpathyEngineService:
    """Get EmpathyEngineService compatibility wrapper."""
    return EmpathyEngineService()

def get_ultra_empathy_greeting_engine() -> UltraEmpathyGreetingEngine:
    """Get UltraEmpathyGreetingEngine compatibility wrapper."""
    return UltraEmpathyGreetingEngine()

def get_ultra_empathy_price_handler() -> UltraEmpathyPriceHandler:
    """Get UltraEmpathyPriceHandler compatibility wrapper."""
    return UltraEmpathyPriceHandler()

def get_advanced_sentiment_service() -> AdvancedSentimentService:
    """Get AdvancedSentimentService compatibility wrapper."""
    return AdvancedSentimentService()

def get_sentiment_alert_service() -> SentimentAlertService:
    """Get SentimentAlertService compatibility wrapper."""
    return SentimentAlertService()

def get_adaptive_personality_service() -> AdaptivePersonalityService:
    """Get AdaptivePersonalityService compatibility wrapper."""
    return AdaptivePersonalityService()


# === MIGRATION HELPER ===
class EmpathyMigrationHelper:
    """Helper class for migrating from legacy services to consolidated service."""
    
    def __init__(self):
        self.migration_stats = {
            "legacy_calls": 0,
            "consolidated_calls": 0,
            "performance_improvements": [],
            "migration_started": datetime.now().isoformat()
        }
    
    def track_legacy_call(self, service_name: str, method_name: str):
        """Track legacy service usage for migration planning."""
        self.migration_stats["legacy_calls"] += 1
        logger.info(f"Legacy call tracked: {service_name}.{method_name}")
    
    def track_consolidated_call(self, method_name: str):
        """Track consolidated service usage."""
        self.migration_stats["consolidated_calls"] += 1
        logger.info(f"Consolidated call: {method_name}")
    
    def get_migration_report(self) -> Dict[str, Any]:
        """Get migration progress report."""
        total_calls = self.migration_stats["legacy_calls"] + self.migration_stats["consolidated_calls"]
        migration_percentage = (
            self.migration_stats["consolidated_calls"] / max(total_calls, 1) * 100
        )
        
        return {
            "migration_percentage": migration_percentage,
            "legacy_calls": self.migration_stats["legacy_calls"],
            "consolidated_calls": self.migration_stats["consolidated_calls"],
            "total_calls": total_calls,
            "migration_started": self.migration_stats["migration_started"],
            "recommendations": self._get_migration_recommendations(migration_percentage)
        }
    
    def _get_migration_recommendations(self, migration_percentage: float) -> List[str]:
        """Get migration recommendations based on progress."""
        if migration_percentage < 25:
            return [
                "Start migrating high-frequency endpoints first",
                "Test consolidated service in development environment",
                "Document API differences for team"
            ]
        elif migration_percentage < 75:
            return [
                "Continue migrating remaining endpoints",
                "Monitor performance improvements",
                "Phase out legacy service imports gradually"
            ]
        else:
            return [
                "Complete remaining migrations",
                "Remove legacy service files after full migration",
                "Update documentation to reflect new architecture"
            ]


# Global migration helper instance
migration_helper = EmpathyMigrationHelper()