"""
WebSocket Session Manager for enhanced security.

Provides token revocation and session management capabilities
for WebSocket connections.
"""

import asyncio
import time
from typing import Dict, Set, Optional
from datetime import datetime, timedelta
import logging

from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)


class WebSocketSessionManager:
    """Manages WebSocket sessions with token revocation support."""
    
    def __init__(self):
        # Revoked tokens (JWT IDs) with expiration times
        self.revoked_tokens: Dict[str, float] = {}
        # Active sessions by user_id -> {jti, last_activity, websocket_id}
        self.active_sessions: Dict[str, dict] = {}
        # Session cleanup interval (seconds)
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
        
    async def is_token_revoked(self, jti: str) -> bool:
        """Check if a token is revoked."""
        # Clean up expired revoked tokens periodically
        await self._cleanup_expired_revoked_tokens()
        
        return jti in self.revoked_tokens
    
    async def revoke_token(self, jti: str, expires_at: float):
        """Revoke a token by its JWT ID."""
        self.revoked_tokens[jti] = expires_at
        
        logger.info("Token revoked",
                   extra={
                       "security_event": "token_revoked",
                       "jti": jti,
                       "expires_at": expires_at
                   })
    
    async def revoke_all_user_sessions(self, user_id: str):
        """Revoke all active sessions for a user."""
        if user_id in self.active_sessions:
            session_info = self.active_sessions[user_id]
            jti = session_info.get("jti")
            expires_at = session_info.get("expires_at", time.time() + 3600)
            
            if jti:
                await self.revoke_token(jti, expires_at)
            
            del self.active_sessions[user_id]
            
            logger.info("All user sessions revoked",
                       extra={
                           "security_event": "user_sessions_revoked",
                           "user_id": user_id
                       })
    
    async def register_session(
        self, 
        user_id: str, 
        jti: str, 
        expires_at: float,
        websocket_id: str
    ):
        """Register a new WebSocket session."""
        self.active_sessions[user_id] = {
            "jti": jti,
            "expires_at": expires_at,
            "websocket_id": websocket_id,
            "last_activity": time.time()
        }
        
        logger.debug("WebSocket session registered",
                    extra={
                        "user_id": user_id,
                        "websocket_id": websocket_id
                    })
    
    async def update_session_activity(self, user_id: str):
        """Update last activity for a session."""
        if user_id in self.active_sessions:
            self.active_sessions[user_id]["last_activity"] = time.time()
    
    async def remove_session(self, user_id: str):
        """Remove a WebSocket session."""
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
            
            logger.debug("WebSocket session removed",
                        extra={"user_id": user_id})
    
    async def validate_session_token(self, user_id: str, jti: str) -> bool:
        """Validate that a session token is still valid."""
        # Check if token is globally revoked
        if await self.is_token_revoked(jti):
            return False
        
        # Check if session exists and matches
        session_info = self.active_sessions.get(user_id)
        if not session_info:
            return False
        
        if session_info.get("jti") != jti:
            return False
        
        # Check if session has expired
        expires_at = session_info.get("expires_at", 0)
        if time.time() >= expires_at:
            await self.remove_session(user_id)
            return False
        
        # Update activity
        await self.update_session_activity(user_id)
        return True
    
    async def _cleanup_expired_revoked_tokens(self):
        """Clean up expired revoked tokens."""
        now = time.time()
        
        # Only run cleanup every cleanup_interval seconds
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        expired_tokens = [
            jti for jti, expires_at in self.revoked_tokens.items()
            if now >= expires_at
        ]
        
        for jti in expired_tokens:
            del self.revoked_tokens[jti]
        
        self.last_cleanup = now
        
        if expired_tokens:
            logger.debug(f"Cleaned up {len(expired_tokens)} expired revoked tokens")
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        now = time.time()
        expired_sessions = []
        
        for user_id, session_info in self.active_sessions.items():
            expires_at = session_info.get("expires_at", 0)
            last_activity = session_info.get("last_activity", 0)
            
            # Session expired or inactive for too long (1 hour)
            if now >= expires_at or (now - last_activity) > 3600:
                expired_sessions.append(user_id)
        
        for user_id in expired_sessions:
            await self.remove_session(user_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired WebSocket sessions")


# Global session manager instance
session_manager = WebSocketSessionManager()