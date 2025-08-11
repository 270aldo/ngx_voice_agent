"""
Conversation endpoints for NGX Command Center

Handles conversation listing, messaging, and monitoring.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

from src.models.user import User
from src.core.auth.deps import get_current_user
from src.integrations.supabase.client import supabase_client
from src.utils.structured_logging import StructuredLogger
from src.services.websocket.broadcast_service import broadcast_service
from pydantic import BaseModel

logger = StructuredLogger.get_logger(__name__)
router = APIRouter()


class ConversationResponse(BaseModel):
    """Conversation response model"""
    id: str
    customer: Dict[str, Any]
    status: str
    channel: str
    startedAt: datetime
    lastMessage: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any]
    agent: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    """Message response model"""
    id: str
    text: str
    timestamp: datetime
    isAgent: bool
    metadata: Optional[Dict[str, Any]] = None


class SendMessageRequest(BaseModel):
    """Send message request model"""
    message: str


class EndConversationRequest(BaseModel):
    """End conversation request model"""
    outcome: str
    summary: Optional[Dict[str, Any]] = None


@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> List[ConversationResponse]:
    """
    List conversations for the organization.
    
    Returns conversations with optional status filtering.
    """
    supabase = supabase_client
    
    try:
        # Build query
        query = supabase.table("conversations").select("*").eq(
            "organization_id", str(current_user.organization_id)
        )
        
        # Apply status filter if provided
        if status:
            query = query.eq("status", status)
        
        # Apply pagination
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        
        response = query.execute()
        
        if not response.data:
            return []
        
        # Transform to response format
        conversations = []
        for conv in response.data:
            conversation = ConversationResponse(
                id=conv["id"],
                customer={
                    "name": conv.get("customer_name", "Unknown"),
                    "email": conv.get("customer_email"),
                    "phone": conv.get("customer_phone")
                },
                status=conv["status"],
                channel=conv.get("channel", "chat"),
                startedAt=datetime.fromisoformat(conv["created_at"]),
                lastMessage=conv.get("last_message"),
                metrics={
                    "duration": conv.get("duration", 0),
                    "messageCount": conv.get("message_count", 0),
                    "sentiment": conv.get("sentiment", "neutral")
                },
                agent={
                    "name": "NGX Agent",
                    "status": "ready"
                } if conv["status"] == "active" else None
            )
            conversations.append(conversation)
        
        return conversations
        
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list conversations"
        )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
) -> ConversationResponse:
    """
    Get a specific conversation by ID.
    
    Returns conversation details if user has access.
    """
    supabase = supabase_client
    
    try:
        response = supabase.table("conversations").select("*").eq(
            "id", conversation_id
        ).eq(
            "organization_id", str(current_user.organization_id)
        ).single().execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        conv = response.data
        
        return ConversationResponse(
            id=conv["id"],
            customer={
                "name": conv.get("customer_name", "Unknown"),
                "email": conv.get("customer_email"),
                "phone": conv.get("customer_phone")
            },
            status=conv["status"],
            channel=conv.get("channel", "chat"),
            startedAt=datetime.fromisoformat(conv["created_at"]),
            lastMessage=conv.get("last_message"),
            metrics={
                "duration": conv.get("duration", 0),
                "messageCount": conv.get("message_count", 0),
                "sentiment": conv.get("sentiment", "neutral")
            },
            agent={
                "name": "NGX Agent",
                "status": "ready"
            } if conv["status"] == "active" else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get conversation"
        )


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> List[MessageResponse]:
    """
    Get messages for a conversation.
    
    Returns messages in chronological order.
    """
    supabase = supabase_client
    
    try:
        # First verify conversation belongs to user's organization
        conv_response = supabase.table("conversations").select("id").eq(
            "id", conversation_id
        ).eq(
            "organization_id", str(current_user.organization_id)
        ).single().execute()
        
        if not conv_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Get messages
        response = supabase.table("messages").select("*").eq(
            "conversation_id", conversation_id
        ).order("created_at").range(offset, offset + limit - 1).execute()
        
        if not response.data:
            return []
        
        # Transform to response format
        messages = []
        for msg in response.data:
            message = MessageResponse(
                id=msg["id"],
                text=msg["content"],
                timestamp=datetime.fromisoformat(msg["created_at"]),
                isAgent=msg.get("is_agent", False),
                metadata=msg.get("metadata", {})
            )
            messages.append(message)
        
        return messages
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get messages"
        )


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user)
) -> MessageResponse:
    """
    Send a message in a conversation.
    
    This allows human agents to intervene in conversations.
    """
    supabase = supabase_client
    
    try:
        # Verify conversation belongs to user's organization and is active
        conv_response = supabase.table("conversations").select("*").eq(
            "id", conversation_id
        ).eq(
            "organization_id", str(current_user.organization_id)
        ).single().execute()
        
        if not conv_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        if conv_response.data["status"] != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation is not active"
            )
        
        # Create message
        message_id = str(uuid.uuid4())
        message_data = {
            "id": message_id,
            "conversation_id": conversation_id,
            "content": request.message,
            "is_agent": False,  # Human intervention
            "sender_id": str(current_user.id),
            "sender_name": current_user.full_name,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {
                "type": "human_intervention",
                "user_role": current_user.role
            }
        }
        
        response = supabase.table("messages").insert(message_data).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send message"
            )
        
        # Update conversation
        supabase.table("conversations").update({
            "last_message": {
                "text": request.message,
                "timestamp": message_data["created_at"],
                "isAgent": False
            },
            "message_count": conv_response.data.get("message_count", 0) + 1,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", conversation_id).execute()
        
        # Broadcast via WebSocket
        await broadcast_service.broadcast_conversation_message(
            organization_id=str(current_user.organization_id),
            conversation_id=conversation_id,
            message={
                "text": request.message,
                "metadata": message_data["metadata"]
            },
            is_agent=False
        )
        
        return MessageResponse(
            id=message_id,
            text=request.message,
            timestamp=datetime.utcnow(),
            isAgent=False,
            metadata=message_data["metadata"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )


@router.post("/{conversation_id}/end")
async def end_conversation(
    conversation_id: str,
    request: EndConversationRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    End a conversation.
    
    Marks the conversation as ended with the specified outcome.
    """
    supabase = supabase_client
    
    try:
        # Verify conversation belongs to user's organization
        conv_response = supabase.table("conversations").select("*").eq(
            "id", conversation_id
        ).eq(
            "organization_id", str(current_user.organization_id)
        ).single().execute()
        
        if not conv_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        if conv_response.data["status"] == "ended":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation already ended"
            )
        
        # Calculate duration
        started_at = datetime.fromisoformat(conv_response.data["created_at"])
        duration = int((datetime.utcnow() - started_at).total_seconds())
        
        # Update conversation
        update_data = {
            "status": "ended",
            "outcome": request.outcome,
            "ended_at": datetime.utcnow().isoformat(),
            "duration": duration,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if request.summary:
            update_data["summary"] = request.summary
        
        response = supabase.table("conversations").update(
            update_data
        ).eq("id", conversation_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to end conversation"
            )
        
        # Broadcast via WebSocket
        await broadcast_service.broadcast_conversation_ended(
            organization_id=str(current_user.organization_id),
            conversation_id=conversation_id,
            outcome=request.outcome,
            summary=request.summary
        )
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "outcome": request.outcome,
            "duration": duration
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to end conversation"
        )