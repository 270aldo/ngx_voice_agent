"""
Metrics Collector

Collects and tracks metrics, analytics, and ML events.
Single responsibility: Metrics and analytics tracking.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and tracks conversation metrics and analytics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        # Metrics storage
        self.conversation_metrics = defaultdict(dict)
        self.ml_events = []
        self.performance_metrics = defaultdict(list)
        self.business_metrics = defaultdict(float)
        
        # ML Pipeline tracking
        self.ml_pipeline = None
        self._initialize_ml_pipeline()
        
        # Counters
        self.counters = defaultdict(int)
        
        # Time tracking
        self.timers = defaultdict(list)
    
    def _initialize_ml_pipeline(self):
        """Initialize ML Pipeline for tracking."""
        try:
            from src.services.ml_pipeline.ml_pipeline_service import MLPipelineService
            self.ml_pipeline = MLPipelineService()
        except ImportError:
            logger.warning("ML Pipeline not available for metrics tracking")
            self.ml_pipeline = None
    
    async def track_conversation_event(
        self,
        conversation_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> None:
        """
        Track a conversation event.
        
        Args:
            conversation_id: Conversation identifier
            event_type: Type of event
            event_data: Event data
        """
        try:
            # Create event record
            event = {
                "conversation_id": conversation_id,
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": event_data
            }
            
            # Store in conversation metrics
            if conversation_id not in self.conversation_metrics:
                self.conversation_metrics[conversation_id] = {
                    "events": [],
                    "start_time": datetime.utcnow(),
                    "metrics": {}
                }
            
            self.conversation_metrics[conversation_id]["events"].append(event)
            
            # Update counters
            self.counters[f"event_{event_type}"] += 1
            
            # Track with ML Pipeline if available
            if self.ml_pipeline and event_type in ["message_exchange", "pattern_detected"]:
                await self._track_ml_event(conversation_id, event_type, event_data)
            
            logger.debug(f"Tracked event {event_type} for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Failed to track conversation event: {e}")
    
    async def track_message_exchange(
        self,
        conversation_id: str,
        user_message: str,
        assistant_response: str,
        analysis: Dict[str, Any]
    ) -> None:
        """
        Track a message exchange.
        
        Args:
            conversation_id: Conversation identifier
            user_message: User's message
            assistant_response: Assistant's response
            analysis: Message analysis results
        """
        event_data = {
            "user_message": user_message[:500],  # Truncate for storage
            "assistant_response": assistant_response[:500],
            "intent": analysis.get("intent", {}).get("type"),
            "sentiment": analysis.get("nlp", {}).get("sentiment"),
            "confidence": analysis.get("confidence", 0.0),
            "response_time_ms": analysis.get("response_time_ms")
        }
        
        await self.track_conversation_event(
            conversation_id,
            "message_exchange",
            event_data
        )
        
        # Update message count
        self.counters["total_messages"] += 1
        
        # Track sentiment distribution
        sentiment = event_data.get("sentiment", "neutral")
        self.counters[f"sentiment_{sentiment}"] += 1
    
    async def track_ml_prediction(
        self,
        conversation_id: str,
        prediction_type: str,
        prediction_value: Any,
        confidence: float
    ) -> None:
        """
        Track ML prediction.
        
        Args:
            conversation_id: Conversation identifier
            prediction_type: Type of prediction
            prediction_value: Predicted value
            confidence: Confidence score
        """
        event_data = {
            "prediction_type": prediction_type,
            "prediction_value": prediction_value,
            "confidence": confidence
        }
        
        await self.track_conversation_event(
            conversation_id,
            "ml_prediction",
            event_data
        )
        
        # Track ML accuracy metrics
        self.ml_events.append({
            "conversation_id": conversation_id,
            "type": prediction_type,
            "value": prediction_value,
            "confidence": confidence,
            "timestamp": datetime.utcnow()
        })
    
    async def track_pattern_detection(
        self,
        conversation_id: str,
        pattern_type: str,
        pattern_data: Dict[str, Any]
    ) -> None:
        """
        Track pattern detection.
        
        Args:
            conversation_id: Conversation identifier
            pattern_type: Type of pattern detected
            pattern_data: Pattern details
        """
        event_data = {
            "pattern_type": pattern_type,
            "confidence": pattern_data.get("confidence", 0.0),
            "details": pattern_data
        }
        
        await self.track_conversation_event(
            conversation_id,
            "pattern_detected",
            event_data
        )
        
        # Update pattern counters
        self.counters[f"pattern_{pattern_type}"] += 1
    
    async def track_conversion_event(
        self,
        conversation_id: str,
        conversion_type: str,
        value: Optional[float] = None
    ) -> None:
        """
        Track conversion event.
        
        Args:
            conversation_id: Conversation identifier
            conversion_type: Type of conversion
            value: Optional conversion value
        """
        event_data = {
            "conversion_type": conversion_type,
            "value": value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.track_conversation_event(
            conversation_id,
            "conversion",
            event_data
        )
        
        # Update business metrics
        self.counters["total_conversions"] += 1
        self.counters[f"conversion_{conversion_type}"] += 1
        
        if value:
            self.business_metrics["total_revenue"] += value
            self.business_metrics[f"revenue_{conversion_type}"] += value
    
    def track_performance_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "ms"
    ) -> None:
        """
        Track performance metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement
        """
        self.performance_metrics[metric_name].append({
            "value": value,
            "unit": unit,
            "timestamp": datetime.utcnow()
        })
        
        # Keep only last 1000 entries per metric
        if len(self.performance_metrics[metric_name]) > 1000:
            self.performance_metrics[metric_name] = self.performance_metrics[metric_name][-1000:]
    
    def start_timer(self, timer_name: str) -> str:
        """
        Start a timer.
        
        Args:
            timer_name: Name of the timer
            
        Returns:
            Timer ID
        """
        timer_id = f"{timer_name}_{datetime.utcnow().timestamp()}"
        self.timers[timer_id] = datetime.utcnow()
        return timer_id
    
    def end_timer(self, timer_id: str) -> Optional[float]:
        """
        End a timer and get duration.
        
        Args:
            timer_id: Timer identifier
            
        Returns:
            Duration in milliseconds or None if timer not found
        """
        if timer_id not in self.timers:
            return None
        
        start_time = self.timers[timer_id]
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Clean up timer
        del self.timers[timer_id]
        
        # Extract metric name from timer_id
        metric_name = timer_id.rsplit("_", 1)[0]
        self.track_performance_metric(metric_name, duration, "ms")
        
        return duration
    
    async def _track_ml_event(
        self,
        conversation_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> None:
        """Track event with ML Pipeline."""
        if not self.ml_pipeline:
            return
        
        try:
            await self.ml_pipeline.track_event(
                conversation_id=conversation_id,
                event_type=event_type,
                event_data=event_data
            )
        except Exception as e:
            logger.error(f"Failed to track ML event: {e}")
    
    def get_conversation_metrics(
        self,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        Get metrics for a specific conversation.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Conversation metrics
        """
        if conversation_id not in self.conversation_metrics:
            return {}
        
        metrics = self.conversation_metrics[conversation_id]
        
        # Calculate derived metrics
        if metrics.get("events"):
            metrics["event_count"] = len(metrics["events"])
            metrics["duration"] = (
                datetime.utcnow() - metrics["start_time"]
            ).total_seconds()
            
            # Calculate message velocity
            message_events = [
                e for e in metrics["events"]
                if e["event_type"] == "message_exchange"
            ]
            if message_events:
                metrics["message_count"] = len(message_events)
                metrics["avg_response_time"] = sum(
                    e["data"].get("response_time_ms", 0)
                    for e in message_events
                ) / len(message_events)
        
        return metrics
    
    def get_aggregate_metrics(self) -> Dict[str, Any]:
        """Get aggregate metrics across all conversations."""
        total_conversations = len(self.conversation_metrics)
        
        if total_conversations == 0:
            return {
                "total_conversations": 0,
                "total_messages": 0,
                "conversion_rate": 0.0
            }
        
        # Calculate aggregate metrics
        total_messages = self.counters["total_messages"]
        total_conversions = self.counters["total_conversions"]
        
        aggregate = {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_conversions": total_conversions,
            "conversion_rate": total_conversions / total_conversations,
            "avg_messages_per_conversation": total_messages / total_conversations,
            "sentiment_distribution": {
                "positive": self.counters["sentiment_positive"],
                "neutral": self.counters["sentiment_neutral"],
                "negative": self.counters["sentiment_negative"]
            },
            "pattern_counts": {
                k.replace("pattern_", ""): v
                for k, v in self.counters.items()
                if k.startswith("pattern_")
            },
            "revenue_metrics": {
                "total": self.business_metrics.get("total_revenue", 0.0),
                "average_per_conversion": (
                    self.business_metrics.get("total_revenue", 0.0) / total_conversions
                    if total_conversions > 0 else 0.0
                )
            }
        }
        
        # Add performance metrics
        if self.performance_metrics:
            perf_summary = {}
            for metric_name, values in self.performance_metrics.items():
                if values:
                    recent_values = [v["value"] for v in values[-100:]]
                    perf_summary[metric_name] = {
                        "avg": sum(recent_values) / len(recent_values),
                        "min": min(recent_values),
                        "max": max(recent_values),
                        "count": len(values)
                    }
            aggregate["performance"] = perf_summary
        
        return aggregate
    
    def get_ml_metrics(self) -> Dict[str, Any]:
        """Get ML-specific metrics."""
        if not self.ml_events:
            return {
                "total_predictions": 0,
                "avg_confidence": 0.0
            }
        
        total_predictions = len(self.ml_events)
        avg_confidence = sum(e["confidence"] for e in self.ml_events) / total_predictions
        
        # Group by prediction type
        by_type = defaultdict(list)
        for event in self.ml_events:
            by_type[event["type"]].append(event["confidence"])
        
        type_metrics = {}
        for pred_type, confidences in by_type.items():
            type_metrics[pred_type] = {
                "count": len(confidences),
                "avg_confidence": sum(confidences) / len(confidences),
                "min_confidence": min(confidences),
                "max_confidence": max(confidences)
            }
        
        return {
            "total_predictions": total_predictions,
            "avg_confidence": avg_confidence,
            "by_type": type_metrics,
            "recent_predictions": self.ml_events[-10:]  # Last 10 predictions
        }
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for analysis or persistence."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "aggregate": self.get_aggregate_metrics(),
            "ml_metrics": self.get_ml_metrics(),
            "counters": dict(self.counters),
            "business_metrics": dict(self.business_metrics),
            "conversation_count": len(self.conversation_metrics)
        }
    
    def reset_metrics(self, conversation_id: Optional[str] = None) -> None:
        """
        Reset metrics.
        
        Args:
            conversation_id: Optional specific conversation to reset
        """
        if conversation_id:
            # Reset specific conversation
            if conversation_id in self.conversation_metrics:
                del self.conversation_metrics[conversation_id]
        else:
            # Reset all metrics
            self.conversation_metrics.clear()
            self.ml_events.clear()
            self.performance_metrics.clear()
            self.business_metrics.clear()
            self.counters.clear()
            self.timers.clear()
            
        logger.info(f"Metrics reset {'for conversation ' + conversation_id if conversation_id else 'globally'}")