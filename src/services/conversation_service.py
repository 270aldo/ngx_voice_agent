"""
Conversation Service - Intelligent Orchestrator Selector

This file provides a smart wrapper that can switch between the legacy
and refactored orchestrator implementations based on feature flags,
ensuring zero downtime deployment and easy rollback capabilities.
"""

import logging
from typing import Optional, Dict, Any

from src.models.conversation import ConversationState, CustomerData
from src.models.platform_context import PlatformContext, PlatformInfo
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Intelligent orchestrator selector with feature flag support.
    
    This class dynamically selects between legacy and refactored orchestrator
    implementations based on the USE_REFACTORED_ORCHESTRATOR feature flag,
    ensuring safe deployment and easy rollback capabilities.
    """
    
    def __init__(self, industry: str = 'salud', platform_context: Optional[PlatformContext] = None):
        """
        Initialize conversation service with intelligent orchestrator selection.
        
        Args:
            industry: Industry for customization
            platform_context: Platform context (optional)
        """
        self.settings = get_settings()
        self.industry = industry
        self.platform_context = platform_context
        
        # Dynamically import and initialize the appropriate orchestrator
        self._orchestrator = self._create_orchestrator()
        
        logger.info(f"ConversationService initialized with {'refactored' if self.settings.use_refactored_orchestrator else 'legacy'} orchestrator")
        
        # Expose orchestrator properties for backward compatibility
        self._sync_properties_with_orchestrator()
    
    def _create_orchestrator(self):
        """
        Create the appropriate orchestrator based on feature flag.
        
        Returns:
            Either legacy or refactored orchestrator instance
        """
        try:
            if self.settings.use_refactored_orchestrator:
                # Import and use refactored orchestrator
                from src.services.conversation.orchestrator_refactored import ConversationOrchestratorFacade
                logger.info("Using refactored ConversationOrchestratorFacade")
                return ConversationOrchestratorFacade(self.industry, self.platform_context)
            else:
                # Import and use legacy orchestrator
                from src.services.conversation.orchestrator import ConversationOrchestrator
                logger.info("Using legacy ConversationOrchestrator")
                return ConversationOrchestrator(self.industry, self.platform_context)
        except Exception as e:
            logger.error(f"Failed to create orchestrator: {e}")
            # Fallback to legacy orchestrator on any import/creation error
            logger.warning("Falling back to legacy orchestrator due to error")
            from src.services.conversation.orchestrator import ConversationOrchestrator
            return ConversationOrchestrator(self.industry, self.platform_context)
    
    def _sync_properties_with_orchestrator(self):
        """Sync properties with the underlying orchestrator for backward compatibility."""
        # Update industry and platform context to match orchestrator
        if hasattr(self._orchestrator, 'industry'):
            self.industry = self._orchestrator.industry
        if hasattr(self._orchestrator, 'platform_context'):
            self.platform_context = self._orchestrator.platform_context
        
        # Handle different property names between legacy and refactored
        if hasattr(self._orchestrator, '_initialized'):
            self._initialized = self._orchestrator._initialized
        elif hasattr(self._orchestrator, 'initialized'):
            self._initialized = self._orchestrator.initialized
        else:
            self._initialized = False
            
        if hasattr(self._orchestrator, '_current_agent'):
            self._current_agent = self._orchestrator._current_agent
        else:
            self._current_agent = None
        
        # Expose services for backward compatibility (only for legacy orchestrator)
        self._expose_legacy_services()
    
    def _expose_legacy_services(self):
        """Expose legacy services for backward compatibility."""
        legacy_services = [
            'intent_analysis_service', 'enhanced_intent_service', 'qualification_service',
            'human_transfer_service', 'follow_up_service', 'personalization_service',
            'multi_voice_service', 'program_router'
        ]
        
        for service_name in legacy_services:
            if hasattr(self._orchestrator, service_name):
                setattr(self, service_name, getattr(self._orchestrator, service_name))
            else:
                # Set to None if service doesn't exist in refactored version
                setattr(self, service_name, None)
    
    async def initialize(self) -> None:
        """Initialize the service."""
        await self._orchestrator.initialize()
        self._sync_properties_with_orchestrator()
    
    async def _ensure_initialized(self) -> None:
        """Ensure service is initialized."""
        if hasattr(self._orchestrator, '_ensure_initialized'):
            await self._orchestrator._ensure_initialized()
        else:
            # For refactored orchestrator, use standard initialize
            await self._orchestrator.initialize()
        self._sync_properties_with_orchestrator()
    
    async def start_conversation(
        self, 
        customer_data: CustomerData, 
        program_type: Optional[str] = None,
        platform_info: Optional[PlatformInfo] = None
    ) -> ConversationState:
        """Start a new conversation (delegates to orchestrator with compatibility layer)."""
        if self.settings.use_refactored_orchestrator:
            # Refactored orchestrator expects platform_context instead of platform_info
            platform_context = self.platform_context
            if platform_info:
                # Convert PlatformInfo to PlatformContext if needed
                platform_context = self._convert_platform_info_to_context(platform_info)
            
            return await self._orchestrator.start_conversation(
                customer_data, platform_context
            )
        else:
            # Legacy orchestrator signature
            return await self._orchestrator.start_conversation(
                customer_data, program_type, platform_info
            )
    
    def _convert_platform_info_to_context(self, platform_info: PlatformInfo) -> PlatformContext:
        """Convert PlatformInfo to PlatformContext for compatibility."""
        # This is a simple adapter - you may need to adjust based on actual structure
        if not platform_info:
            return self.platform_context
        
        # Create PlatformContext from PlatformInfo if needed
        # (This may need adjustment based on actual class definitions)
        return PlatformContext(
            platform_type=getattr(platform_info, 'platform_type', 'web'),
            **platform_info.__dict__ if hasattr(platform_info, '__dict__') else {}
        )
    
    async def process_message(
        self,
        conversation_id: str,
        message_text: str,
        audio_data: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """Process a message (delegates to orchestrator with compatibility layer)."""
        if self.settings.use_refactored_orchestrator:
            # Refactored orchestrator has different signature
            voice_enabled = audio_data is not None
            return await self._orchestrator.process_message(
                conversation_id, message_text, voice_enabled
            )
        else:
            # Legacy orchestrator signature
            return await self._orchestrator.process_message(
                conversation_id, message_text, audio_data
            )
    
    async def end_conversation(
        self, 
        conversation_id: str, 
        end_reason: str = "completed"
    ) -> ConversationState:
        """End a conversation (delegates to orchestrator with compatibility layer)."""
        if self.settings.use_refactored_orchestrator:
            # Refactored orchestrator uses 'reason' parameter name
            result = await self._orchestrator.end_conversation(conversation_id, reason=end_reason)
            # Return format might be different, handle conversion if needed
            if isinstance(result, dict) and result.get('success'):
                # Convert dict result to ConversationState if needed
                # This might need adjustment based on actual return formats
                return result
            return result
        else:
            # Legacy orchestrator signature
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