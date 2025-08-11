"""
A/B Testing Integration Module for Conversation Orchestrator.

This module integrates A/B testing capabilities into the conversation flow,
enabling dynamic variant selection for greetings, objection handling,
closing techniques, and empathetic responses.
"""

import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from src.services.ab_testing_manager import (
    ABTestingManager, ExperimentCategory, VariantContent
)
from src.models.conversation import ConversationState

logger = logging.getLogger(__name__)


class ABTestingIntegration:
    """
    Integration layer between Conversation Orchestrator and A/B Testing Manager.
    
    This class provides methods to:
    - Apply A/B test variants during conversation
    - Track experiment outcomes
    - Enhance responses with variant content
    """
    
    def __init__(self):
        """Initialize A/B Testing Integration."""
        self.ab_manager = ABTestingManager()
        self.variant_cache: Dict[str, Dict[str, VariantContent]] = {}
        logger.info("ABTestingIntegration initialized")
    
    async def initialize(self) -> None:
        """Initialize the A/B Testing Manager."""
        await self.ab_manager.initialize()
    
    async def get_greeting_variant(
        self,
        conversation_id: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get A/B test variant for greeting.
        
        Args:
            conversation_id: Conversation identifier
            context: Conversation context
            
        Returns:
            Variant configuration or None
        """
        try:
            variant = await self.ab_manager.get_variant_for_conversation(
                conversation_id=conversation_id,
                category=ExperimentCategory.GREETING,
                context=context
            )
            
            if variant:
                # Cache the variant
                if conversation_id not in self.variant_cache:
                    self.variant_cache[conversation_id] = {}
                self.variant_cache[conversation_id]["greeting"] = variant
                
                # Return variant parameters for greeting generation
                return {
                    "style": variant.parameters.get("style", "consultive"),
                    "empathy_level": variant.parameters.get("empathy_level", "high"),
                    "personalization": variant.parameters.get("personalization", "medium"),
                    "variant_id": variant.variant_id,
                    "experiment_metadata": variant.metadata
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting greeting variant: {e}")
            return None
    
    async def get_price_objection_variant(
        self,
        conversation_id: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get A/B test variant for price objection handling.
        
        Args:
            conversation_id: Conversation identifier
            context: Conversation context with objection details
            
        Returns:
            Variant configuration or None
        """
        try:
            # Add phase to context for targeting
            enhanced_context = {
                **context,
                "phase": "pricing_discussion",
                "has_price_objection": True
            }
            
            variant = await self.ab_manager.get_variant_for_conversation(
                conversation_id=conversation_id,
                category=ExperimentCategory.PRICE_OBJECTION,
                context=enhanced_context
            )
            
            if variant:
                # Cache the variant
                if conversation_id not in self.variant_cache:
                    self.variant_cache[conversation_id] = {}
                self.variant_cache[conversation_id]["price_objection"] = variant
                
                # Return variant parameters for objection handling
                return {
                    "approach": variant.parameters.get("approach", "value_demonstration"),
                    "roi_calculation": variant.parameters.get("roi_calculation", False),
                    "payment_plans": variant.parameters.get("payment_plans", False),
                    "success_stories": variant.parameters.get("success_stories", False),
                    "variant_id": variant.variant_id,
                    "experiment_metadata": variant.metadata
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting price objection variant: {e}")
            return None
    
    async def get_closing_variant(
        self,
        conversation_id: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get A/B test variant for closing technique.
        
        Args:
            conversation_id: Conversation identifier
            context: Conversation context
            
        Returns:
            Variant configuration or None
        """
        try:
            # Add phase to context
            enhanced_context = {
                **context,
                "phase": "closing",
                "ready_to_close": True
            }
            
            variant = await self.ab_manager.get_variant_for_conversation(
                conversation_id=conversation_id,
                category=ExperimentCategory.CLOSING_TECHNIQUE,
                context=enhanced_context
            )
            
            if variant:
                # Cache the variant
                if conversation_id not in self.variant_cache:
                    self.variant_cache[conversation_id] = {}
                self.variant_cache[conversation_id]["closing"] = variant
                
                # Return variant parameters for closing
                return {
                    "style": variant.parameters.get("style", "consultive"),
                    "urgency": variant.parameters.get("urgency", "medium"),
                    "scarcity": variant.parameters.get("scarcity", None),
                    "next_steps": variant.parameters.get("next_steps", "clear"),
                    "variant_id": variant.variant_id,
                    "experiment_metadata": variant.metadata
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting closing variant: {e}")
            return None
    
    async def get_empathy_variant(
        self,
        conversation_id: str,
        emotional_state: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get A/B test variant for empathetic response.
        
        Args:
            conversation_id: Conversation identifier
            emotional_state: Detected emotional state
            context: Conversation context
            
        Returns:
            Variant configuration or None
        """
        try:
            # Add emotional context
            enhanced_context = {
                **context,
                "emotional_state": emotional_state,
                "requires_empathy": True
            }
            
            variant = await self.ab_manager.get_variant_for_conversation(
                conversation_id=conversation_id,
                category=ExperimentCategory.EMPATHY_RESPONSE,
                context=enhanced_context
            )
            
            if variant:
                # Cache the variant
                if conversation_id not in self.variant_cache:
                    self.variant_cache[conversation_id] = {}
                self.variant_cache[conversation_id]["empathy"] = variant
                
                # Return variant parameters for empathy
                return {
                    "style": variant.parameters.get("style", "reflective"),
                    "intensity": variant.parameters.get("intensity", "matched"),
                    "validation": variant.parameters.get("validation", "high"),
                    "action_oriented": variant.parameters.get("action_oriented", False),
                    "variant_id": variant.variant_id,
                    "experiment_metadata": variant.metadata
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting empathy variant: {e}")
            return None
    
    async def record_conversation_outcome(
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
        try:
            # Add variant information to metrics
            if conversation_id in self.variant_cache:
                metrics["ab_variants"] = {
                    category: {
                        "variant_id": variant.variant_id,
                        "experiment_name": variant.metadata.get("experiment_name")
                    }
                    for category, variant in self.variant_cache[conversation_id].items()
                }
            
            # Record outcome in A/B manager
            await self.ab_manager.record_outcome(
                conversation_id=conversation_id,
                outcome=outcome,
                metrics=metrics
            )
            
            # Clean up cache
            if conversation_id in self.variant_cache:
                del self.variant_cache[conversation_id]
            
            logger.debug(f"Recorded A/B testing outcome for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error recording A/B outcome: {e}")
    
    def enhance_response_with_variant(
        self,
        response: str,
        variant_config: Optional[Dict[str, Any]]
    ) -> str:
        """
        Enhance response based on A/B test variant configuration.
        
        Args:
            response: Original response
            variant_config: Variant configuration
            
        Returns:
            Enhanced response
        """
        if not variant_config:
            return response
        
        try:
            # Apply variant-specific enhancements
            style = variant_config.get("style")
            
            if style == "motivational":
                # Add motivational elements
                response = f"💪 {response}"
                if not response.endswith("!"):
                    response = response.rstrip(".") + "!"
            
            elif style == "urgent":
                # Add urgency elements
                urgency_phrases = [
                    "Es importante que sepas que",
                    "No queremos que pierdas esta oportunidad",
                    "Este es el momento perfecto para"
                ]
                import random
                urgency_phrase = random.choice(urgency_phrases)
                response = f"{urgency_phrase} {response.lower()}"
            
            elif style == "personal":
                # Make more personal
                response = response.replace("usted", "tú")
                response = response.replace("su", "tu")
            
            return response
            
        except Exception as e:
            logger.error(f"Error enhancing response with variant: {e}")
            return response
    
    async def get_active_experiments_summary(self) -> Dict[str, Any]:
        """
        Get summary of active A/B testing experiments.
        
        Returns:
            Summary of active experiments
        """
        try:
            summary = self.ab_manager.get_active_experiment_summary()
            results = await self.ab_manager.get_experiment_results()
            
            return {
                "active_experiments": summary,
                "performance": results.get("summary", {}),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting experiments summary: {e}")
            return {"error": str(e)}