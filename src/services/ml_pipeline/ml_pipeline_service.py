"""
ML Pipeline Service - Central orchestrator for all ML operations.

This service coordinates the entire ML pipeline including:
- Prediction capture and storage
- A/B test integration
- Pattern recognition
- Feedback loops
- Model updates
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import uuid
import json
from collections import defaultdict

from src.services.training.ml_prediction_service import MLPredictionService
from src.services.ml_pipeline.ml_event_tracker import MLEventTracker
from src.services.ml_pipeline.ml_feedback_loop import MLFeedbackLoop
from src.services.ml_pipeline.ml_metrics_aggregator import MLMetricsAggregator
from src.services.ml_pipeline.ml_model_updater import MLModelUpdater
from src.services.ml_pipeline.ml_drift_detector import MLDriftDetector
from src.services.ab_testing_framework import ABTestingFramework
from src.services.conversation_outcome_tracker import ConversationOutcomeTracker
from src.models.learning_models import AdaptiveLearningConfig
from src.integrations.supabase.resilient_client import resilient_supabase_client as supabase_client
from src.utils.async_task_manager import AsyncTaskManager, get_task_registry

logger = logging.getLogger(__name__)


class MLPipelineService:
    """
    Central ML Pipeline orchestrator that manages the complete ML lifecycle.
    """
    
    def __init__(self):
        """Initialize ML Pipeline components."""
        self.prediction_service = MLPredictionService()
        self.event_tracker = MLEventTracker()
        self.feedback_loop = MLFeedbackLoop()
        self.metrics_aggregator = MLMetricsAggregator()
        self.model_updater = MLModelUpdater()
        self.drift_detector = MLDriftDetector()
        self.ab_testing = ABTestingFramework(AdaptiveLearningConfig())
        self.outcome_tracker = ConversationOutcomeTracker()
        self.supabase = supabase_client
        
        # Pipeline configuration
        self.config = {
            "batch_size": 100,
            "update_frequency_hours": 24,
            "min_samples_for_update": 500,
            "confidence_threshold": 0.75,
            "pattern_detection_window_hours": 168,  # 7 days
            "ab_test_min_conversions": 100
        }
        
        # In-memory buffers for performance
        self.prediction_buffer = []
        self.event_buffer = []
        self.pattern_buffer = []
        
        # Task manager for background tasks
        self.task_manager: Optional[AsyncTaskManager] = None
        
        # Start async initialization
        asyncio.create_task(self._initialize_async())
    
    async def _initialize_async(self):
        """Async initialization including task manager setup."""
        try:
            # Get task manager from registry
            registry = get_task_registry()
            self.task_manager = await registry.register_service("ml_pipeline")
            
            # Start background tasks
            await self._start_background_tasks()
            
            logger.info("MLPipelineService async initialization complete")
        except Exception as e:
            logger.error(f"Failed to initialize MLPipelineService async: {e}")
    
    async def _start_background_tasks(self):
        """Start background processing tasks with proper management."""
        if not self.task_manager:
            logger.error("Task manager not initialized")
            return
        
        await self.task_manager.create_task(
            self._process_buffers_periodically(),
            name="process_buffers"
        )
        await self.task_manager.create_task(
            self._run_feedback_loop_periodically(),
            name="feedback_loop"
        )
        await self.task_manager.create_task(
            self._update_models_periodically(),
            name="update_models"
        )
        await self.task_manager.create_task(
            self._analyze_patterns_periodically(),
            name="analyze_patterns"
        )
    
    async def process_conversation_predictions(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any],
        predictions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process and store all ML predictions for a conversation turn.
        
        Args:
            conversation_id: Unique conversation identifier
            messages: Conversation messages
            context: Conversation context (customer data, phase, etc.)
            predictions: Pre-computed predictions (optional)
            
        Returns:
            Complete prediction results with tracking info
        """
        try:
            # Get or compute predictions
            if not predictions:
                predictions = await self._compute_all_predictions(messages, context)
            
            # Enhance predictions with A/B test variants if applicable
            predictions = await self._enhance_with_ab_testing(conversation_id, predictions, context)
            
            # Create tracking event
            event = {
                "id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat(),
                "predictions": predictions,
                "context": context,
                "message_count": len(messages)
            }
            
            # Add to buffer for batch processing
            self.prediction_buffer.append(event)
            
            # Process immediately if buffer is full
            if len(self.prediction_buffer) >= self.config["batch_size"]:
                await self._flush_prediction_buffer()
            
            # Track ML event
            await self.event_tracker.track_prediction_event(
                conversation_id=conversation_id,
                event_type="predictions_computed",
                predictions=predictions
            )
            
            # Track for drift detection
            await self._track_for_drift_detection(
                conversation_id=conversation_id,
                predictions=predictions,
                context=context,
                messages=messages
            )
            
            # Return enhanced predictions
            return {
                "predictions": predictions,
                "tracking_id": event["id"],
                "ab_variants": predictions.get("ab_variants", {}),
                "confidence_scores": self._extract_confidence_scores(predictions)
            }
            
        except Exception as e:
            logger.error(f"Error processing predictions: {e}")
            return {"error": str(e), "predictions": {}}
    
    async def _compute_all_predictions(
        self,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute all ML predictions for the current conversation state.
        """
        # Run predictions in parallel
        objection_task = self.prediction_service.predict_objections(messages, context)
        needs_task = self.prediction_service.predict_needs(messages, context)
        conversion_task = self.prediction_service.predict_conversion(messages, context)
        
        # Wait for all predictions
        objections, needs, conversion = await asyncio.gather(
            objection_task, needs_task, conversion_task
        )
        
        return {
            "objections": objections,
            "needs": needs,
            "conversion": conversion,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _enhance_with_ab_testing(
        self,
        conversation_id: str,
        predictions: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance predictions with A/B test variant selections.
        """
        ab_variants = {}
        
        # Check for active experiments
        active_experiments = await self.ab_testing.get_active_experiments()
        
        for experiment in active_experiments:
            if self._should_apply_experiment(experiment, context):
                # Select variant using Multi-Armed Bandit
                variant = await self.ab_testing.select_variant(
                    experiment_id=experiment["id"],
                    context=context
                )
                
                if variant:
                    ab_variants[experiment["name"]] = {
                        "experiment_id": experiment["id"],
                        "variant_id": variant["id"],
                        "variant_name": variant["name"],
                        "parameters": variant.get("parameters", {})
                    }
        
        predictions["ab_variants"] = ab_variants
        return predictions
    
    async def record_conversation_outcome(
        self,
        conversation_id: str,
        outcome: str,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Record the final outcome of a conversation for learning.
        
        Args:
            conversation_id: Conversation identifier
            outcome: Final outcome (completed, abandoned, etc.)
            metrics: Performance metrics
        """
        try:
            # Record in outcome tracker
            await self.outcome_tracker.end_conversation(
                conversation_id=conversation_id,
                outcome=outcome,
                final_metrics=metrics
            )
            
            # Process A/B test conversions
            if "ab_variants" in metrics:
                for variant_info in metrics["ab_variants"].values():
                    success = outcome in ["completed", "qualified"]
                    await self.ab_testing.record_conversion(
                        experiment_id=variant_info["experiment_id"],
                        variant_id=variant_info["variant_id"],
                        success=success,
                        value=metrics.get("conversion_value", 0)
                    )
            
            # Queue for feedback loop processing
            await self.feedback_loop.queue_outcome(
                conversation_id=conversation_id,
                outcome=outcome,
                predictions=metrics.get("predictions", {}),
                actual_results=metrics
            )
            
            # Track completion event
            await self.event_tracker.track_outcome_event(
                conversation_id=conversation_id,
                outcome=outcome,
                metrics=metrics
            )
            
        except Exception as e:
            logger.error(f"Error recording outcome: {e}")
    
    async def get_pattern_insights(
        self,
        timeframe_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get pattern insights from recent conversations.
        
        Args:
            timeframe_hours: Hours to look back
            
        Returns:
            Pattern analysis results
        """
        try:
            # Get recent patterns from database
            since = datetime.now() - timedelta(hours=timeframe_hours)
            
            response = await self.supabase.table("pattern_recognitions").select(
                "*"
            ).gte("created_at", since.isoformat()).execute()
            
            patterns = response.data if response.data else []
            
            # Aggregate patterns
            pattern_summary = self._aggregate_patterns(patterns)
            
            # Get trending topics
            trending = self._identify_trending_patterns(patterns)
            
            # Get anomalies
            anomalies = self._detect_anomalies(patterns)
            
            return {
                "total_patterns": len(patterns),
                "timeframe_hours": timeframe_hours,
                "pattern_summary": pattern_summary,
                "trending_patterns": trending,
                "anomalies": anomalies,
                "insights": self._generate_pattern_insights(pattern_summary, trending)
            }
            
        except Exception as e:
            logger.error(f"Error getting pattern insights: {e}")
            return {"error": str(e)}
    
    async def get_ml_pipeline_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive ML pipeline metrics.
        """
        try:
            # Get metrics from all components
            prediction_metrics = await self._get_prediction_metrics()
            ab_test_metrics = await self._get_ab_test_metrics()
            feedback_metrics = await self.feedback_loop.get_metrics()
            model_metrics = await self.model_updater.get_update_metrics()
            
            # Get buffer status
            buffer_status = {
                "prediction_buffer": len(self.prediction_buffer),
                "event_buffer": len(self.event_buffer),
                "pattern_buffer": len(self.pattern_buffer)
            }
            
            return {
                "pipeline_status": "operational",
                "timestamp": datetime.now().isoformat(),
                "predictions": prediction_metrics,
                "ab_testing": ab_test_metrics,
                "feedback_loop": feedback_metrics,
                "model_updates": model_metrics,
                "buffers": buffer_status,
                "health_score": self._calculate_pipeline_health()
            }
            
        except Exception as e:
            logger.error(f"Error getting pipeline metrics: {e}")
            return {"error": str(e), "pipeline_status": "error"}
    
    # Background processing methods
    
    async def _process_buffers_periodically(self):
        """Periodically flush buffers to database."""
        while True:
            try:
                await asyncio.sleep(60)  # Every minute
                
                # Flush all buffers
                await self._flush_prediction_buffer()
                await self._flush_event_buffer()
                await self._flush_pattern_buffer()
                
            except Exception as e:
                logger.error(f"Error in buffer processing: {e}")
    
    async def _run_feedback_loop_periodically(self):
        """Run feedback loop processing periodically."""
        while True:
            try:
                await asyncio.sleep(3600)  # Every hour
                
                # Process feedback loop
                results = await self.feedback_loop.process_feedback_batch()
                
                if results["improvements_found"]:
                    logger.info(f"Feedback loop found {len(results['improvements_found'])} improvements")
                    
                    # Queue model updates if significant improvements found
                    if len(results["improvements_found"]) >= 10:
                        await self.model_updater.queue_update(
                            model_type="all",
                            reason="feedback_loop_improvements",
                            data=results["improvements_found"]
                        )
                
            except Exception as e:
                logger.error(f"Error in feedback loop: {e}")
    
    async def _update_models_periodically(self):
        """Check and update models periodically."""
        while True:
            try:
                update_hours = self.config["update_frequency_hours"]
                await asyncio.sleep(update_hours * 3600)
                
                # Check if models need updating
                update_needed = await self._check_model_update_needed()
                
                if update_needed:
                    logger.info("Starting scheduled model update")
                    
                    # Get recent training data
                    training_data = await self._prepare_training_data()
                    
                    # Update models
                    update_results = await self.model_updater.update_all_models(
                        training_data=training_data,
                        validation_split=0.2
                    )
                    
                    logger.info(f"Model update completed: {update_results}")
                    
                    # Update drift detection baselines after retraining
                    await self._update_drift_baselines()
                
            except Exception as e:
                logger.error(f"Error in model update: {e}")
    
    async def _analyze_patterns_periodically(self):
        """Analyze patterns in conversation data."""
        while True:
            try:
                await asyncio.sleep(1800)  # Every 30 minutes
                
                # Get recent predictions and outcomes
                window_hours = self.config["pattern_detection_window_hours"]
                patterns = await self._detect_conversation_patterns(window_hours)
                
                if patterns:
                    # Store patterns
                    for pattern in patterns:
                        self.pattern_buffer.append(pattern)
                    
                    # Flush if buffer is large
                    if len(self.pattern_buffer) >= 50:
                        await self._flush_pattern_buffer()
                
            except Exception as e:
                logger.error(f"Error in pattern analysis: {e}")
    
    # Helper methods
    
    async def _flush_prediction_buffer(self):
        """Flush prediction buffer to database."""
        if not self.prediction_buffer:
            return
        
        try:
            # Prepare batch insert
            records = []
            for event in self.prediction_buffer:
                records.append({
                    "id": event["id"],
                    "conversation_id": event["conversation_id"],
                    "timestamp": event["timestamp"],
                    "predictions": json.dumps(event["predictions"]),
                    "context": json.dumps(event["context"]),
                    "message_count": event["message_count"]
                })
            
            # Insert to ml_tracking_events
            await self.supabase.table("ml_tracking_events").insert(records).execute()
            
            # Clear buffer
            self.prediction_buffer.clear()
            
            logger.info(f"Flushed {len(records)} predictions to database")
            
        except Exception as e:
            logger.error(f"Error flushing prediction buffer: {e}")
    
    def _should_apply_experiment(
        self,
        experiment: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """Check if experiment should be applied to this conversation."""
        # Check experiment criteria
        criteria = experiment.get("targeting_criteria", {})
        
        if not criteria:
            return True
        
        # Check customer segment
        if "segment" in criteria:
            customer_segment = context.get("customer_segment", "general")
            if customer_segment not in criteria["segment"]:
                return False
        
        # Check conversation phase
        if "phases" in criteria:
            current_phase = context.get("phase", "greeting")
            if current_phase not in criteria["phases"]:
                return False
        
        return True
    
    def _extract_confidence_scores(self, predictions: Dict[str, Any]) -> Dict[str, float]:
        """Extract all confidence scores from predictions."""
        scores = {}
        
        # Extract objection confidence
        if "objections" in predictions and "confidence" in predictions["objections"]:
            scores["objection_confidence"] = predictions["objections"]["confidence"]
        
        # Extract needs confidence
        if "needs" in predictions and "confidence" in predictions["needs"]:
            scores["needs_confidence"] = predictions["needs"]["confidence"]
        
        # Extract conversion probability
        if "conversion" in predictions and "probability" in predictions["conversion"]:
            scores["conversion_probability"] = predictions["conversion"]["probability"]
        
        return scores
    
    def _aggregate_patterns(self, patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate patterns by type and frequency."""
        aggregated = {}
        
        for pattern in patterns:
            pattern_type = pattern.get("pattern_type", "unknown")
            if pattern_type not in aggregated:
                aggregated[pattern_type] = {
                    "count": 0,
                    "occurrences": [],
                    "confidence_avg": 0
                }
            
            aggregated[pattern_type]["count"] += 1
            aggregated[pattern_type]["occurrences"].append(pattern)
            
        # Calculate averages
        for pattern_type, data in aggregated.items():
            confidences = [p.get("confidence", 0) for p in data["occurrences"]]
            data["confidence_avg"] = sum(confidences) / len(confidences) if confidences else 0
        
        return aggregated
    
    def _calculate_pipeline_health(self) -> float:
        """Calculate overall pipeline health score (0-100)."""
        health_factors = []
        
        # Check buffer sizes (lower is better)
        buffer_health = 100 - min(100, (
            len(self.prediction_buffer) + 
            len(self.event_buffer) + 
            len(self.pattern_buffer)
        ) / 3)
        health_factors.append(buffer_health)
        
        # Check last successful operations
        # TODO: Track last successful operations
        health_factors.append(90)  # Placeholder
        
        # Average health score
        return sum(health_factors) / len(health_factors)
    
    async def _track_for_drift_detection(
        self,
        conversation_id: str,
        predictions: Dict[str, Any],
        context: Dict[str, Any],
        messages: List[Dict[str, Any]]
    ):
        """Track predictions and features for drift detection."""
        try:
            # Extract features from context and messages
            features = self._extract_features_for_drift(context, messages)
            
            # Track each model's predictions
            if "objections" in predictions:
                await self.drift_detector.track_prediction(
                    model_name="objection_predictor",
                    features=features,
                    prediction=predictions["objections"].get("predicted_objections", []),
                    metadata={"conversation_id": conversation_id}
                )
            
            if "needs" in predictions:
                await self.drift_detector.track_prediction(
                    model_name="needs_predictor", 
                    features=features,
                    prediction=predictions["needs"].get("predicted_needs", []),
                    metadata={"conversation_id": conversation_id}
                )
            
            if "conversion" in predictions:
                await self.drift_detector.track_prediction(
                    model_name="conversion_predictor",
                    features=features,
                    prediction=predictions["conversion"].get("probability", 0.5),
                    metadata={"conversation_id": conversation_id}
                )
            
        except Exception as e:
            logger.error(f"Error tracking for drift detection: {e}")
    
    def _extract_features_for_drift(
        self,
        context: Dict[str, Any],
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract features for drift detection."""
        features = {
            "message_count": len(messages),
            "conversation_phase": context.get("phase", "unknown"),
            "customer_segment": context.get("customer_segment", "general")
        }
        
        # Add customer profile features
        if "customer_data" in context:
            customer = context["customer_data"]
            features.update({
                "has_budget": bool(customer.get("budget")),
                "has_timeline": bool(customer.get("timeline")),
                "interest_level": customer.get("interest_level", 0)
            })
        
        # Add conversation statistics
        if messages:
            total_length = sum(len(msg.get("content", "")) for msg in messages)
            features["avg_message_length"] = total_length / len(messages)
            features["user_message_count"] = sum(1 for msg in messages if msg.get("role") == "user")
        
        return features
    
    async def _check_model_update_needed(self) -> bool:
        """Check if models need updating based on drift or performance."""
        try:
            # Check drift for all models
            models_to_check = ["objection_predictor", "needs_predictor", "conversion_predictor"]
            
            for model_name in models_to_check:
                report = await self.drift_detector.detect_drift(model_name)
                
                if report.requires_retraining:
                    logger.info(f"Model {model_name} requires retraining due to drift")
                    return True
            
            # Check sample size thresholds
            min_samples = self.config["min_samples_for_update"]
            for model_name in models_to_check:
                sample_count = len(self.drift_detector.prediction_windows.get(model_name, []))
                if sample_count >= min_samples:
                    logger.info(f"Model {model_name} has enough samples for update")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking model update need: {e}")
            return False
    
    async def _update_drift_baselines(self):
        """Update drift detection baselines after model retraining."""
        try:
            logger.info("Updating drift detection baselines")
            
            # Get recent prediction data for baselines
            since = datetime.now() - timedelta(days=7)
            
            # Update baselines for each model
            models = ["objection_predictor", "needs_predictor", "conversion_predictor"]
            
            for model_name in models:
                # Get recent predictions and features
                response = await self.supabase.table("ml_prediction_tracking").select("*").eq(
                    "model_name", model_name
                ).gte("created_at", since.isoformat()).execute()
                
                if response.data and len(response.data) > 100:
                    # Extract features and predictions
                    features_dict = defaultdict(list)
                    predictions = []
                    
                    for record in response.data:
                        features = json.loads(record["features"])
                        for feat_name, value in features.items():
                            if isinstance(value, (int, float)):
                                features_dict[feat_name].append(value)
                        
                        pred = record["prediction"]
                        if isinstance(pred, str):
                            pred = json.loads(pred)
                        predictions.append(pred)
                    
                    # Calculate performance if we have actuals
                    performance = None
                    if any(r.get("actual") for r in response.data):
                        correct = sum(1 for r in response.data 
                                    if r.get("actual") and r["prediction"] == r["actual"])
                        performance = correct / len(response.data)
                    
                    # Update baseline
                    await self.drift_detector.update_baseline(
                        model_name=model_name,
                        features=dict(features_dict),
                        predictions=predictions,
                        performance_score=performance
                    )
                    
                    logger.info(f"Updated baseline for {model_name}")
            
        except Exception as e:
            logger.error(f"Error updating drift baselines: {e}")
    
    async def _prepare_training_data(self) -> Dict[str, Any]:
        """Prepare training data for model updates."""
        # This would typically fetch recent conversation data
        # and format it for training
        return {
            "objection_data": [],
            "needs_data": [],
            "conversion_data": []
        }
    
    async def _detect_conversation_patterns(self, window_hours: int) -> List[Dict[str, Any]]:
        """Detect patterns in recent conversations."""
        # Placeholder for pattern detection logic
        return []
    
    async def _flush_event_buffer(self):
        """Flush event buffer to database."""
        # Placeholder - implement if needed
        pass
    
    async def _flush_pattern_buffer(self):
        """Flush pattern buffer to database."""
        # Placeholder - implement if needed
        pass
    
    async def _get_prediction_metrics(self) -> Dict[str, Any]:
        """Get metrics about predictions."""
        return {
            "total_predictions": len(self.prediction_buffer),
            "models_active": 3
        }
    
    async def _get_ab_test_metrics(self) -> Dict[str, Any]:
        """Get A/B testing metrics."""
        return {
            "active_experiments": len(self.ab_testing.active_experiments),
            "total_assignments": len(self.ab_testing.experiment_assignments)
        }
    
    def _identify_trending_patterns(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify trending patterns."""
        # Placeholder for trending analysis
        return []
    
    def _detect_anomalies(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalous patterns."""
        # Placeholder for anomaly detection
        return []
    
    def _generate_pattern_insights(
        self,
        pattern_summary: Dict[str, Any],
        trending: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate insights from patterns."""
        insights = []
        
        for pattern_type, data in pattern_summary.items():
            if data["count"] > 10:
                insights.append(f"High frequency of {pattern_type}: {data['count']} occurrences")
        
        return insights
    
    async def _process_buffers(self):
        """Process all buffers immediately."""
        await self._flush_prediction_buffer()
        await self._flush_event_buffer()
        await self._flush_pattern_buffer()
    
    async def cleanup(self):
        """
        Cleanup resources and stop background tasks.
        
        This should be called when shutting down the service.
        """
        logger.info("Cleaning up MLPipelineService")
        
        try:
            # Process remaining buffers
            if self.prediction_buffer or self.event_buffer or self.pattern_buffer:
                logger.info("Processing remaining buffers before shutdown")
                await self._process_buffers()
            
            # Unregister from task registry
            if self.task_manager:
                registry = get_task_registry()
                await registry.unregister_service("ml_pipeline")
                self.task_manager = None
            
            logger.info("MLPipelineService cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during MLPipelineService cleanup: {e}")