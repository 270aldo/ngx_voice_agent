"""
Security management API endpoints.

This module provides endpoints for managing security features including
JWT rotation, security events monitoring, and security configuration.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from src.auth.auth_dependencies import get_current_user, has_admin_role
from src.auth.auth_utils import TokenData
from src.services.jwt_rotation_service import get_jwt_rotation_service
from src.integrations.supabase.client import supabase_client

import logging

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/security",
    tags=["security"],
    responses={
        403: {
            "model": dict,
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "error": {
                            "code": "FORBIDDEN",
                            "message": "Access denied. Admin role required."
                        }
                    }
                }
            }
        }
    }
)


@router.get("/jwt/status")
async def get_jwt_rotation_status(
    current_user: TokenData = Depends(has_admin_role)
) -> Dict[str, Any]:
    """
    Get current JWT rotation status.
    
    Returns:
        Dict containing rotation status information
    """
    try:
        rotation_service = await get_jwt_rotation_service()
        status = rotation_service.get_rotation_status()
        
        return {
            "success": True,
            "data": status,
            "error": None
        }
    except Exception as e:
        logger.error(f"Error getting JWT rotation status: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": f"Error getting rotation status: {str(e)}"
                }
            }
        )


@router.post("/jwt/rotate")
async def rotate_jwt_secret(
    background_tasks: BackgroundTasks,
    force: bool = False,
    current_user: TokenData = Depends(has_admin_role)
) -> Dict[str, Any]:
    """
    Trigger JWT secret rotation.
    
    Args:
        force: Force rotation even if not due
        
    Returns:
        Dict with rotation result
    """
    try:
        rotation_service = await get_jwt_rotation_service()
        
        # Check if rotation is needed
        if not force and not await rotation_service.check_rotation_needed():
            return {
                "success": True,
                "data": {
                    "rotated": False,
                    "message": "Rotation not needed yet",
                    "next_rotation": rotation_service._next_rotation.isoformat() if rotation_service._next_rotation else None
                },
                "error": None
            }
        
        # Perform rotation
        rotated = await rotation_service.rotate_secret(force=force)
        
        if rotated:
            # Schedule cleanup of expired secrets in background
            background_tasks.add_task(rotation_service.cleanup_expired_secrets)
            
            return {
                "success": True,
                "data": {
                    "rotated": True,
                    "message": "JWT secret rotated successfully",
                    "next_rotation": rotation_service._next_rotation.isoformat() if rotation_service._next_rotation else None
                },
                "error": None
            }
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "ROTATION_FAILED",
                        "message": "Failed to rotate JWT secret"
                    }
                }
            )
            
    except Exception as e:
        logger.error(f"Error rotating JWT secret: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": f"Error during rotation: {str(e)}"
                }
            }
        )


@router.get("/events/recent")
async def get_recent_security_events(
    limit: int = 100,
    event_type: Optional[str] = None,
    current_user: TokenData = Depends(has_admin_role)
) -> Dict[str, Any]:
    """
    Get recent security events.
    
    Args:
        limit: Maximum number of events to return
        event_type: Filter by event type
        
    Returns:
        Dict with list of security events
    """
    try:
        supabase = supabase_client
        
        # Build query
        query = supabase.table("security_events").select("*")
        
        if event_type:
            query = query.eq("event_type", event_type)
            
        # Order by timestamp and limit
        query = query.order("timestamp", desc=True).limit(limit)
        
        result = await query.execute()
        
        return {
            "success": True,
            "data": {
                "events": result.data if result.data else [],
                "count": len(result.data) if result.data else 0
            },
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Error fetching security events: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": f"Error fetching events: {str(e)}"
                }
            }
        )


@router.get("/events/stats")
async def get_security_stats(
    days: int = 7,
    current_user: TokenData = Depends(has_admin_role)
) -> Dict[str, Any]:
    """
    Get security statistics for the specified period.
    
    Args:
        days: Number of days to analyze
        
    Returns:
        Dict with security statistics
    """
    try:
        supabase = supabase_client
        
        # Get events from the last N days
        from_date = datetime.utcnow() - timedelta(days=days)
        
        result = await supabase.table("security_events")\
            .select("event_type, success")\
            .gte("timestamp", from_date.isoformat())\
            .execute()
        
        if not result.data:
            return {
                "success": True,
                "data": {
                    "period_days": days,
                    "total_events": 0,
                    "events_by_type": {},
                    "success_rate": 1.0,
                    "failed_events": []
                },
                "error": None
            }
        
        # Calculate statistics
        events_by_type = {}
        failed_events = []
        total_success = 0
        
        for event in result.data:
            event_type = event["event_type"]
            success = event["success"]
            
            if event_type not in events_by_type:
                events_by_type[event_type] = {"total": 0, "success": 0, "failed": 0}
                
            events_by_type[event_type]["total"] += 1
            
            if success:
                events_by_type[event_type]["success"] += 1
                total_success += 1
            else:
                events_by_type[event_type]["failed"] += 1
                failed_events.append(event)
        
        total_events = len(result.data)
        success_rate = total_success / total_events if total_events > 0 else 1.0
        
        return {
            "success": True,
            "data": {
                "period_days": days,
                "total_events": total_events,
                "events_by_type": events_by_type,
                "success_rate": success_rate,
                "failed_events": failed_events[:10]  # Limit to 10 most recent failures
            },
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Error calculating security stats: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": f"Error calculating stats: {str(e)}"
                }
            }
        )


@router.get("/jwt/history")
async def get_jwt_rotation_history(
    limit: int = 50,
    current_user: TokenData = Depends(has_admin_role)
) -> Dict[str, Any]:
    """
    Get JWT rotation history.
    
    Args:
        limit: Maximum number of records to return
        
    Returns:
        Dict with rotation history
    """
    try:
        supabase = supabase_client
        
        result = await supabase.table("jwt_rotation_history")\
            .select("*")\
            .order("rotation_timestamp", desc=True)\
            .limit(limit)\
            .execute()
        
        return {
            "success": True,
            "data": {
                "history": result.data if result.data else [],
                "count": len(result.data) if result.data else 0
            },
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Error fetching rotation history: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": f"Error fetching history: {str(e)}"
                }
            }
        )