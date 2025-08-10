"""
WebSocket endpoints for real-time communication

Provides WebSocket connections for dashboard updates.
"""

from fastapi import APIRouter, WebSocket, Query
from typing import Optional

from src.services.websocket.websocket_manager import websocket_endpoint

router = APIRouter()


@router.websocket("/ws")
async def websocket_connection(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token")
):
    """
    WebSocket endpoint for real-time updates.
    
    Requires JWT token as query parameter for authentication.
    
    Message types:
    - ping: Keep-alive ping
    - pong: Response to ping
    - metric_update: Real-time metric updates
    - conversation_update: Conversation state changes
    - connection: Connection status updates
    
    Example connection:
    ws://localhost:8000/api/v1/ws?token=<jwt_token>
    """
    await websocket_endpoint(websocket, token)