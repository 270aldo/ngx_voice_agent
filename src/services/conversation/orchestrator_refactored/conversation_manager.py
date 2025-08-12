"""
Conversation Manager

Manages conversation state, sessions, and lifecycle operations.
Single responsibility: Conversation state management.
"""

import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from src.models.conversation import ConversationState, CustomerData, Message
from src.models.platform_context import PlatformContext
from src.integrations.supabase.resilient_client import resilient_supabase_client as supabase_client

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation state and lifecycle."""
    
    def __init__(self):
        """Initialize the conversation manager."""
        self.conversations: Dict[str, ConversationState] = {}
        self.supabase_client = supabase_client
        
    async def create_conversation(
        self,
        customer_data: CustomerData,
        platform_context: Optional[PlatformContext] = None
    ) -> ConversationState:
        """
        Create a new conversation.
        
        Args:
            customer_data: Customer information
            platform_context: Platform-specific context
            
        Returns:
            New conversation state
        """
        conversation_id = str(uuid.uuid4())
        
        conversation = ConversationState(
            conversation_id=conversation_id,
            customer_data=customer_data,
            platform_context=platform_context,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            messages=[],
            context={},
            metadata={
                "version": "2.0",
                "refactored": True
            }
        )
        
        # Store in memory
        self.conversations[conversation_id] = conversation
        
        # Persist to database
        try:
            await self._persist_conversation(conversation)
        except Exception as e:
            logger.error(f"Failed to persist conversation {conversation_id}: {e}")
            # Continue even if persistence fails
        
        logger.info(f"Created conversation {conversation_id}")
        return conversation
    
    async def get_conversation(self, conversation_id: str) -> Optional[ConversationState]:
        """
        Get a conversation by ID.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Conversation state or None if not found
        """
        # Check memory first
        if conversation_id in self.conversations:
            return self.conversations[conversation_id]
        
        # Try to load from database
        try:
            conversation = await self._load_conversation(conversation_id)
            if conversation:
                self.conversations[conversation_id] = conversation
                return conversation
        except Exception as e:
            logger.error(f"Failed to load conversation {conversation_id}: {e}")
        
        return None
    
    async def update_conversation(
        self,
        conversation_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update conversation state.
        
        Args:
            conversation_id: Conversation identifier
            updates: Dictionary of updates to apply
            
        Returns:
            True if successful, False otherwise
        """
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            return False
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(conversation, key):
                setattr(conversation, key, value)
        
        conversation.updated_at = datetime.utcnow()
        
        # Persist changes
        try:
            await self._persist_conversation(conversation)
            return True
        except Exception as e:
            logger.error(f"Failed to update conversation {conversation_id}: {e}")
            return False
    
    async def add_message(
        self,
        conversation_id: str,
        message: Message
    ) -> bool:
        """
        Add a message to the conversation.
        
        Args:
            conversation_id: Conversation identifier
            message: Message to add
            
        Returns:
            True if successful, False otherwise
        """
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            return False
        
        conversation.messages.append(message)
        conversation.message_count = len(conversation.messages)
        conversation.updated_at = datetime.utcnow()
        
        # Update last message timestamp
        if message.role == "user":
            conversation.last_user_message = message.content
            conversation.last_user_message_at = message.timestamp
        elif message.role == "assistant":
            conversation.last_assistant_message = message.content
            conversation.last_assistant_message_at = message.timestamp
        
        # Persist changes
        try:
            await self._persist_message(conversation_id, message)
            return True
        except Exception as e:
            logger.error(f"Failed to add message to conversation {conversation_id}: {e}")
            return False
    
    async def end_conversation(
        self,
        conversation_id: str,
        reason: str = "completed"
    ) -> bool:
        """
        End a conversation.
        
        Args:
            conversation_id: Conversation identifier
            reason: Reason for ending the conversation
            
        Returns:
            True if successful, False otherwise
        """
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            return False
        
        conversation.status = "completed"
        conversation.ended_at = datetime.utcnow()
        conversation.end_reason = reason
        
        # Calculate duration
        if conversation.created_at:
            duration = (conversation.ended_at - conversation.created_at).total_seconds()
            conversation.duration_seconds = duration
        
        # Persist final state
        try:
            await self._persist_conversation(conversation)
            
            # Remove from memory after successful persistence
            if conversation_id in self.conversations:
                del self.conversations[conversation_id]
            
            logger.info(f"Ended conversation {conversation_id}: {reason}")
            return True
        except Exception as e:
            logger.error(f"Failed to end conversation {conversation_id}: {e}")
            return False
    
    async def _persist_conversation(self, conversation: ConversationState) -> None:
        """Persist conversation to database."""
        if not self.supabase_client:
            return
        
        data = {
            "id": conversation.conversation_id,
            "customer_data": conversation.customer_data.dict() if conversation.customer_data else {},
            "status": conversation.status,
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
            "metadata": conversation.metadata or {},
            "context": conversation.context or {},
            "message_count": conversation.message_count,
            "sales_phase": conversation.sales_phase,
        }
        
        await self.supabase_client.upsert("conversations", data)
    
    async def _persist_message(self, conversation_id: str, message: Message) -> None:
        """Persist message to database."""
        if not self.supabase_client:
            return
        
        data = {
            "conversation_id": conversation_id,
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            "metadata": message.metadata or {}
        }
        
        await self.supabase_client.insert("messages", data)
    
    async def _load_conversation(self, conversation_id: str) -> Optional[ConversationState]:
        """Load conversation from database."""
        if not self.supabase_client:
            return None
        
        try:
            result = await self.supabase_client.get(
                "conversations",
                {"id": conversation_id}
            )
            
            if result and result.data:
                # Convert database record to ConversationState
                # This is simplified - you'd need proper deserialization
                return ConversationState(**result.data[0])
        except Exception as e:
            logger.error(f"Failed to load conversation from database: {e}")
        
        return None
    
    def get_active_conversations(self) -> Dict[str, ConversationState]:
        """Get all active conversations in memory."""
        return {
            cid: conv for cid, conv in self.conversations.items()
            if conv.status == "active"
        }
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get statistics about conversations."""
        total = len(self.conversations)
        active = len(self.get_active_conversations())
        
        return {
            "total_in_memory": total,
            "active": active,
            "completed": total - active,
            "memory_usage_mb": total * 0.01  # Rough estimate
        }