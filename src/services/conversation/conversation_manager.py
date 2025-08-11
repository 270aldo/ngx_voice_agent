"""
Conversation Manager - Handles conversation state and lifecycle.
Part of the ConversationOrchestrator refactoring to break down the god class.
"""

import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.models.conversation import ConversationState, CustomerData, Message
from src.models.platform_context import PlatformContext
from src.services.conversation.service_registry import ServiceRegistry
from src.integrations.supabase.resilient_client import resilient_supabase_client as supabase_client

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages conversation state and lifecycle.
    
    Responsibilities:
    - Start/end conversations
    - Load/save conversation state
    - Session registration
    - Platform context management
    """
    
    def __init__(self, service_registry: ServiceRegistry):
        """
        Initialize the conversation manager.
        
        Args:
            service_registry: Service registry for dependencies
        """
        self.service_registry = service_registry
        self._conversations: Dict[str, ConversationState] = {}
        self._sessions: Dict[str, str] = {}  # session_id -> conversation_id
        
        logger.info("ConversationManager initialized")
    
    async def initialize(self):
        """Initialize the conversation manager."""
        logger.info("ConversationManager ready")
    
    async def start_conversation(
        self,
        customer_data: CustomerData,
        program_type: Optional[str] = None,
        platform_context: Optional[PlatformContext] = None
    ) -> ConversationState:
        """
        Start a new conversation.
        
        Args:
            customer_data: Customer information
            program_type: Optional program type override
            platform_context: Platform context information
            
        Returns:
            Initial conversation state
        """
        conversation_id = str(uuid.uuid4())
        
        # Auto-detect program if not provided
        if not program_type:
            program_type = await self._auto_detect_program(customer_data, platform_context)
        
        # Create initial state
        state = ConversationState(
            conversation_id=conversation_id,
            customer=customer_data,
            messages=[],
            program_type=program_type,
            phase="greeting",
            start_time=datetime.now(),
            metadata={
                "ml_tracking_enabled": True,
                "platform_context": platform_context.to_dict() if platform_context else {}
            },
            platform_context=platform_context
        )
        
        # Save state
        await self._save_conversation_state(state)
        
        # Store in memory
        self._conversations[conversation_id] = state
        
        # Track conversation start
        await self._track_conversation_start(state)
        
        logger.info(f"Started conversation {conversation_id} with program: {program_type}")
        
        return state
    
    async def get_state(self, conversation_id: str) -> ConversationState:
        """
        Get conversation state.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Conversation state
            
        Raises:
            ValueError: If conversation not found
        """
        # Check memory first
        if conversation_id in self._conversations:
            return self._conversations[conversation_id]
        
        # Load from database
        state = await self._get_conversation_state(conversation_id)
        if not state:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Cache in memory
        self._conversations[conversation_id] = state
        
        return state
    
    async def save_state(self, state: ConversationState):
        """
        Save conversation state.
        
        Args:
            state: Conversation state to save
        """
        # Update memory
        self._conversations[state.conversation_id] = state
        
        # Save to database
        await self._save_conversation_state(state)
    
    async def end_conversation(
        self,
        conversation_id: str,
        end_reason: str = "completed"
    ) -> Dict[str, Any]:
        """
        End a conversation.
        
        Args:
            conversation_id: Conversation ID
            end_reason: Reason for ending
            
        Returns:
            Conversation summary
        """
        try:
            state = await self.get_state(conversation_id)
            
            # Update state
            state.status = end_reason
            state.end_time = datetime.now()
            
            # Calculate duration
            duration = (state.end_time - state.start_time).total_seconds()
            
            # Save final state
            await self._save_conversation_state(state)
            
            # Update database status
            await supabase_client.conversations.update(
                conversation_id,
                {
                    "status": end_reason,
                    "ended_at": state.end_time.isoformat(),
                    "total_duration_seconds": int(duration),
                    "message_count": len(state.messages)
                }
            )
            
            # Track conversation end
            await self._track_conversation_end(state, end_reason)
            
            # Remove from memory
            self._conversations.pop(conversation_id, None)
            
            # Create summary
            summary = {
                "conversation_id": conversation_id,
                "status": end_reason,
                "duration_seconds": duration,
                "message_count": len(state.messages),
                "program_type": state.program_type,
                "outcome": state.metadata.get("outcome", "unknown")
            }
            
            logger.info(f"Ended conversation {conversation_id}: {end_reason}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error ending conversation {conversation_id}: {e}")
            raise
    
    async def register_session(self, session_id: str, conversation_id: str):
        """
        Register a session to conversation mapping.
        
        Args:
            session_id: Session identifier
            conversation_id: Conversation identifier
        """
        self._sessions[session_id] = conversation_id
        logger.debug(f"Registered session {session_id} -> conversation {conversation_id}")
    
    async def get_conversation_by_session(self, session_id: str) -> Optional[str]:
        """
        Get conversation ID by session ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Conversation ID or None
        """
        return self._sessions.get(session_id)
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a message to conversation history.
        
        Args:
            conversation_id: Conversation ID
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional message metadata
        """
        state = await self.get_state(conversation_id)
        
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        state.messages.append(message)
        state.last_message_at = datetime.now()
        
        # Save updated state
        await self.save_state(state)
        
        # Also save to messages table
        try:
            await supabase_client.messages.create({
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "metadata": metadata or {}
            })
        except Exception as e:
            logger.error(f"Failed to save message to database: {e}")
    
    async def _get_conversation_state(self, conversation_id: str) -> Optional[ConversationState]:
        """Load conversation state from database."""
        try:
            # Get conversation data
            conversation = await supabase_client.conversations.get(conversation_id)
            if not conversation:
                return None
            
            # Get messages
            messages = await supabase_client.messages.get_by_conversation(conversation_id)
            
            # Reconstruct state
            state = ConversationState(
                conversation_id=conversation_id,
                customer=CustomerData(
                    name=conversation.get("customer_name", ""),
                    phone=conversation.get("customer_phone", ""),
                    email=conversation.get("customer_email"),
                    business_type=conversation.get("business_type")
                ),
                messages=[
                    Message(
                        role=msg["role"],
                        content=msg["content"],
                        timestamp=msg["created_at"],
                        metadata=msg.get("metadata", {})
                    )
                    for msg in messages
                ],
                program_type=conversation.get("program_type", "ngx_30k"),
                phase=conversation.get("phase", "greeting"),
                start_time=datetime.fromisoformat(conversation["created_at"]),
                metadata=conversation.get("metadata", {}),
                status=conversation.get("status", "active"),
                platform_context=PlatformContext.from_dict(
                    conversation.get("platform_context", {})
                ) if conversation.get("platform_context") else None
            )
            
            return state
            
        except Exception as e:
            logger.error(f"Error loading conversation state: {e}")
            return None
    
    async def _save_conversation_state(self, state: ConversationState):
        """Save conversation state to database."""
        try:
            data = {
                "conversation_id": state.conversation_id,
                "customer_name": state.customer.name,
                "customer_phone": state.customer.phone,
                "customer_email": state.customer.email,
                "business_type": state.customer.business_type,
                "program_type": state.program_type,
                "phase": state.phase,
                "status": state.status,
                "metadata": state.metadata,
                "platform_context": state.platform_context.to_dict() if state.platform_context else {},
                "message_count": len(state.messages),
                "last_message_at": state.last_message_at.isoformat() if state.last_message_at else None
            }
            
            # Create or update
            existing = await supabase_client.conversations.get(state.conversation_id)
            if existing:
                await supabase_client.conversations.update(state.conversation_id, data)
            else:
                await supabase_client.conversations.create(data)
                
        except Exception as e:
            logger.error(f"Error saving conversation state: {e}")
            raise
    
    async def _auto_detect_program(
        self,
        customer_data: CustomerData,
        platform_context: Optional[PlatformContext]
    ) -> str:
        """Auto-detect the best program for a customer."""
        # Default program
        default_program = "ngx_30k"
        
        # Check if we have a program router service
        program_router = self.service_registry.get('program_router')
        if not program_router:
            return default_program
        
        try:
            # Use business type and platform info for detection
            context = {
                "business_type": customer_data.business_type,
                "platform": platform_context.platform_info.platform_type if platform_context else None,
                "source": platform_context.platform_info.source_type if platform_context else None
            }
            
            detected_program = await program_router.detect_program(context)
            return detected_program or default_program
            
        except Exception as e:
            logger.error(f"Error detecting program: {e}")
            return default_program
    
    async def _track_conversation_start(self, state: ConversationState):
        """Track conversation start event."""
        try:
            # Track with ML Pipeline if available
            ml_pipeline = self.service_registry.get('ml_pipeline')
            if ml_pipeline:
                await ml_pipeline.track_event(
                    conversation_id=state.conversation_id,
                    event_type="conversation_started",
                    event_data={
                        "program_type": state.program_type,
                        "platform": state.platform_context.platform_info.platform_type if state.platform_context else None,
                        "customer_type": state.customer.business_type
                    }
                )
        except Exception as e:
            logger.error(f"Error tracking conversation start: {e}")
    
    async def _track_conversation_end(self, state: ConversationState, end_reason: str):
        """Track conversation end event."""
        try:
            # Track with ML Pipeline if available
            ml_pipeline = self.service_registry.get('ml_pipeline')
            if ml_pipeline:
                duration = (state.end_time - state.start_time).total_seconds() if state.end_time else 0
                
                await ml_pipeline.track_event(
                    conversation_id=state.conversation_id,
                    event_type="conversation_ended",
                    event_data={
                        "end_reason": end_reason,
                        "duration_seconds": duration,
                        "message_count": len(state.messages),
                        "outcome": state.metadata.get("outcome", "unknown"),
                        "final_phase": state.phase
                    }
                )
        except Exception as e:
            logger.error(f"Error tracking conversation end: {e}")
    
    async def cleanup(self):
        """Cleanup manager resources."""
        self._conversations.clear()
        self._sessions.clear()
        logger.info("ConversationManager cleaned up")