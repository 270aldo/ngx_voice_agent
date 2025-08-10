"""
Pre-processing pipeline stages for message analysis.
"""

import logging
from typing import Dict, Any, List, Optional

from .base import PipelineStage, Pipeline
from src.services.conversation.conversation_context import ConversationContext
from src.services.conversation.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)


class IntentAnalysisStage(PipelineStage):
    """Analyze user intent from the message."""
    
    def __init__(self, service_registry: ServiceRegistry):
        super().__init__("intent_analysis", service_registry)
    
    async def _process(self, context: ConversationContext) -> ConversationContext:
        """Analyze intent from the current message."""
        if not context.current_message:
            return context
        
        # Get intent analysis service
        intent_service = self.service_registry.get('enhanced_intent_analysis')
        if not intent_service:
            intent_service = self.service_registry.get('intent_analysis')
        
        if not intent_service:
            logger.warning("No intent analysis service available")
            return context
        
        try:
            # Analyze intent
            intent_result = await intent_service.analyze(
                context.current_message,
                context.get_message_history()
            )
            
            # Store results
            context.metadata.intent = intent_result.get('intent')
            context.metadata.intent_confidence = intent_result.get('confidence', 0.0)
            
            # Check for specific intents
            if intent_result.get('intent') == 'price_inquiry':
                context.metadata.is_price_objection = True
            
            # Cache result
            context.add_service_result('intent_analysis', intent_result)
            
            logger.info(f"Detected intent: {context.metadata.intent} (confidence: {context.metadata.intent_confidence:.2f})")
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
        
        return context


class EmotionDetectionStage(PipelineStage):
    """Detect emotional state and sentiment."""
    
    def __init__(self, service_registry: ServiceRegistry):
        super().__init__("emotion_detection", service_registry)
    
    async def _process(self, context: ConversationContext) -> ConversationContext:
        """Detect emotions and sentiment."""
        if not context.current_message:
            return context
        
        try:
            # Use empathy engine if available
            empathy_engine = self.service_registry.get('advanced_empathy_engine')
            if empathy_engine:
                emotion_result = await empathy_engine.analyze_emotional_state(
                    context.current_message,
                    context.get_message_history()
                )
                
                context.metadata.emotional_state = emotion_result.get('primary_emotion')
                context.metadata.sentiment_score = emotion_result.get('sentiment_score', 0.0)
                
                # Cache result
                context.add_service_result('emotion_analysis', emotion_result)
                
                logger.info(f"Detected emotion: {context.metadata.emotional_state} (sentiment: {context.metadata.sentiment_score:.2f})")
            
        except Exception as e:
            logger.error(f"Emotion detection failed: {e}")
        
        return context


class PredictiveAnalysisStage(PipelineStage):
    """Run ML predictive analysis on the conversation."""
    
    def __init__(self, service_registry: ServiceRegistry):
        super().__init__("predictive_analysis", service_registry)
    
    async def _process(self, context: ConversationContext) -> ConversationContext:
        """Run predictive ML models."""
        try:
            # Get decision engine
            decision_engine = self.service_registry.get('decision_engine')
            if not decision_engine:
                return context
            
            # Prepare customer profile
            customer_profile = {
                "conversation_id": context.conversation_id,
                "name": context.customer_name,
                "business_type": context.state.customer.business_type,
                "phase": context.current_phase,
                "message_count": len(context.messages)
            }
            
            # Get decision
            decision_result = await decision_engine.make_decision(
                context.get_message_history(),
                customer_profile
            )
            
            # Store predictions
            context.metadata.conversion_probability = decision_result.get('conversion_probability', 0.5)
            context.metadata.recommended_action = decision_result.get('action')
            context.metadata.decision_confidence = decision_result.get('confidence', 0.5)
            
            # Extract specific predictions
            predictions = decision_result.get('predictions', {})
            context.metadata.detected_objections = predictions.get('objections', [])
            context.metadata.detected_needs = predictions.get('needs', [])
            
            # Cache result
            context.add_service_result('decision_engine', decision_result)
            
            logger.info(
                f"ML Decision: {context.metadata.recommended_action} "
                f"(conversion: {context.metadata.conversion_probability:.2f})"
            )
            
        except Exception as e:
            logger.error(f"Predictive analysis failed: {e}")
        
        return context


class ContextEnrichmentStage(PipelineStage):
    """Enrich context with additional information."""
    
    def __init__(self, service_registry: ServiceRegistry):
        super().__init__("context_enrichment", service_registry)
    
    async def _process(self, context: ConversationContext) -> ConversationContext:
        """Add additional context information."""
        try:
            # Check if this is a greeting
            if len(context.messages) == 0 or context.current_phase == 'greeting':
                context.metadata.is_greeting = True
            
            # Check for human transfer conditions
            qualification_service = self.service_registry.get('qualification')
            if qualification_service:
                # Quick qualification check
                qual_result = await qualification_service.qualify_lead(
                    context.get_message_history(),
                    {
                        "name": context.customer_name,
                        "business_type": context.state.customer.business_type
                    }
                )
                
                lead_score = qual_result.get('score', 50)
                
                # Check transfer conditions
                human_transfer_service = self.service_registry.get('human_transfer')
                if human_transfer_service:
                    should_transfer = await human_transfer_service.should_transfer(
                        context.state,
                        lead_score
                    )
                    
                    context.metadata.requires_human_transfer = should_transfer
                    
                    if should_transfer:
                        logger.info("Human transfer recommended")
            
            # Run pattern recognition if available
            pattern_engine = self.service_registry.get('pattern_recognition')
            if pattern_engine and context.current_message:
                patterns = await pattern_engine.detect_patterns(
                    context.conversation_id,
                    context.current_message,
                    context.get_message_history()
                )
                
                context.add_service_result('detected_patterns', patterns)
                
        except Exception as e:
            logger.error(f"Context enrichment failed: {e}")
        
        return context


class PreProcessingPipeline(Pipeline):
    """Pre-processing pipeline for message analysis."""
    
    def __init__(self, service_registry: ServiceRegistry):
        """Initialize pre-processing pipeline with all stages."""
        stages = [
            IntentAnalysisStage(service_registry),
            EmotionDetectionStage(service_registry),
            PredictiveAnalysisStage(service_registry),
            ContextEnrichmentStage(service_registry)
        ]
        
        super().__init__("preprocessing", stages)