"""
ML Feedback Loop - Implements continuous learning from outcomes.

Responsible for:
- Comparing predictions with actual outcomes
- Identifying prediction errors
- Generating improvement suggestions
- Queuing model retraining
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import numpy as np
from collections import defaultdict

from src.integrations.supabase.resilient_client import resilient_supabase_client as supabase_client

logger = logging.getLogger(__name__)


class MLFeedbackLoop:
    """
    Implements feedback loop for continuous ML improvement.
    """
    
    def __init__(self):
        """Initialize the feedback loop."""
        self.supabase = supabase_client
        
        # Feedback queue for batch processing
        self.feedback_queue = []
        
        # Error analysis thresholds
        self.error_thresholds = {
            "objection_miss_rate": 0.20,  # 20% miss rate
            "needs_miss_rate": 0.25,  # 25% miss rate
            "conversion_error_rate": 0.30,  # 30% error rate
            "confidence_calibration_error": 0.15  # 15% calibration error
        }
        
        # Learning parameters
        self.learning_config = {
            "min_samples_for_learning": 100,
            "confidence_weight": 0.7,
            "recency_weight": 0.3,
            "pattern_threshold": 0.6
        }
    
    async def queue_outcome(
        self,
        conversation_id: str,
        outcome: str,
        predictions: Dict[str, Any],
        actual_results: Dict[str, Any]
    ) -> None:
        """
        Queue a conversation outcome for feedback processing.
        
        Args:
            conversation_id: ID of the conversation
            outcome: Actual conversation outcome
            predictions: ML predictions made during conversation
            actual_results: Actual results and metrics
        """
        try:
            feedback_item = {
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat(),
                "outcome": outcome,
                "predictions": predictions,
                "actual_results": actual_results,
                "processed": False
            }
            
            # Add to queue
            self.feedback_queue.append(feedback_item)
            
            # Process immediately if queue is large
            if len(self.feedback_queue) >= 50:
                await self.process_feedback_batch()
            
        except Exception as e:
            logger.error(f"Error queuing outcome: {e}")
    
    async def process_feedback_batch(
        self,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Process batch of feedback items.
        
        Args:
            force: Force processing even with small batch
            
        Returns:
            Processing results
        """
        try:
            # Check if we have enough items
            if not force and len(self.feedback_queue) < 10:
                return {"processed": 0, "improvements_found": []}
            
            # Process items
            processed_count = 0
            improvements = []
            error_patterns = defaultdict(list)
            
            for item in self.feedback_queue:
                if item["processed"]:
                    continue
                
                # Analyze prediction accuracy
                analysis = await self._analyze_prediction_accuracy(
                    item["predictions"],
                    item["outcome"],
                    item["actual_results"]
                )
                
                # Collect error patterns
                if analysis["errors"]:
                    for error in analysis["errors"]:
                        error_patterns[error["type"]].append(error)
                
                # Mark as processed
                item["processed"] = True
                processed_count += 1
            
            # Identify improvement opportunities
            if error_patterns:
                improvements = await self._identify_improvements(error_patterns)
            
            # Store feedback results
            await self._store_feedback_results(improvements, error_patterns)
            
            # Clear processed items
            self.feedback_queue = [item for item in self.feedback_queue if not item["processed"]]
            
            return {
                "processed": processed_count,
                "improvements_found": improvements,
                "error_patterns": dict(error_patterns)
            }
            
        except Exception as e:
            logger.error(f"Error processing feedback batch: {e}")
            return {"error": str(e), "processed": 0}
    
    async def get_learning_insights(
        self,
        model_type: str,
        timeframe_days: int = 7
    ) -> Dict[str, Any]:
        """
        Get learning insights for a specific model.
        
        Args:
            model_type: Type of model (objection, needs, conversion)
            timeframe_days: Days to analyze
            
        Returns:
            Learning insights
        """
        try:
            since = datetime.now() - timedelta(days=timeframe_days)
            
            # Get feedback data from database
            response = await self.supabase.table("ml_tracking_events").select(
                "data"
            ).eq(
                "event_category", "feedback"
            ).gte(
                "timestamp", since.isoformat()
            ).execute()
            
            # Analyze feedback for the model
            insights = {
                "model_type": model_type,
                "timeframe_days": timeframe_days,
                "total_feedback_items": len(response.data or []),
                "accuracy_trends": [],
                "common_errors": [],
                "improvement_suggestions": []
            }
            
            # Process feedback data
            accuracy_by_day = defaultdict(list)
            error_counts = defaultdict(int)
            
            for event in response.data or []:
                if not event.get("data"):
                    continue
                
                data = json.loads(event["data"])
                if model_type not in data.get("model_performance", {}):
                    continue
                
                perf = data["model_performance"][model_type]
                day = datetime.fromisoformat(data["timestamp"]).date()
                
                # Track accuracy
                if "accuracy" in perf:
                    accuracy_by_day[day.isoformat()].append(perf["accuracy"])
                
                # Track errors
                if "errors" in perf:
                    for error in perf["errors"]:
                        error_counts[error["type"]] += 1
            
            # Calculate accuracy trends
            for day, accuracies in sorted(accuracy_by_day.items()):
                insights["accuracy_trends"].append({
                    "date": day,
                    "avg_accuracy": np.mean(accuracies),
                    "sample_size": len(accuracies)
                })
            
            # Get common errors
            for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                insights["common_errors"].append({
                    "type": error_type,
                    "count": count,
                    "percentage": count / insights["total_feedback_items"] * 100
                })
            
            # Generate improvement suggestions
            insights["improvement_suggestions"] = self._generate_improvement_suggestions(
                insights["accuracy_trends"],
                insights["common_errors"]
            )
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting learning insights: {e}")
            return {"error": str(e)}
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get feedback loop metrics.
        
        Returns:
            Current metrics
        """
        try:
            # Get recent feedback stats
            last_24h = datetime.now() - timedelta(hours=24)
            
            response = await self.supabase.table("ml_tracking_events").select(
                "id"
            ).eq(
                "event_category", "feedback"
            ).gte(
                "timestamp", last_24h.isoformat()
            ).execute()
            
            feedback_count_24h = len(response.data or [])
            
            return {
                "queue_size": len(self.feedback_queue),
                "feedback_processed_24h": feedback_count_24h,
                "active_improvements": await self._get_active_improvements_count(),
                "avg_accuracy_improvement": await self._get_accuracy_improvement(),
                "last_batch_processed": await self._get_last_batch_time()
            }
            
        except Exception as e:
            logger.error(f"Error getting feedback metrics: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    
    async def _analyze_prediction_accuracy(
        self,
        predictions: Dict[str, Any],
        outcome: str,
        actual_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze accuracy of predictions vs actual outcomes.
        
        Args:
            predictions: ML predictions
            outcome: Actual outcome
            actual_results: Actual results
            
        Returns:
            Accuracy analysis
        """
        errors = []
        analysis = {
            "overall_accuracy": 0,
            "errors": errors,
            "model_performance": {}
        }
        
        # Analyze objection predictions
        if "objections" in predictions:
            objection_analysis = self._analyze_objection_accuracy(
                predictions["objections"],
                actual_results.get("actual_objections", [])
            )
            analysis["model_performance"]["objection"] = objection_analysis
            errors.extend(objection_analysis.get("errors", []))
        
        # Analyze needs predictions
        if "needs" in predictions:
            needs_analysis = self._analyze_needs_accuracy(
                predictions["needs"],
                actual_results.get("actual_needs", [])
            )
            analysis["model_performance"]["needs"] = needs_analysis
            errors.extend(needs_analysis.get("errors", []))
        
        # Analyze conversion predictions
        if "conversion" in predictions:
            conversion_analysis = self._analyze_conversion_accuracy(
                predictions["conversion"],
                outcome,
                actual_results.get("conversion_value", 0)
            )
            analysis["model_performance"]["conversion"] = conversion_analysis
            errors.extend(conversion_analysis.get("errors", []))
        
        # Calculate overall accuracy
        accuracies = [
            perf.get("accuracy", 0) 
            for perf in analysis["model_performance"].values()
        ]
        if accuracies:
            analysis["overall_accuracy"] = np.mean(accuracies)
        
        return analysis
    
    def _analyze_objection_accuracy(
        self,
        predicted: Dict[str, Any],
        actual: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze objection prediction accuracy.
        
        Args:
            predicted: Predicted objections
            actual: Actual objections encountered
            
        Returns:
            Accuracy analysis
        """
        analysis = {
            "accuracy": 0,
            "errors": [],
            "metrics": {}
        }
        
        predicted_types = [
            obj["type"] for obj in predicted.get("objections", [])
        ]
        
        # Calculate precision and recall
        if predicted_types or actual:
            true_positives = len(set(predicted_types) & set(actual))
            false_positives = len(set(predicted_types) - set(actual))
            false_negatives = len(set(actual) - set(predicted_types))
            
            precision = true_positives / (true_positives + false_positives) if predicted_types else 0
            recall = true_positives / (true_positives + false_negatives) if actual else 0
            
            analysis["accuracy"] = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            analysis["metrics"] = {
                "precision": precision,
                "recall": recall,
                "f1_score": analysis["accuracy"]
            }
            
            # Record errors
            for objection in set(actual) - set(predicted_types):
                analysis["errors"].append({
                    "type": "missed_objection",
                    "objection": objection,
                    "impact": "high"
                })
        
        return analysis
    
    def _analyze_needs_accuracy(
        self,
        predicted: Dict[str, Any],
        actual: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze needs prediction accuracy.
        
        Args:
            predicted: Predicted needs
            actual: Actual needs identified
            
        Returns:
            Accuracy analysis
        """
        analysis = {
            "accuracy": 0,
            "errors": [],
            "metrics": {}
        }
        
        predicted_types = [
            need["type"] for need in predicted.get("needs", [])
        ]
        
        # Similar analysis to objections
        if predicted_types or actual:
            overlap = len(set(predicted_types) & set(actual))
            total = len(set(predicted_types) | set(actual))
            
            analysis["accuracy"] = overlap / total if total > 0 else 0
            
            # Record missed needs
            for need in set(actual) - set(predicted_types):
                analysis["errors"].append({
                    "type": "missed_need",
                    "need": need,
                    "impact": "medium"
                })
        
        return analysis
    
    def _analyze_conversion_accuracy(
        self,
        predicted: Dict[str, Any],
        actual_outcome: str,
        actual_value: float
    ) -> Dict[str, Any]:
        """
        Analyze conversion prediction accuracy.
        
        Args:
            predicted: Predicted conversion probability
            actual_outcome: Actual conversation outcome
            actual_value: Actual conversion value
            
        Returns:
            Accuracy analysis
        """
        analysis = {
            "accuracy": 0,
            "errors": [],
            "metrics": {}
        }
        
        predicted_prob = predicted.get("probability", 0)
        predicted_convert = predicted.get("will_convert", False)
        actual_convert = actual_outcome in ["completed", "qualified"]
        
        # Binary accuracy
        if predicted_convert == actual_convert:
            analysis["accuracy"] = 1.0
        else:
            analysis["accuracy"] = 0.0
            analysis["errors"].append({
                "type": "conversion_misprediction",
                "predicted": predicted_convert,
                "actual": actual_convert,
                "probability_gap": abs(predicted_prob - (1.0 if actual_convert else 0.0)),
                "impact": "high"
            })
        
        # Probability calibration
        calibration_error = abs(predicted_prob - (1.0 if actual_convert else 0.0))
        analysis["metrics"]["calibration_error"] = calibration_error
        
        return analysis
    
    async def _identify_improvements(
        self,
        error_patterns: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Identify improvement opportunities from error patterns.
        
        Args:
            error_patterns: Grouped error patterns
            
        Returns:
            List of improvements
        """
        improvements = []
        
        for error_type, errors in error_patterns.items():
            if len(errors) < 5:  # Need sufficient samples
                continue
            
            # Calculate error rate
            error_rate = len(errors) / self.learning_config["min_samples_for_learning"]
            
            # Check against thresholds
            threshold_key = f"{error_type}_rate"
            if threshold_key in self.error_thresholds:
                if error_rate > self.error_thresholds[threshold_key]:
                    improvement = {
                        "type": error_type,
                        "error_rate": error_rate,
                        "sample_size": len(errors),
                        "priority": self._calculate_priority(error_type, error_rate),
                        "suggested_action": self._suggest_improvement_action(error_type, errors),
                        "created_at": datetime.now().isoformat()
                    }
                    improvements.append(improvement)
        
        return sorted(improvements, key=lambda x: x["priority"], reverse=True)
    
    def _calculate_priority(
        self,
        error_type: str,
        error_rate: float
    ) -> str:
        """
        Calculate improvement priority.
        
        Args:
            error_type: Type of error
            error_rate: Rate of errors
            
        Returns:
            Priority level
        """
        # High impact errors
        if error_type in ["conversion_misprediction", "missed_objection"]:
            return "high" if error_rate > 0.3 else "medium"
        
        # Medium impact errors
        if error_type in ["missed_need", "confidence_calibration"]:
            return "medium" if error_rate > 0.4 else "low"
        
        return "low"
    
    def _suggest_improvement_action(
        self,
        error_type: str,
        errors: List[Dict[str, Any]]
    ) -> str:
        """
        Suggest improvement action based on error type.
        
        Args:
            error_type: Type of error
            errors: List of errors
            
        Returns:
            Suggested action
        """
        suggestions = {
            "missed_objection": "Retrain objection model with focus on missed objection types",
            "missed_need": "Expand needs taxonomy and retrain with more diverse examples",
            "conversion_misprediction": "Adjust conversion threshold and add more features",
            "confidence_calibration": "Implement confidence calibration techniques"
        }
        
        return suggestions.get(error_type, "Review and retrain model with recent data")
    
    def _generate_improvement_suggestions(
        self,
        accuracy_trends: List[Dict[str, Any]],
        common_errors: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Generate improvement suggestions based on trends and errors.
        
        Args:
            accuracy_trends: Accuracy trend data
            common_errors: Common error types
            
        Returns:
            List of suggestions
        """
        suggestions = []
        
        # Check for declining accuracy
        if len(accuracy_trends) >= 3:
            recent_accuracies = [t["avg_accuracy"] for t in accuracy_trends[-3:]]
            if all(recent_accuracies[i] < recent_accuracies[i-1] for i in range(1, len(recent_accuracies))):
                suggestions.append("Accuracy is declining - consider immediate model retraining")
        
        # Check for persistent errors
        for error in common_errors:
            if error["percentage"] > 20:
                suggestions.append(f"High {error['type']} rate ({error['percentage']:.1f}%) - focus training on this area")
        
        return suggestions
    
    async def _store_feedback_results(
        self,
        improvements: List[Dict[str, Any]],
        error_patterns: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        """
        Store feedback results in database.
        
        Args:
            improvements: Identified improvements
            error_patterns: Error patterns found
        """
        try:
            # Store as feedback event
            event_data = {
                "id": str(uuid.uuid4()),
                "event_type": "feedback_analysis",
                "event_category": "feedback",
                "timestamp": datetime.now().isoformat(),
                "data": json.dumps({
                    "improvements": improvements,
                    "error_summary": {
                        error_type: len(errors) 
                        for error_type, errors in error_patterns.items()
                    },
                    "total_errors": sum(len(errors) for errors in error_patterns.values())
                }),
                "created_at": datetime.now().isoformat()
            }
            
            await self.supabase.table("ml_tracking_events").insert(event_data).execute()
            
        except Exception as e:
            logger.error(f"Error storing feedback results: {e}")
    
    async def _get_active_improvements_count(self) -> int:
        """Get count of active improvements."""
        # TODO: Implement tracking of active improvements
        return 0
    
    async def _get_accuracy_improvement(self) -> float:
        """Get average accuracy improvement."""
        # TODO: Calculate from historical data
        return 0.0
    
    async def _get_last_batch_time(self) -> Optional[str]:
        """Get timestamp of last batch processing."""
        # TODO: Track last batch processing time
        return None