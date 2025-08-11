"""
A/B Testing Mixin for Conversation Orchestrator.

This mixin adds A/B testing capabilities to the conversation orchestrator,
enabling dynamic experimentation with different conversation strategies.
"""

import logging
from typing import Optional, Dict, Any

from .ab_testing_integration import ABTestingIntegration

logger = logging.getLogger(__name__)


class ABTestingMixin:
    """
    Mixin to add A/B testing capabilities to the conversation orchestrator.
    """
    
    def __init__(self):
        """Initialize A/B testing components."""
        self.ab_testing = ABTestingIntegration()
        self._ab_testing_initialized = False
    
    async def _init_ab_testing(self) -> None:
        """Initialize A/B testing services."""
        if self._ab_testing_initialized:
            return
        
        try:
            await self.ab_testing.initialize()
            self._ab_testing_initialized = True
            logger.info("A/B testing services initialized")
        except Exception as e:
            logger.error(f"Failed to initialize A/B testing: {e}")
            # Continue without A/B testing
            self.ab_testing = None
    
    async def _apply_greeting_ab_test(
        self,
        conversation_id: str,
        customer_data: Dict[str, Any],
        program_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Apply A/B testing to greeting generation.
        
        Args:
            conversation_id: Conversation identifier
            customer_data: Customer information
            program_type: Program type
            
        Returns:
            A/B test variant configuration or None
        """
        if not self.ab_testing:
            return None
        
        try:
            context = {
                "customer_age": customer_data.get("age"),
                "customer_segment": customer_data.get("segment", "general"),
                "program_type": program_type,
                "platform": customer_data.get("platform", "web")
            }
            
            variant = await self.ab_testing.get_greeting_variant(
                conversation_id=conversation_id,
                context=context
            )
            
            if variant:
                logger.debug(f"Applied greeting variant: {variant.get('variant_id')}")
            
            return variant
            
        except Exception as e:
            logger.error(f"Error applying greeting A/B test: {e}")
            return None
    
    async def _apply_price_objection_ab_test(
        self,
        conversation_id: str,
        objection_text: str,
        tier_detected: str,
        emotional_state: str
    ) -> Optional[Dict[str, Any]]:
        """
        Apply A/B testing to price objection handling.
        
        Args:
            conversation_id: Conversation identifier
            objection_text: The price objection text
            tier_detected: Detected pricing tier
            emotional_state: Current emotional state
            
        Returns:
            A/B test variant configuration or None
        """
        if not self.ab_testing:
            return None
        
        try:
            context = {
                "objection_text": objection_text,
                "tier_detected": tier_detected,
                "emotional_state": emotional_state,
                "objection_strength": self._assess_objection_strength(objection_text)
            }
            
            variant = await self.ab_testing.get_price_objection_variant(
                conversation_id=conversation_id,
                context=context
            )
            
            if variant:
                logger.debug(f"Applied price objection variant: {variant.get('variant_id')}")
            
            return variant
            
        except Exception as e:
            logger.error(f"Error applying price objection A/B test: {e}")
            return None
    
    async def _apply_closing_ab_test(
        self,
        conversation_id: str,
        conversation_state: Any,
        readiness_score: float
    ) -> Optional[Dict[str, Any]]:
        """
        Apply A/B testing to closing technique.
        
        Args:
            conversation_id: Conversation identifier
            conversation_state: Current conversation state
            readiness_score: Customer readiness score (0-1)
            
        Returns:
            A/B test variant configuration or None
        """
        if not self.ab_testing:
            return None
        
        try:
            context = {
                "phase": conversation_state.phase,
                "message_count": len(conversation_state.messages),
                "readiness_score": readiness_score,
                "tier_selected": conversation_state.context.get("tier_selected"),
                "objections_overcome": conversation_state.context.get("objections_overcome", 0)
            }
            
            variant = await self.ab_testing.get_closing_variant(
                conversation_id=conversation_id,
                context=context
            )
            
            if variant:
                logger.debug(f"Applied closing variant: {variant.get('variant_id')}")
            
            return variant
            
        except Exception as e:
            logger.error(f"Error applying closing A/B test: {e}")
            return None
    
    async def _apply_empathy_ab_test(
        self,
        conversation_id: str,
        emotional_state: str,
        conversation_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Apply A/B testing to empathetic responses.
        
        Args:
            conversation_id: Conversation identifier
            emotional_state: Detected emotional state
            conversation_context: Current conversation context
            
        Returns:
            A/B test variant configuration or None
        """
        if not self.ab_testing:
            return None
        
        try:
            variant = await self.ab_testing.get_empathy_variant(
                conversation_id=conversation_id,
                emotional_state=emotional_state,
                context=conversation_context
            )
            
            if variant:
                logger.debug(f"Applied empathy variant: {variant.get('variant_id')}")
            
            return variant
            
        except Exception as e:
            logger.error(f"Error applying empathy A/B test: {e}")
            return None
    
    async def _record_ab_testing_outcome(
        self,
        conversation_id: str,
        outcome: str,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Record conversation outcome for A/B testing.
        
        Args:
            conversation_id: Conversation identifier
            outcome: Conversation outcome
            metrics: Performance metrics
        """
        if not self.ab_testing:
            return
        
        try:
            await self.ab_testing.record_conversation_outcome(
                conversation_id=conversation_id,
                outcome=outcome,
                metrics=metrics
            )
        except Exception as e:
            logger.error(f"Error recording A/B testing outcome: {e}")
    
    def _enhance_response_with_ab_variant(
        self,
        response: str,
        variant_config: Optional[Dict[str, Any]]
    ) -> str:
        """
        Enhance response based on A/B test variant.
        
        Args:
            response: Original response
            variant_config: A/B test variant configuration
            
        Returns:
            Enhanced response
        """
        if not self.ab_testing or not variant_config:
            return response
        
        return self.ab_testing.enhance_response_with_variant(response, variant_config)
    
    def _assess_objection_strength(self, objection_text: str) -> str:
        """
        Assess the strength of a price objection.
        
        Args:
            objection_text: The objection text
            
        Returns:
            Objection strength: 'low', 'medium', or 'high'
        """
        strong_indicators = ["muy caro", "demasiado", "no puedo pagar", "imposible", "fuera de mi alcance"]
        medium_indicators = ["caro", "mucho dinero", "costoso", "elevado"]
        
        text_lower = objection_text.lower()
        
        for indicator in strong_indicators:
            if indicator in text_lower:
                return "high"
        
        for indicator in medium_indicators:
            if indicator in text_lower:
                return "medium"
        
        return "low"