"""
Dashboard API endpoints for NGX Command Center

Provides real-time metrics, analytics, and insights for the dashboard.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from src.core.auth.deps import get_current_user
from src.models.user import User
from src.services.analytics.metrics_service import MetricsService
from src.services.conversation.tracker import ConversationTracker
from src.integrations.supabase.client import supabase_client
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)
router = APIRouter()


class DashboardMetrics(BaseModel):
    """Dashboard metrics response model"""
    conversions: Dict[str, Any]
    active_leads: Dict[str, Any]
    revenue: Dict[str, Any]
    response_time: Dict[str, Any]
    conversations_count: Dict[str, Any]
    satisfaction_score: Dict[str, Any]
    timestamp: datetime


class ConversionFunnel(BaseModel):
    """Conversion funnel data"""
    stages: List[Dict[str, Any]]
    total_visitors: int
    conversion_rate: float


class LiveConversation(BaseModel):
    """Live conversation summary"""
    id: str
    customer_name: str
    status: str
    duration_seconds: int
    emotional_state: str
    stage: str
    last_message: str
    started_at: datetime


class RecentActivity(BaseModel):
    """Recent activity item"""
    id: str
    timestamp: datetime
    event_type: str
    description: str
    customer_name: Optional[str]
    metadata: Optional[Dict[str, Any]]


@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    timeframe: str = Query("today", description="Timeframe: today, week, month"),
    current_user: User = Depends(get_current_user)
) -> DashboardMetrics:
    """
    Get main dashboard metrics.
    
    Returns conversion rates, active leads, revenue, and other KPIs.
    """
    try:
        # Calculate time range
        now = datetime.utcnow()
        if timeframe == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == "week":
            start_date = now - timedelta(days=7)
        elif timeframe == "month":
            start_date = now - timedelta(days=30)
        else:
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get metrics from analytics service
        metrics_service = MetricsService()
        
        # Get conversion metrics
        conversions = await metrics_service.get_conversion_metrics(
            organization_id=current_user.organization_id,
            start_date=start_date,
            end_date=now
        )
        
        # Get active leads
        active_leads = await metrics_service.get_active_leads_count(
            organization_id=current_user.organization_id
        )
        
        # Get revenue metrics
        revenue = await metrics_service.get_revenue_metrics(
            organization_id=current_user.organization_id,
            start_date=start_date,
            end_date=now
        )
        
        # Get response time metrics
        response_time = await metrics_service.get_response_time_metrics(
            organization_id=current_user.organization_id,
            start_date=start_date,
            end_date=now
        )
        
        # Get conversation count
        conversations_count = await metrics_service.get_conversations_count(
            organization_id=current_user.organization_id,
            start_date=start_date,
            end_date=now
        )
        
        # Get satisfaction score
        satisfaction_score = await metrics_service.get_satisfaction_score(
            organization_id=current_user.organization_id,
            start_date=start_date,
            end_date=now
        )
        
        return DashboardMetrics(
            conversions=conversions,
            active_leads=active_leads,
            revenue=revenue,
            response_time=response_time,
            conversations_count=conversations_count,
            satisfaction_score=satisfaction_score,
            timestamp=now
        )
        
    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving metrics")


@router.get("/funnel", response_model=ConversionFunnel)
async def get_conversion_funnel(
    timeframe: str = Query("today", description="Timeframe: today, week, month"),
    current_user: User = Depends(get_current_user)
) -> ConversionFunnel:
    """
    Get conversion funnel data.
    
    Shows the progression of visitors through different stages.
    """
    try:
        metrics_service = MetricsService()
        
        # Calculate time range
        now = datetime.utcnow()
        if timeframe == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == "week":
            start_date = now - timedelta(days=7)
        else:
            start_date = now - timedelta(days=30)
        
        # Get funnel data
        funnel_data = await metrics_service.get_conversion_funnel(
            organization_id=current_user.organization_id,
            start_date=start_date,
            end_date=now
        )
        
        return ConversionFunnel(
            stages=funnel_data["stages"],
            total_visitors=funnel_data["total_visitors"],
            conversion_rate=funnel_data["conversion_rate"]
        )
        
    except Exception as e:
        logger.error(f"Error getting conversion funnel: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving funnel data")


@router.get("/conversations/live", response_model=List[LiveConversation])
async def get_live_conversations(
    limit: int = Query(10, description="Number of conversations to return"),
    current_user: User = Depends(get_current_user)
) -> List[LiveConversation]:
    """
    Get currently active conversations.
    
    Returns real-time data about ongoing conversations.
    """
    try:
        tracker = ConversationTracker()
        
        # Get active conversations
        active_conversations = await tracker.get_active_conversations(
            organization_id=current_user.organization_id,
            limit=limit
        )
        
        # Transform to response model
        live_conversations = []
        for conv in active_conversations:
            live_conversations.append(LiveConversation(
                id=conv["id"],
                customer_name=conv["customer_name"],
                status=conv["status"],
                duration_seconds=conv["duration_seconds"],
                emotional_state=conv["emotional_state"],
                stage=conv["stage"],
                last_message=conv["last_message"],
                started_at=conv["started_at"]
            ))
        
        return live_conversations
        
    except Exception as e:
        logger.error(f"Error getting live conversations: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving conversations")


@router.get("/activity/recent", response_model=List[RecentActivity])
async def get_recent_activity(
    limit: int = Query(20, description="Number of activities to return"),
    current_user: User = Depends(get_current_user)
) -> List[RecentActivity]:
    """
    Get recent activity feed.
    
    Shows latest events, conversions, and significant actions.
    """
    try:
        supabase = supabase_client
        
        # Query recent activities
        response = supabase.table("activity_logs").select("*").eq(
            "organization_id", current_user.organization_id
        ).order("created_at", desc=True).limit(limit).execute()
        
        # Transform to response model
        activities = []
        for item in response.data:
            activities.append(RecentActivity(
                id=item["id"],
                timestamp=datetime.fromisoformat(item["created_at"]),
                event_type=item["event_type"],
                description=item["description"],
                customer_name=item.get("customer_name"),
                metadata=item.get("metadata", {})
            ))
        
        return activities
        
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving activity")


@router.get("/analytics/summary")
async def get_analytics_summary(
    timeframe: str = Query("week", description="Timeframe for comparison"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get comprehensive analytics summary for AI Assistant.
    
    This endpoint provides data formatted for conversational queries.
    """
    try:
        metrics_service = MetricsService()
        
        # Get various analytics
        summary = await metrics_service.get_analytics_summary(
            organization_id=current_user.organization_id,
            timeframe=timeframe
        )
        
        # Format for AI Assistant consumption
        return {
            "summary": summary,
            "insights": await metrics_service.generate_insights(summary),
            "recommendations": await metrics_service.get_recommendations(summary),
            "trends": await metrics_service.analyze_trends(summary)
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics summary: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving analytics")


@router.post("/query")
async def query_analytics(
    query: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Natural language query endpoint for AI Assistant.
    
    Processes conversational queries about metrics and returns structured data.
    """
    try:
        metrics_service = MetricsService()
        
        # Process natural language query
        result = await metrics_service.process_nl_query(
            query=query,
            organization_id=current_user.organization_id
        )
        
        return {
            "query": query,
            "interpretation": result["interpretation"],
            "data": result["data"],
            "visualization_type": result["visualization_type"],
            "response": result["response"]
        }
        
    except Exception as e:
        logger.error(f"Error processing analytics query: {e}")
        raise HTTPException(status_code=500, detail="Error processing query")