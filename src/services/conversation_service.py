"""
Conversation Service - Refactored Entry Point

This file maintains backward compatibility while delegating to the new
modular conversation orchestrator.
"""

import logging
from typing import Optional, Dict, Any

from src.models.conversation import ConversationState, CustomerData
from src.models.platform_context import PlatformContext, PlatformInfo
from src.services.conversation import ConversationOrchestrator

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Backward-compatible wrapper for the refactored ConversationOrchestrator.
    
    This class maintains the same interface as the original ConversationService
    while delegating all functionality to the new modular system.
    """
    
    def __init__(self, industry: str = 'salud', platform_context: Optional[PlatformContext] = None):
        """
        Initialize conversation service with backward compatibility.
        
        Args:
            industry: Industry for customization
            platform_context: Platform context (optional)
        """
        self._orchestrator = ConversationOrchestrator(industry, platform_context)
        
        # Expose orchestrator properties for backward compatibility
        self.industry = self._orchestrator.industry
        self.platform_context = self._orchestrator.platform_context
        self._initialized = self._orchestrator._initialized
        self._current_agent = self._orchestrator._current_agent
        
        # Expose services for backward compatibility
        self.intent_analysis_service = self._orchestrator.intent_analysis_service
        self.enhanced_intent_service = self._orchestrator.enhanced_intent_service
        self.qualification_service = self._orchestrator.qualification_service
        self.human_transfer_service = self._orchestrator.human_transfer_service
        self.follow_up_service = self._orchestrator.follow_up_service
        self.personalization_service = self._orchestrator.personalization_service
        self.multi_voice_service = self._orchestrator.multi_voice_service
        self.program_router = self._orchestrator.program_router
        
        logger.info("ConversationService initialized with refactored orchestrator")
    
    async def initialize(self) -> None:
        """Initialize the service."""
        await self._orchestrator.initialize()
        self._initialized = self._orchestrator._initialized
    
    async def _ensure_initialized(self) -> None:
        """Ensure service is initialized."""
        await self._orchestrator._ensure_initialized()
        self._initialized = self._orchestrator._initialized
    
    async def start_conversation(
        self, 
        customer_data: CustomerData, 
        program_type: Optional[str] = None,
        platform_info: Optional[PlatformInfo] = None
    ) -> ConversationState:
        """Start a new conversation (delegates to orchestrator)."""
        return await self._orchestrator.start_conversation(
            customer_data, program_type, platform_info
        )
    
    async def process_message(
        self,
        conversation_id: str,
        message_text: str,
        audio_data: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """Process a message (delegates to orchestrator)."""
        return await self._orchestrator.process_message(
            conversation_id, message_text, audio_data
        )
    
    async def end_conversation(
        self, 
        conversation_id: str, 
        end_reason: str = "completed"
    ) -> ConversationState:
        """End a conversation (delegates to orchestrator)."""
        return await self._orchestrator.end_conversation(conversation_id, end_reason)
    
    def set_platform_context(self, platform_context: PlatformContext) -> None:
        """Set platform context."""
        self._orchestrator.set_platform_context(platform_context)
        self.platform_context = platform_context
    
    def get_platform_context(self) -> Optional[PlatformContext]:
        """Get platform context."""
        return self._orchestrator.get_platform_context()
    
    # Delegate all ML tracking methods
    async def _start_ml_conversation_tracking(self, *args, **kwargs):
        """Delegate ML tracking start."""
        return await self._orchestrator._start_ml_conversation_tracking(*args, **kwargs)
    
    async def _update_ml_conversation_metrics(self, *args, **kwargs):
        """Delegate ML metrics update."""
        return await self._orchestrator._update_ml_conversation_metrics(*args, **kwargs)
    
    async def _record_conversation_outcome_for_ml(self, *args, **kwargs):
        """Delegate ML outcome recording."""
        return await self._orchestrator._record_conversation_outcome_for_ml(*args, **kwargs)
    
    async def get_ml_conversation_summary(self, conversation_id: str):
        """Get ML conversation summary."""
        return await self._orchestrator.get_ml_conversation_summary(conversation_id)
    
    async def get_adaptive_learning_status(self):
        """Get adaptive learning status."""
        return await self._orchestrator.get_adaptive_learning_status()
    
    # Delegate tier management methods
    async def detect_tier_and_adjust_strategy(self, *args, **kwargs):
        """Delegate tier detection."""
        return await self._orchestrator.detect_tier_and_adjust_strategy(*args, **kwargs)
    
    async def handle_price_objection_with_tier_adjustment(self, *args, **kwargs):
        """Delegate price objection handling."""
        return await self._orchestrator.handle_price_objection_with_tier_adjustment(*args, **kwargs)
    
    async def suggest_upsell_opportunity(self, *args, **kwargs):
        """Delegate upsell suggestions."""
        return await self._orchestrator.suggest_upsell_opportunity(*args, **kwargs)
    
    # Delegate emotional processing methods
    async def _analyze_emotional_state(self, *args, **kwargs):
        """Delegate emotional analysis."""
        return await self._orchestrator._analyze_emotional_state(*args, **kwargs)
    
    async def _analyze_personality(self, *args, **kwargs):
        """Delegate personality analysis."""
        return await self._orchestrator._analyze_personality(*args, **kwargs)
    
    async def _generate_empathic_response(self, *args, **kwargs):
        """Delegate empathic response generation."""
        return await self._orchestrator._generate_empathic_response(*args, **kwargs)
    
    # Delegate sales strategy methods
    async def _calculate_personalized_roi(self, *args, **kwargs):
        """Delegate ROI calculation."""
        return await self._orchestrator._calculate_personalized_roi(*args, **kwargs)
    
    def _get_program_specific_benefits(self, *args, **kwargs):
        """Delegate program benefits."""
        return self._orchestrator._get_program_specific_benefits(*args, **kwargs)
    
    def _generate_urgency_factors(self, *args, **kwargs):
        """Delegate urgency factors."""
        return self._orchestrator._generate_urgency_factors(*args, **kwargs)
    
    def _get_relevant_social_proof(self, *args, **kwargs):
        """Delegate social proof."""
        return self._orchestrator._get_relevant_social_proof(*args, **kwargs)
    
    def _build_hie_sales_context(self, *args, **kwargs):
        """Delegate HIE sales context."""
        return self._orchestrator._build_hie_sales_context(*args, **kwargs)
    
    # Delegate base service methods
    async def _get_conversation_state(self, conversation_id: str):
        """Get conversation state."""
        return await self._orchestrator._get_conversation_state(conversation_id)
    
    async def _save_conversation_state(self, state: ConversationState):
        """Save conversation state."""
        return await self._orchestrator._save_conversation_state(state)
    
    async def _restore_agent_from_state(self, state: ConversationState):
        """Restore agent from state."""
        result = await self._orchestrator._restore_agent_from_state(state)
        # Update current agent reference
        self._current_agent = self._orchestrator._current_agent
        return result
    
    def _generate_greeting(self, customer_data: CustomerData, program_type: str) -> str:
        """Generate greeting."""
        return self._orchestrator._generate_greeting(customer_data, program_type)
    
    async def _should_continue_conversation(self, state: ConversationState) -> bool:
        """Check if conversation should continue."""
        return await self._orchestrator._should_continue_conversation(state)
    
    # Additional backward compatibility methods can be added here as needed
    def __getattr__(self, name):
        """
        Fallback for any missing methods - delegate to orchestrator.
        This ensures full backward compatibility.
        """
        if hasattr(self._orchestrator, name):
            attr = getattr(self._orchestrator, name)
            # If it's a method, wrap it to maintain self reference
            if callable(attr):
                def wrapper(*args, **kwargs):
                    return attr(*args, **kwargs)
                return wrapper
            else:
                return attr
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


# Export the refactored service
__all__ = ['ConversationService']