"""
ML Event Tracker - Tracks all ML-related events in the pipeline.

Responsible for:
- Recording predictions
- Tracking model performance
- Monitoring drift
- Event streaming
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from src.integrations.supabase.resilient_client import resilient_supabase_client as supabase_client

logger = logging.getLogger(__name__)


class MLEventTracker:
    """
    Tracks and stores all ML-related events for analysis and monitoring.
    """
    
    def __init__(self):
        """Initialize the ML Event Tracker."""
        self.supabase = supabase_client
        
        # Event types we track
        self.event_types = {
            "prediction": "ML prediction made",
            "outcome": "Conversation outcome recorded",
            "drift_detected": "Model drift detected",
            "model_update": "Model updated",
            "experiment_assigned": "A/B test variant assigned",
            "pattern_detected": "Pattern recognized",
            "feedback_received": "User feedback received",
            "error": "ML pipeline error"
        }
        
        # Drift detection thresholds
        self.drift_thresholds = {
            "accuracy_drop": 0.05,  # 5% drop in accuracy
            "confidence_drop": 0.10,  # 10% drop in confidence
            "distribution_shift": 0.15,  # 15% shift in predictions
            "latency_increase": 1.5  # 50% increase in latency
        }
        
        # Performance baselines (will be updated dynamically)
        self.performance_baselines = {
            "objection_accuracy": 0.85,
            "needs_accuracy": 0.80,
            "conversion_accuracy": 0.75,
            "avg_latency_ms": 200
        }
    
    async def track_prediction_event(
        self,
        conversation_id: str,
        event_type: str,
        predictions: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Track a prediction event.
        
        Args:
            conversation_id: ID of the conversation
            event_type: Type of prediction event
            predictions: Prediction results
            metadata: Additional metadata
            
        Returns:
            Event ID
        """
        try:
            event_id = str(uuid.uuid4())
            
            # Prepare event data
            event_data = {
                "id": event_id,
                "conversation_id": conversation_id,
                "event_type": event_type,
                "event_category": "prediction",
                "timestamp": datetime.now().isoformat(),
                "data": json.dumps({
                    "predictions": predictions,
                    "metadata": metadata or {}
                }),
                "created_at": datetime.now().isoformat()
            }
            
            # Check for drift before storing
            drift_analysis = await self._check_for_drift(predictions)
            if drift_analysis["drift_detected"]:
                event_data["drift_alert"] = json.dumps(drift_analysis)
                
                # Create separate drift event
                await self._create_drift_alert(conversation_id, drift_analysis)
            
            # Store event
            await self.supabase.table("ml_tracking_events").insert(event_data).execute()
            
            # Update real-time metrics
            await self._update_realtime_metrics(event_type, predictions)
            
            return event_id
            
        except Exception as e:
            logger.error(f"Error tracking prediction event: {e}")
            return ""
    
    async def track_outcome_event(
        self,
        conversation_id: str,
        outcome: str,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Track conversation outcome event.
        
        Args:
            conversation_id: ID of the conversation
            outcome: Conversation outcome
            metrics: Performance metrics
        """
        try:
            event_data = {
                "id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "event_type": "conversation_outcome",
                "event_category": "outcome",
                "timestamp": datetime.now().isoformat(),
                "data": json.dumps({
                    "outcome": outcome,
                    "metrics": metrics,
                    "success": outcome in ["completed", "qualified"]
                }),
                "created_at": datetime.now().isoformat()
            }
            
            # Store event
            await self.supabase.table("ml_tracking_events").insert(event_data).execute()
            
            # Update outcome statistics
            await self._update_outcome_stats(outcome, metrics)
            
        except Exception as e:
            logger.error(f"Error tracking outcome event: {e}")
    
    async def track_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        conversation_id: Optional[str] = None
    ) -> str:
        """
        Generic method to track any ML-related event.
        
        Args:
            event_type: Type of event (message_exchange, pattern_detected, etc.)
            event_data: Event data dictionary
            conversation_id: Optional conversation ID
            
        Returns:
            Event ID
        """
        try:
            event_id = str(uuid.uuid4())
            
            # Prepare event data
            event_record = {
                "id": event_id,
                "conversation_id": conversation_id,
                "event_type": event_type,
                "event_category": "general",
                "timestamp": datetime.now().isoformat(),
                "data": json.dumps(event_data),
                "created_at": datetime.now().isoformat()
            }
            
            # Store event
            await self.supabase.table("ml_tracking_events").insert(event_record).execute()
            
            logger.debug(f"Tracked {event_type} event for conversation {conversation_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Error tracking generic event {event_type}: {e}")
            return ""
    
    async def track_experiment_event(
        self,
        conversation_id: str,
        experiment_id: str,
        variant_id: str,
        event_data: Dict[str, Any]
    ) -> None:
        """
        Track A/B test experiment event.
        
        Args:
            conversation_id: ID of the conversation
            experiment_id: ID of the experiment
            variant_id: ID of the variant
            event_data: Event data
        """
        try:
            event = {
                "id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "event_type": "experiment_interaction",
                "event_category": "experiment",
                "timestamp": datetime.now().isoformat(),
                "data": json.dumps({
                    "experiment_id": experiment_id,
                    "variant_id": variant_id,
                    "event_data": event_data
                }),
                "created_at": datetime.now().isoformat()
            }
            
            await self.supabase.table("ml_tracking_events").insert(event).execute()
            
        except Exception as e:
            logger.error(f"Error tracking experiment event: {e}")
    
    async def get_event_stream(
        self,
        conversation_id: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get stream of ML events.
        
        Args:
            conversation_id: Filter by conversation ID
            event_types: Filter by event types
            since: Get events since this timestamp
            limit: Maximum number of events
            
        Returns:
            List of events
        """
        try:
            query = self.supabase.table("ml_tracking_events").select("*")
            
            if conversation_id:
                query = query.eq("conversation_id", conversation_id)
            
            if event_types:
                query = query.in_("event_type", event_types)
            
            if since:
                query = query.gte("timestamp", since.isoformat())
            
            query = query.order("timestamp", desc=True).limit(limit)
            
            response = await query.execute()
            
            # Parse JSON data fields
            events = []
            for event in response.data or []:
                if event.get("data"):
                    event["data"] = json.loads(event["data"])
                events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting event stream: {e}")
            return []
    
    async def get_drift_alerts(
        self,
        timeframe_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get recent drift alerts.
        
        Args:
            timeframe_hours: Hours to look back
            
        Returns:
            List of drift alerts
        """
        try:
            since = datetime.now() - timedelta(hours=timeframe_hours)
            
            response = await self.supabase.table("ml_tracking_events").select(
                "*"
            ).eq(
                "event_category", "drift"
            ).gte(
                "timestamp", since.isoformat()
            ).execute()
            
            alerts = []
            for event in response.data or []:
                if event.get("data"):
                    event["data"] = json.loads(event["data"])
                alerts.append(event)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting drift alerts: {e}")
            return []
    
    async def get_performance_metrics(
        self,
        model_type: str,
        timeframe_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get performance metrics for a model.
        
        Args:
            model_type: Type of model (objection, needs, conversion)
            timeframe_hours: Hours to look back
            
        Returns:
            Performance metrics
        """
        try:
            since = datetime.now() - timedelta(hours=timeframe_hours)
            
            # Get prediction events
            response = await self.supabase.table("ml_tracking_events").select(
                "data"
            ).eq(
                "event_category", "prediction"
            ).gte(
                "timestamp", since.isoformat()
            ).execute()
            
            # Extract metrics for the model type
            total_predictions = 0
            confidence_sum = 0
            latency_sum = 0
            
            for event in response.data or []:
                if not event.get("data"):
                    continue
                    
                data = json.loads(event["data"])
                predictions = data.get("predictions", {})
                
                if model_type in predictions:
                    total_predictions += 1
                    model_pred = predictions[model_type]
                    
                    if "confidence" in model_pred:
                        confidence_sum += model_pred["confidence"]
                    
                    if "metadata" in data and "latency_ms" in data["metadata"]:
                        latency_sum += data["metadata"]["latency_ms"]
            
            if total_predictions == 0:
                return {"error": "No predictions found"}
            
            return {
                "model_type": model_type,
                "timeframe_hours": timeframe_hours,
                "total_predictions": total_predictions,
                "avg_confidence": confidence_sum / total_predictions,
                "avg_latency_ms": latency_sum / total_predictions if latency_sum > 0 else 0,
                "predictions_per_hour": total_predictions / timeframe_hours
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    
    async def _check_for_drift(
        self,
        predictions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if predictions indicate model drift.
        
        Args:
            predictions: Current predictions
            
        Returns:
            Drift analysis results
        """
        drift_indicators = []
        drift_detected = False
        
        # Check confidence levels
        for model_type in ["objections", "needs", "conversion"]:
            if model_type in predictions:
                confidence = predictions[model_type].get("confidence", 1.0)
                baseline_key = f"{model_type.rstrip('s')}_accuracy"
                
                if baseline_key in self.performance_baselines:
                    baseline = self.performance_baselines[baseline_key]
                    if confidence < baseline - self.drift_thresholds["confidence_drop"]:
                        drift_indicators.append({
                            "type": "confidence_drop",
                            "model": model_type,
                            "current": confidence,
                            "baseline": baseline,
                            "drop": baseline - confidence
                        })
                        drift_detected = True
        
        return {
            "drift_detected": drift_detected,
            "indicators": drift_indicators,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _create_drift_alert(
        self,
        conversation_id: str,
        drift_analysis: Dict[str, Any]
    ) -> None:
        """
        Create a drift alert event.
        
        Args:
            conversation_id: ID of the conversation
            drift_analysis: Drift analysis results
        """
        try:
            event_data = {
                "id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "event_type": "drift_detected",
                "event_category": "drift",
                "timestamp": datetime.now().isoformat(),
                "data": json.dumps(drift_analysis),
                "severity": self._calculate_drift_severity(drift_analysis),
                "created_at": datetime.now().isoformat()
            }
            
            await self.supabase.table("ml_tracking_events").insert(event_data).execute()
            
            logger.warning(f"Drift detected: {drift_analysis}")
            
        except Exception as e:
            logger.error(f"Error creating drift alert: {e}")
    
    def _calculate_drift_severity(
        self,
        drift_analysis: Dict[str, Any]
    ) -> str:
        """
        Calculate severity of drift.
        
        Args:
            drift_analysis: Drift analysis results
            
        Returns:
            Severity level (low, medium, high)
        """
        indicators = drift_analysis.get("indicators", [])
        
        if not indicators:
            return "low"
        
        max_drop = max(ind.get("drop", 0) for ind in indicators)
        
        if max_drop > 0.20:
            return "high"
        elif max_drop > 0.10:
            return "medium"
        else:
            return "low"
    
    async def _update_realtime_metrics(
        self,
        event_type: str,
        predictions: Dict[str, Any]
    ) -> None:
        """
        Update real-time metrics cache.
        
        Args:
            event_type: Type of event
            predictions: Prediction data
        """
        # TODO: Implement real-time metrics update
        # This could use Redis or similar for fast access
        pass
    
    async def _update_outcome_stats(
        self,
        outcome: str,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Update outcome statistics.
        
        Args:
            outcome: Conversation outcome
            metrics: Performance metrics
        """
        # TODO: Implement outcome statistics update
        # This could aggregate success rates, conversion values, etc.
        pass