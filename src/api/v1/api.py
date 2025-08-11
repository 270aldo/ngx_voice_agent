"""
Main API router for NGX Voice Agent

Combines all API endpoints into a single router.
"""

from fastapi import APIRouter

from src.api.v1.endpoints import (
    auth,
    dashboard,
    websocket,
    conversations
)

api_router = APIRouter()

# Authentication endpoints
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

# Dashboard endpoints
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"]
)

# WebSocket endpoint
api_router.include_router(
    websocket.router,
    tags=["websocket"]
)

# Conversations endpoints
api_router.include_router(
    conversations.router,
    prefix="/conversations",
    tags=["conversations"]
)

# Agent configuration endpoints (to be implemented)
# api_router.include_router(
#     agents.router,
#     prefix="/agents",
#     tags=["agents"]
# )

# Analytics endpoints (to be implemented)
# api_router.include_router(
#     analytics.router,
#     prefix="/analytics",
#     tags=["analytics"]
# )