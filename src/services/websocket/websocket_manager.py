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
from .session_manager import session_manager

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
    """Authenticate WebSocket connection using JWT token with enhanced security."""
    try:
        # Decode and validate token using JWTHandler
        try:
            payload = JWTHandler.verify_token(token, token_type="access")
        except Exception as decode_error:
            logger.warning(f"WebSocket authentication failed - Invalid token: {decode_error}", 
                         extra={
                             "security_event": "websocket_auth_failure",
                             "reason": "invalid_token",
                             "token_preview": token[:10] + "..." if len(token) > 10 else "short_token"
                         })
            return None
        
        # Verify token is for WebSocket access (if type is specified)
        token_type = payload.get("type")
        if token_type and token_type != "access":
            logger.warning("WebSocket authentication failed - Wrong token type",
                         extra={
                             "security_event": "websocket_auth_failure", 
                             "reason": "wrong_token_type",
                             "token_type": token_type
                         })
            return None
        
        user_id = payload.get("sub")
        jti = payload.get("jti")  # JWT ID for session management
        
        if not user_id:
            logger.warning("WebSocket authentication failed - Missing user ID",
                         extra={"security_event": "websocket_auth_failure", "reason": "missing_user_id"})
            return None
        
        if not jti:
            logger.warning("WebSocket authentication failed - Missing JWT ID",
                         extra={"security_event": "websocket_auth_failure", "reason": "missing_jti"})
            return None
        
        # Check if token is revoked
        if await session_manager.is_token_revoked(jti):
            logger.warning("WebSocket authentication failed - Token revoked",
                         extra={
                             "security_event": "websocket_auth_failure",
                             "reason": "token_revoked",
                             "user_id": user_id,
                             "jti": jti
                         })
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
            logger.warning("WebSocket authentication failed - User not active",
                         extra={
                             "security_event": "websocket_auth_failure",
                             "reason": "user_not_active", 
                             "user_id": user_id
                         })
            return None
            
        # Register session in session manager
        expires_at = payload.get("exp", 0)
        websocket_id = str(uuid.uuid4())
        await session_manager.register_session(user_id, jti, expires_at, websocket_id)
        
        # Log successful authentication
        logger.info("WebSocket authentication successful",
                   extra={
                       "security_event": "websocket_auth_success",
                       "user_id": user_id,
                       "organization_id": user.organization_id,
                       "websocket_id": websocket_id
                   })
        
        # Store session info in user object for later use
        user.websocket_session = {
            "jti": jti,
            "websocket_id": websocket_id,
            "expires_at": expires_at
        }
            
        return user
        
    except (JWTError, Exception) as e:
        logger.error(f"WebSocket authentication error: {e}",
                    extra={
                        "security_event": "websocket_auth_error",
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
        return None


async def websocket_endpoint(websocket: WebSocket, token: str):
    """Main WebSocket endpoint handler with enhanced security."""
    # SECURITY: Rate limiting check for WebSocket connections
    client_ip = websocket.client.host if websocket.client else "unknown"
    
    # Basic rate limiting for WebSocket connections (100 attempts per hour per IP)
    if hasattr(manager, 'connection_attempts'):
        current_hour = datetime.utcnow().hour
        if client_ip not in manager.connection_attempts:
            manager.connection_attempts[client_ip] = {"hour": current_hour, "count": 0}
        
        attempt_data = manager.connection_attempts[client_ip]
        if attempt_data["hour"] != current_hour:
            # Reset for new hour
            attempt_data["hour"] = current_hour
            attempt_data["count"] = 0
        
        attempt_data["count"] += 1
        if attempt_data["count"] > 100:
            logger.warning(f"WebSocket rate limit exceeded for IP {client_ip}",
                         extra={"security_event": "websocket_rate_limit", "client_ip": client_ip})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Rate limit exceeded")
            return
    else:
        manager.connection_attempts = {}
    
    # SECURITY: Authenticate user BEFORE accepting connection
    user = await authenticate_websocket(token)
    if not user:
        # Close connection with policy violation code before accepting
        logger.warning(f"WebSocket connection rejected for IP {client_ip}",
                      extra={"security_event": "websocket_connection_rejected", "client_ip": client_ip})
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
            
            # Validate session on every message (security check)
            session_info = getattr(user, 'websocket_session', {})
            jti = session_info.get("jti")
            if jti and not await session_manager.validate_session_token(str(user.id), jti):
                logger.warning("WebSocket session validation failed - closing connection",
                             extra={
                                 "security_event": "websocket_session_invalid",
                                 "user_id": str(user.id),
                                 "jti": jti
                             })
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Session expired or revoked")
                break
            
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
        await session_manager.remove_session(str(user.id))
    except Exception as e:
        logger.error(f"WebSocket error for user {user.id}: {e}")
        manager.disconnect(str(user.id))
        await session_manager.remove_session(str(user.id))


# Background task to clean up stale connections
async def cleanup_task():
    """Background task to clean up stale connections and expired sessions."""
    while True:
        await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
        
        # Clean up stale WebSocket connections
        await manager.cleanup_stale_connections()
        
        # Clean up expired sessions
        await session_manager.cleanup_expired_sessions()
        
        logger.debug("WebSocket cleanup task completed")