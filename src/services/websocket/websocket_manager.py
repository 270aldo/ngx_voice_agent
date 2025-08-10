"""
WebSocket Manager for real-time communications

Handles WebSocket connections, authentication, and real-time updates
for the NGX Command Center dashboard.
"""

import asyncio
import json
import uuid
from typing import Dict, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status
from jose import JWTError, jwt

from src.config.settings import settings
from src.models.user import User, TokenData
from src.integrations.supabase.client import supabase_client
from src.utils.structured_logging import StructuredLogger
from src.auth.jwt_handler import JWTHandler

logger = StructuredLogger.get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        # Active connections by user_id
        self.active_connections: Dict[str, WebSocket] = {}
        # Organization subscriptions
        self.organization_subscriptions: Dict[str, Set[str]] = {}
        # Connection metadata
        self.connection_metadata: Dict[str, dict] = {}
        
    async def connect(
        self, 
        websocket: WebSocket, 
        user_id: str, 
        organization_id: str
    ):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        # Store connection
        self.active_connections[user_id] = websocket
        
        # Add to organization subscription
        if organization_id not in self.organization_subscriptions:
            self.organization_subscriptions[organization_id] = set()
        self.organization_subscriptions[organization_id].add(user_id)
        
        # Store metadata
        self.connection_metadata[user_id] = {
            "organization_id": organization_id,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow()
        }
        
        logger.info(f"User {user_id} connected to WebSocket")
        
        # Send welcome message
        await self.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "timestamp": datetime.utcnow().isoformat()
            },
            user_id
        )
        
    async def connect_authenticated_user(
        self, 
        websocket: WebSocket, 
        user_id: str, 
        organization_id: str
    ):
        """Register an already-accepted WebSocket connection for authenticated user."""
        
        # Store connection
        self.active_connections[user_id] = websocket
        
        # Add to organization subscription
        if organization_id not in self.organization_subscriptions:
            self.organization_subscriptions[organization_id] = set()
        self.organization_subscriptions[organization_id].add(user_id)
        
        # Store metadata
        self.connection_metadata[user_id] = {
            "organization_id": organization_id,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow()
        }
        
        logger.info(f"User {user_id} connected to WebSocket")
        
        # Send welcome message
        await self.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "timestamp": datetime.utcnow().isoformat()
            },
            user_id
        )
        
    def disconnect(self, user_id: str):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            
        # Remove from organization subscriptions
        metadata = self.connection_metadata.get(user_id)
        if metadata and metadata.get("organization_id"):
            org_id = metadata["organization_id"]
            if org_id in self.organization_subscriptions:
                self.organization_subscriptions[org_id].discard(user_id)
                if not self.organization_subscriptions[org_id]:
                    del self.organization_subscriptions[org_id]
        
        # Clean up metadata
        if user_id in self.connection_metadata:
            del self.connection_metadata[user_id]
            
        logger.info(f"User {user_id} disconnected from WebSocket")
        
    async def send_personal_message(self, message: dict, user_id: str):
        """Send a message to a specific user."""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                self.disconnect(user_id)
                
    async def send_organization_message(self, message: dict, organization_id: str):
        """Send a message to all users in an organization."""
        if organization_id in self.organization_subscriptions:
            tasks = []
            for user_id in self.organization_subscriptions[organization_id]:
                if user_id in self.active_connections:
                    tasks.append(self.send_personal_message(message, user_id))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
    async def broadcast_metric_update(
        self, 
        organization_id: str, 
        metric_type: str, 
        data: dict
    ):
        """Broadcast metric updates to an organization."""
        message = {
            "type": "metric_update",
            "metric_type": metric_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_organization_message(message, organization_id)
        
    async def broadcast_conversation_update(
        self, 
        organization_id: str, 
        conversation_id: str, 
        event_type: str,
        data: dict
    ):
        """Broadcast conversation updates to an organization."""
        message = {
            "type": "conversation_update",
            "conversation_id": conversation_id,
            "event_type": event_type,  # started, message, ended, transferred
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_organization_message(message, organization_id)
        
    async def handle_ping(self, user_id: str):
        """Handle ping message to keep connection alive."""
        if user_id in self.connection_metadata:
            self.connection_metadata[user_id]["last_ping"] = datetime.utcnow()
            await self.send_personal_message(
                {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
                user_id
            )
            
    async def cleanup_stale_connections(self):
        """Clean up stale connections periodically."""
        current_time = datetime.utcnow()
        stale_connections = []
        
        for user_id, metadata in self.connection_metadata.items():
            last_ping = metadata.get("last_ping")
            if last_ping:
                time_diff = (current_time - last_ping).total_seconds()
                if time_diff > settings.WS_CONNECTION_TIMEOUT:
                    stale_connections.append(user_id)
                    
        for user_id in stale_connections:
            logger.warning(f"Cleaning up stale connection for user {user_id}")
            self.disconnect(user_id)


# Global connection manager instance
manager = ConnectionManager()


async def authenticate_websocket(token: str) -> Optional[User]:
    """Authenticate WebSocket connection using JWT token."""
    try:
        # Decode token using JWTHandler for proper secret rotation support
        try:
            payload = JWTHandler.decode_token(token)
        except Exception as decode_error:
            logger.error(f"JWT decode error: {decode_error}")
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
            
        # Get user from database
        supabase = supabase_client
        response = supabase.table("users").select("*").eq(
            "id", user_id
        ).single().execute()
        
        if not response.data:
            return None
            
        user_data = response.data
        
        # Create User object
        user = User(
            id=user_data["id"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            organization_id=user_data["organization_id"],
            role=user_data["role"],
            is_active=user_data["is_active"],
            created_at=datetime.fromisoformat(user_data["created_at"]),
            updated_at=datetime.fromisoformat(user_data["updated_at"])
        )
        
        if not user.is_active:
            return None
            
        return user
        
    except (JWTError, Exception) as e:
        logger.error(f"WebSocket authentication error: {e}")
        return None


async def websocket_endpoint(websocket: WebSocket, token: str):
    """Main WebSocket endpoint handler."""
    # SECURITY FIX: Authenticate user BEFORE accepting connection
    user = await authenticate_websocket(token)
    if not user:
        # Close connection with policy violation code before accepting
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
        return
        
    # Only accept connection after successful authentication
    await websocket.accept()
    
    # Connect user
    await manager.connect_authenticated_user(
        websocket, 
        str(user.id), 
        str(user.organization_id)
    )
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "ping":
                await manager.handle_ping(str(user.id))
            elif message_type == "subscribe":
                # Handle subscription requests
                topic = data.get("topic")
                logger.info(f"User {user.id} subscribed to {topic}")
            elif message_type == "unsubscribe":
                # Handle unsubscription requests
                topic = data.get("topic")
                logger.info(f"User {user.id} unsubscribed from {topic}")
            else:
                # Handle other message types
                logger.warning(f"Unknown message type: {message_type}")
                
    except WebSocketDisconnect:
        manager.disconnect(str(user.id))
    except Exception as e:
        logger.error(f"WebSocket error for user {user.id}: {e}")
        manager.disconnect(str(user.id))


# Background task to clean up stale connections
async def cleanup_task():
    """Background task to clean up stale connections."""
    while True:
        await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
        await manager.cleanup_stale_connections()