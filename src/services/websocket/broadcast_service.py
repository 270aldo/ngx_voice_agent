"""
WebSocket Broadcast Service

Provides methods to broadcast real-time updates from various parts
of the application to connected WebSocket clients.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

from src.services.websocket.websocket_manager import manager
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)


class BroadcastService:
    """Service for broadcasting updates via WebSocket."""
    
    @staticmethod
    async def broadcast_conversation_started(
        organization_id: str,
        conversation_id: str,
        customer_info: dict
    ):
        """Broadcast when a new conversation starts."""
        try:
            await manager.broadcast_conversation_update(
                organization_id=organization_id,
                conversation_id=conversation_id,
                event_type="started",
                data={
                    "customer": customer_info,
                    "status": "active",
                    "started_at": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error broadcasting conversation start: {e}")
    
    @staticmethod
    async def broadcast_conversation_message(
        organization_id: str,
        conversation_id: str,
        message: dict,
        is_agent: bool = False
    ):
        """Broadcast a new message in a conversation."""
        try:
            await manager.broadcast_conversation_update(
                organization_id=organization_id,
                conversation_id=conversation_id,
                event_type="message",
                data={
                    "message": message,
                    "is_agent": is_agent,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error broadcasting conversation message: {e}")
    
    @staticmethod
    async def broadcast_conversation_ended(
        organization_id: str,
        conversation_id: str,
        outcome: str,
        summary: Optional[dict] = None
    ):
        """Broadcast when a conversation ends."""
        try:
            await manager.broadcast_conversation_update(
                organization_id=organization_id,
                conversation_id=conversation_id,
                event_type="ended",
                data={
                    "outcome": outcome,
                    "summary": summary,
                    "ended_at": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error broadcasting conversation end: {e}")
    
    @staticmethod
    async def broadcast_metric_update(
        organization_id: str,
        metrics: dict
    ):
        """Broadcast updated metrics."""
        try:
            # Broadcast different metric types
            if "conversion_rate" in metrics:
                await manager.broadcast_metric_update(
                    organization_id=organization_id,
                    metric_type="conversion",
                    data=metrics
                )
            
            if "response_time" in metrics:
                await manager.broadcast_metric_update(
                    organization_id=organization_id,
                    metric_type="performance",
                    data={
                        "response_time": metrics["response_time"],
                        "throughput": metrics.get("throughput", 0)
                    }
                )
            
            if "active_conversations" in metrics:
                await manager.broadcast_metric_update(
                    organization_id=organization_id,
                    metric_type="activity",
                    data={
                        "active_conversations": metrics["active_conversations"],
                        "total_conversations": metrics.get("total_conversations", 0)
                    }
                )
                
        except Exception as e:
            logger.error(f"Error broadcasting metric update: {e}")
    
    @staticmethod
    async def broadcast_agent_status_change(
        organization_id: str,
        agent_id: str,
        status: str,
        details: Optional[dict] = None
    ):
        """Broadcast agent status changes."""
        try:
            message = {
                "type": "agent_status",
                "agent_id": agent_id,
                "status": status,
                "details": details or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            await manager.send_organization_message(message, organization_id)
        except Exception as e:
            logger.error(f"Error broadcasting agent status: {e}")
    
    @staticmethod
    async def broadcast_lead_qualified(
        organization_id: str,
        lead_info: dict,
        score: float,
        tier: str
    ):
        """Broadcast when a lead is qualified."""
        try:
            message = {
                "type": "lead_qualified",
                "lead": lead_info,
                "qualification": {
                    "score": score,
                    "tier": tier,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            await manager.send_organization_message(message, organization_id)
        except Exception as e:
            logger.error(f"Error broadcasting lead qualification: {e}")
    
    @staticmethod
    async def broadcast_pattern_detected(
        organization_id: str,
        pattern_type: str,
        confidence: float,
        context: dict
    ):
        """Broadcast when a significant pattern is detected."""
        try:
            message = {
                "type": "pattern_detected",
                "pattern": {
                    "type": pattern_type,
                    "confidence": confidence,
                    "context": context,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            await manager.send_organization_message(message, organization_id)
        except Exception as e:
            logger.error(f"Error broadcasting pattern detection: {e}")


# Create global broadcast service instance
broadcast_service = BroadcastService()