"""
Conversation Orchestrator Facade

Facade pattern implementation that coordinates all refactored components
and provides backward compatibility with the original ConversationOrchestrator.
"""

import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from src.models.conversation import ConversationState, CustomerData, Message
from src.models.platform_context import PlatformContext

from .conversation_manager import ConversationManager
from .message_processor import MessageProcessor
from .integration_handler import IntegrationHandler
from .response_builder import ResponseBuilder
from .metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


class ConversationOrchestratorFacade:
    """
    Facade that coordinates all conversation components.
    
    This class provides a simplified interface to the refactored conversation
    system while maintaining backward compatibility with the original
    ConversationOrchestrator API.
    """
    
    def __init__(
        self,
        industry: str = 'salud',
        platform_context: Optional[PlatformContext] = None
    ):
        """
        Initialize the orchestrator facade.
        
        Args:
            industry: Industry context (default: 'salud'/health)
            platform_context: Platform-specific context
        """
        self.industry = industry
        self.platform_context = platform_context
        
        # Initialize all components
        self.conversation_manager = ConversationManager()
        self.message_processor = MessageProcessor()
        self.integration_handler = IntegrationHandler()
        self.response_builder = ResponseBuilder()
        self.metrics_collector = MetricsCollector()
        
        # State tracking
        self.initialized = False
        self.current_conversation_id = None
        
        logger.info(f"ConversationOrchestratorFacade initialized for industry: {industry}")
    
    async def initialize(self) -> None:
        """Initialize all components and services."""
        if self.initialized:
            return
        
        try:
            # Perform any async initialization needed
            logger.info("Initializing ConversationOrchestratorFacade components...")
            
            # Check service health
            health = await self.integration_handler.health_check()
            logger.info(f"Service health check: {health}")
            
            self.initialized = True
            logger.info("ConversationOrchestratorFacade initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize ConversationOrchestratorFacade: {e}")
            raise
    
    async def start_conversation(
        self,
        customer_data: CustomerData,
        platform_context: Optional[PlatformContext] = None
    ) -> ConversationState:
        """
        Start a new conversation.
        
        Args:
            customer_data: Customer information
            platform_context: Platform-specific context
            
        Returns:
            New conversation state
        """
        # Ensure initialized
        if not self.initialized:
            await self.initialize()
        
        # Use provided platform context or default
        context = platform_context or self.platform_context
        
        # Create conversation
        conversation = await self.conversation_manager.create_conversation(
            customer_data=customer_data,
            platform_context=context
        )
        
        self.current_conversation_id = conversation.conversation_id
        
        # Track conversation start
        await self.metrics_collector.track_conversation_event(
            conversation.conversation_id,
            "conversation_started",
            {
                "customer_type": customer_data.customer_type if customer_data else "unknown",
                "platform": context.platform_type if context else "unknown"
            }
        )
        
        logger.info(f"Started conversation {conversation.conversation_id}")
        return conversation
    
    async def process_message(
        self,
        conversation_id: str,
        message: str,
        voice_enabled: bool = False
    ) -> Dict[str, Any]:
        """
        Process an incoming message and generate a response.
        
        Args:
            conversation_id: Conversation identifier
            message: User's message
            voice_enabled: Whether to generate voice response
            
        Returns:
            Complete response with text, optional audio, and metadata
        """
        try:
            # Start performance timer
            timer_id = self.metrics_collector.start_timer("message_processing")
            
            # Get conversation state
            conversation = await self.conversation_manager.get_conversation(conversation_id)
            if not conversation:
                logger.error(f"Conversation {conversation_id} not found")
                return self._create_error_response("Conversation not found")
            
            # Validate message
            is_valid, error_msg = self.message_processor.validate_message(message)
            if not is_valid:
                return self._create_error_response(error_msg)
            
            # Add user message to conversation
            user_msg = Message(
                role="user",
                content=message,
                timestamp=datetime.utcnow()
            )
            await self.conversation_manager.add_message(conversation_id, user_msg)
            
            # Process and analyze the message
            analysis = await self.message_processor.process_message(message, conversation)
            
            # Check for human transfer
            if analysis.get("requires_human", False):
                transfer_result = await self.integration_handler.check_human_transfer(
                    conversation_state=conversation.dict(),
                    trigger_reason="low_confidence"
                )
                
                if transfer_result.get("transfer_needed"):
                    return await self._handle_human_transfer(
                        conversation_id,
                        transfer_result
                    )
            
            # Generate AI response if needed
            ai_response = None
            if analysis.get("intent", {}).get("type") not in ["greeting", "closing"]:
                ai_response = await self.integration_handler.generate_ai_response(
                    prompt=message,
                    context={
                        "conversation_history": [
                            {"role": m.role, "content": m.content}
                            for m in conversation.messages[-5:]
                        ],
                        "sales_phase": conversation.sales_phase,
                        "customer_type": conversation.customer_data.customer_type if conversation.customer_data else "unknown"
                    }
                )
            
            # Build response
            response = await self.response_builder.build_response(
                analysis=analysis,
                conversation_state=conversation,
                ai_response=ai_response
            )
            
            # Add assistant message to conversation
            assistant_msg = Message(
                role="assistant",
                content=response.get("text", ""),
                timestamp=datetime.utcnow(),
                metadata=response.get("metadata", {})
            )
            await self.conversation_manager.add_message(conversation_id, assistant_msg)
            
            # Generate voice if requested
            if voice_enabled and response.get("text"):
                audio = await self.integration_handler.synthesize_voice(
                    text=response["text"],
                    section=conversation.sales_phase
                )
                if audio:
                    response["audio"] = audio
            
            # Track metrics
            processing_time = self.metrics_collector.end_timer(timer_id)
            await self.metrics_collector.track_message_exchange(
                conversation_id=conversation_id,
                user_message=message,
                assistant_response=response.get("text", ""),
                analysis={**analysis, "response_time_ms": processing_time}
            )
            
            # Check for patterns
            await self._check_patterns(conversation_id, message, response, analysis)
            
            # Update conversation phase if needed
            await self._update_conversation_phase(conversation_id, analysis)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return self._create_error_response(str(e))
    
    async def end_conversation(
        self,
        conversation_id: str,
        reason: str = "completed"
    ) -> Dict[str, Any]:
        """
        End a conversation.
        
        Args:
            conversation_id: Conversation identifier
            reason: Reason for ending
            
        Returns:
            Conversation summary
        """
        try:
            # Get final metrics
            metrics = self.metrics_collector.get_conversation_metrics(conversation_id)
            
            # Get conversation for final analysis
            conversation = await self.conversation_manager.get_conversation(conversation_id)
            
            # Perform lead qualification
            qualification = None
            if conversation and conversation.customer_data:
                qualification = await self.integration_handler.qualify_lead(
                    customer_data=conversation.customer_data.dict(),
                    conversation_data={
                        "message_count": len(conversation.messages),
                        "duration": metrics.get("duration", 0),
                        "sentiment": metrics.get("sentiment_distribution", {})
                    }
                )
            
            # Track conversion if applicable
            if qualification and qualification.get("qualified"):
                await self.metrics_collector.track_conversion_event(
                    conversation_id,
                    "qualified_lead",
                    value=qualification.get("potential_value")
                )
            
            # End the conversation
            success = await self.conversation_manager.end_conversation(
                conversation_id,
                reason
            )
            
            # Track conversation end
            await self.metrics_collector.track_conversation_event(
                conversation_id,
                "conversation_ended",
                {
                    "reason": reason,
                    "qualified": qualification.get("qualified") if qualification else False,
                    "duration": metrics.get("duration", 0),
                    "message_count": metrics.get("message_count", 0)
                }
            )
            
            # Schedule follow-up if needed
            if qualification and qualification.get("qualified"):
                await self.integration_handler.schedule_follow_up(
                    conversation_id,
                    {
                        "type": "email",
                        "scheduled_time": datetime.utcnow() + timedelta(days=1),
                        "message": "Follow-up on our conversation about NGX"
                    }
                )
            
            return {
                "success": success,
                "conversation_id": conversation_id,
                "metrics": metrics,
                "qualification": qualification,
                "reason": reason
            }
            
        except Exception as e:
            logger.error(f"Error ending conversation: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_human_transfer(
        self,
        conversation_id: str,
        transfer_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle human transfer request."""
        response = {
            "text": "I'll connect you with one of our specialists who can better assist you. Please hold for a moment.",
            "requires_human": True,
            "transfer_details": transfer_result,
            "metadata": {
                "response_type": "human_transfer",
                "reason": transfer_result.get("reason"),
                "priority": transfer_result.get("priority")
            }
        }
        
        # Track the transfer event
        await self.metrics_collector.track_conversation_event(
            conversation_id,
            "human_transfer_requested",
            transfer_result
        )
        
        return response
    
    async def _check_patterns(
        self,
        conversation_id: str,
        message: str,
        response: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> None:
        """Check for conversation patterns."""
        try:
            # Import pattern recognition if available
            from src.services.pattern_recognition_engine import pattern_recognition_engine
            
            if pattern_recognition_engine:
                patterns = await pattern_recognition_engine.detect_patterns(
                    message=message,
                    context={
                        "intent": analysis.get("intent"),
                        "sentiment": analysis.get("nlp", {}).get("sentiment")
                    }
                )
                
                for pattern in patterns:
                    await self.metrics_collector.track_pattern_detection(
                        conversation_id,
                        pattern["type"],
                        pattern
                    )
        except Exception as e:
            logger.debug(f"Pattern detection not available: {e}")
    
    async def _update_conversation_phase(
        self,
        conversation_id: str,
        analysis: Dict[str, Any]
    ) -> None:
        """Update conversation sales phase based on analysis."""
        conversation = await self.conversation_manager.get_conversation(conversation_id)
        if not conversation:
            return
        
        # Determine new phase based on conversation progress
        current_phase = conversation.sales_phase or "greeting"
        message_count = len(conversation.messages)
        
        new_phase = current_phase
        
        if current_phase == "greeting" and message_count > 2:
            new_phase = "discovery"
        elif current_phase == "discovery" and message_count > 6:
            new_phase = "qualification"
        elif current_phase == "qualification" and analysis.get("intent", {}).get("type") == "interest":
            new_phase = "presentation"
        elif current_phase == "presentation" and "price" in str(analysis.get("intent", {})):
            new_phase = "objection_handling"
        elif current_phase == "objection_handling" and analysis.get("nlp", {}).get("sentiment") == "positive":
            new_phase = "closing"
        
        if new_phase != current_phase:
            await self.conversation_manager.update_conversation(
                conversation_id,
                {"sales_phase": new_phase}
            )
            
            await self.metrics_collector.track_conversation_event(
                conversation_id,
                "phase_transition",
                {
                    "from_phase": current_phase,
                    "to_phase": new_phase
                }
            )
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create an error response."""
        return {
            "text": "I apologize for the inconvenience. Let me connect you with someone who can help.",
            "error": error_message,
            "requires_human": True,
            "metadata": {
                "response_type": "error",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    
    # Backward compatibility methods
    async def handle_message(
        self,
        message: str,
        conversation_state: ConversationState
    ) -> Tuple[str, Optional[bytes]]:
        """
        Legacy method for backward compatibility.
        
        Args:
            message: User message
            conversation_state: Conversation state
            
        Returns:
            Tuple of (response_text, optional_audio)
        """
        result = await self.process_message(
            conversation_state.conversation_id,
            message,
            voice_enabled=True
        )
        
        return result.get("text", ""), result.get("audio")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return self.metrics_collector.get_aggregate_metrics()
    
    def get_conversation_metrics(self, conversation_id: str) -> Dict[str, Any]:
        """Get metrics for specific conversation."""
        return self.metrics_collector.get_conversation_metrics(conversation_id)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components."""
        return await self.integration_handler.health_check()