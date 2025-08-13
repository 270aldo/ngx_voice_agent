"""
Conversation Tracker Module

Provides tracking functionality for conversations.
This is a compatibility wrapper for the metrics service.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio

from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)


class ConversationTracker:
    """
    Tracks conversation metrics and state.
    This is a simplified implementation for compatibility.
    """
    
    def __init__(self):
        """Initialize the conversation tracker."""
        self.active_conversations = {}
        self.conversation_metrics = {}
        
    async def track_conversation_start(self, conversation_id: str, metadata: Dict[str, Any] = None) -> None:
        """Track the start of a conversation."""
        self.active_conversations[conversation_id] = {
            "start_time": datetime.utcnow(),
            "metadata": metadata or {},
            "messages": 0,
            "status": "active"
        }
        logger.info(f"Started tracking conversation: {conversation_id}")
        
    async def track_message(self, conversation_id: str, message_type: str = "user") -> None:
        """Track a message in a conversation."""
        if conversation_id in self.active_conversations:
            self.active_conversations[conversation_id]["messages"] += 1
            self.active_conversations[conversation_id]["last_message_time"] = datetime.utcnow()
            
    async def track_conversation_end(self, conversation_id: str, outcome: str = "completed") -> None:
        """Track the end of a conversation."""
        if conversation_id in self.active_conversations:
            conversation_data = self.active_conversations[conversation_id]
            conversation_data["end_time"] = datetime.utcnow()
            conversation_data["status"] = outcome
            
            # Move to metrics
            self.conversation_metrics[conversation_id] = conversation_data
            del self.active_conversations[conversation_id]
            
            logger.info(f"Ended tracking conversation: {conversation_id} with outcome: {outcome}")
            
    async def get_active_conversations(self) -> List[Dict[str, Any]]:
        """Get all active conversations."""
        return [
            {
                "conversation_id": conv_id,
                **data
            }
            for conv_id, data in self.active_conversations.items()
        ]
        
    async def get_conversation_metrics(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific conversation."""
        if conversation_id in self.active_conversations:
            return self.active_conversations[conversation_id]
        return self.conversation_metrics.get(conversation_id)
        
    async def get_aggregate_metrics(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get aggregate metrics for a time window."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        active_count = len(self.active_conversations)
        recent_conversations = [
            conv for conv in self.conversation_metrics.values()
            if conv.get("start_time", datetime.min) > cutoff_time
        ]
        
        total_messages = sum(
            conv.get("messages", 0) 
            for conv in list(self.active_conversations.values()) + recent_conversations
        )
        
        return {
            "active_conversations": active_count,
            "completed_conversations": len(recent_conversations),
            "total_messages": total_messages,
            "average_messages_per_conversation": total_messages / max(1, active_count + len(recent_conversations))
        }


# Global instance for easy import
conversation_tracker = ConversationTracker()