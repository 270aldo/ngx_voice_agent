"""
ML Metrics Aggregator - Aggregates and analyzes ML pipeline metrics.

Responsible for:
- Real-time metric aggregation
- Performance monitoring
- Trend analysis
- Alert generation
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import numpy as np
from collections import defaultdict

from src.integrations.supabase.resilient_client import resilient_supabase_client as supabase_client

logger = logging.getLogger(__name__)


class MLMetricsAggregator:
    """
    Aggregates ML metrics for monitoring and analysis.
    """
    
    def __init__(self):
        """Initialize the metrics aggregator."""
        self.supabase = supabase_client
        
        # Metric definitions
        self.metric_definitions = {
            "prediction_latency": {
                "type": "gauge",
                "unit": "milliseconds",
                "aggregations": ["avg", "p50", "p95", "p99"]
            },
            "prediction_confidence": {
                "type": "gauge",
                "unit": "percentage",
                "aggregations": ["avg", "min", "max"]
            },
            "conversion_rate": {
                "type": "rate",
                "unit": "percentage",
                "aggregations": ["value"]
            },
            "model_accuracy": {
                "type": "gauge",
                "unit": "percentage",
                "aggregations": ["avg"]
            },
            "drift_score": {
                "type": "gauge",
                "unit": "score",
                "aggregations": ["max", "avg"]
            },
            "ab_test_lift": {
                "type": "gauge",
                "unit": "percentage",
                "aggregations": ["value"]
            }
        }
        
        # Alert thresholds
        self.alert_thresholds = {
            "prediction_latency_p95": 1000,  # 1 second
            "prediction_confidence_min": 0.5,  # 50%
            "conversion_rate_drop": 0.2,  # 20% drop
            "model_accuracy_min": 0.7,  # 70%
            "drift_score_max": 0.3  # 0.3 drift score
        }
        
        # In-memory metric buffers for fast aggregation
        self.metric_buffers = defaultdict(list)
        self.aggregated_metrics = {}
    
    async def record_metric(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record a metric value.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional tags (model_type, experiment_id, etc.)
            timestamp: Timestamp (defaults to now)
        """
        try:
            if metric_name not in self.metric_definitions:
                logger.warning(f"Unknown metric: {metric_name}")
                return
            
            timestamp = timestamp or datetime.now()
            
            # Create metric point
            metric_point = {
                "timestamp": timestamp.isoformat(),
                "value": value,
                "tags": tags or {}
            }
            
            # Add to buffer
            buffer_key = f"{metric_name}:{json.dumps(tags or {}, sort_keys=True)}"
            self.metric_buffers[buffer_key].append(metric_point)
            
            # Check for alerts
            await self._check_metric_alerts(metric_name, value, tags)
            
            # Aggregate if buffer is large
            if len(self.metric_buffers[buffer_key]) >= 100:
                await self._aggregate_buffer(buffer_key)
            
        except Exception as e:
            logger.error(f"Error recording metric: {e}")
    
    async def get_aggregated_metrics(
        self,
        metric_names: Optional[List[str]] = None,
        timeframe_hours: int = 24,
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated metrics.
        
        Args:
            metric_names: Specific metrics to retrieve (None for all)
            timeframe_hours: Hours to look back
            tags: Filter by tags
            
        Returns:
            Aggregated metrics
        """
        try:
            # Flush buffers first
            await self._flush_all_buffers()
            
            since = datetime.now() - timedelta(hours=timeframe_hours)
            
            # Build query
            query = self.supabase.table("ml_experiments").select(
                "metrics"
            ).gte(
                "created_at", since.isoformat()
            )
            
            if tags:
                for key, value in tags.items():
                    query = query.contains("tags", {key: value})
            
            response = await query.execute()
            
            # Aggregate metrics
            aggregated = {}
            for record in response.data or []:
                metrics = record.get("metrics", {})
                for metric_name, values in metrics.items():
                    if metric_names and metric_name not in metric_names:
                        continue
                    
                    if metric_name not in aggregated:
                        aggregated[metric_name] = []
                    
                    aggregated[metric_name].extend(values)
            
            # Calculate aggregations
            results = {}
            for metric_name, values in aggregated.items():
                if metric_name in self.metric_definitions:
                    results[metric_name] = self._calculate_aggregations(
                        values,
                        self.metric_definitions[metric_name]["aggregations"]
                    )
            
            return {
                "timeframe_hours": timeframe_hours,
                "metrics": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting aggregated metrics: {e}")
            return {"error": str(e)}
    
    async def get_metric_trends(
        self,
        metric_name: str,
        interval: str = "hour",
        periods: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get metric trends over time.
        
        Args:
            metric_name: Name of the metric
            interval: Time interval (hour, day, week)
            periods: Number of periods to retrieve
            
        Returns:
            Trend data
        """
        try:
            # Calculate time boundaries
            interval_hours = {
                "hour": 1,
                "day": 24,
                "week": 168
            }.get(interval, 1)
            
            trends = []
            now = datetime.now()
            
            for i in range(periods):
                start = now - timedelta(hours=(i + 1) * interval_hours)
                end = now - timedelta(hours=i * interval_hours)
                
                # Get metrics for this period
                period_metrics = await self.get_aggregated_metrics(
                    metric_names=[metric_name],
                    timeframe_hours=interval_hours,
                    tags=None
                )
                
                if metric_name in period_metrics.get("metrics", {}):
                    trend_point = {
                        "period_start": start.isoformat(),
                        "period_end": end.isoformat(),
                        "values": period_metrics["metrics"][metric_name]
                    }
                    trends.append(trend_point)
            
            return trends
            
        except Exception as e:
            logger.error(f"Error getting metric trends: {e}")
            return []
    
    async def get_model_comparison_metrics(
        self,
        model_types: List[str],
        timeframe_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Compare metrics across different models.
        
        Args:
            model_types: List of model types to compare
            timeframe_hours: Hours to analyze
            
        Returns:
            Comparison results
        """
        try:
            comparison = {}
            
            for model_type in model_types:
                metrics = await self.get_aggregated_metrics(
                    timeframe_hours=timeframe_hours,
                    tags={"model_type": model_type}
                )
                
                comparison[model_type] = metrics.get("metrics", {})
            
            # Calculate relative performance
            relative_performance = self._calculate_relative_performance(comparison)
            
            return {
                "model_metrics": comparison,
                "relative_performance": relative_performance,
                "best_performing": self._identify_best_model(comparison),
                "improvement_opportunities": self._identify_improvement_opportunities(comparison)
            }
            
        except Exception as e:
            logger.error(f"Error comparing models: {e}")
            return {"error": str(e)}
    
    async def get_ab_test_metrics(
        self,
        experiment_id: str
    ) -> Dict[str, Any]:
        """
        Get metrics for a specific A/B test.
        
        Args:
            experiment_id: ID of the experiment
            
        Returns:
            A/B test metrics
        """
        try:
            # Get experiment results
            response = await self.supabase.table("ab_test_results").select(
                "*"
            ).eq(
                "experiment_id", experiment_id
            ).execute()
            
            if not response.data:
                return {"error": "No results found"}
            
            # Aggregate by variant
            variant_metrics = defaultdict(lambda: {
                "conversions": 0,
                "exposures": 0,
                "total_value": 0
            })
            
            for result in response.data:
                variant = result["variant_id"]
                variant_metrics[variant]["exposures"] += 1
                if result.get("converted", False):
                    variant_metrics[variant]["conversions"] += 1
                    variant_metrics[variant]["total_value"] += result.get("conversion_value", 0)
            
            # Calculate rates and statistics
            results = {}
            control_rate = None
            
            for variant, metrics in variant_metrics.items():
                conversion_rate = metrics["conversions"] / metrics["exposures"] if metrics["exposures"] > 0 else 0
                avg_value = metrics["total_value"] / metrics["conversions"] if metrics["conversions"] > 0 else 0
                
                results[variant] = {
                    "conversion_rate": conversion_rate,
                    "sample_size": metrics["exposures"],
                    "conversions": metrics["conversions"],
                    "avg_conversion_value": avg_value,
                    "total_value": metrics["total_value"]
                }
                
                if variant == "control":
                    control_rate = conversion_rate
            
            # Calculate lift for variants
            if control_rate is not None:
                for variant, metrics in results.items():
                    if variant != "control":
                        lift = (metrics["conversion_rate"] - control_rate) / control_rate if control_rate > 0 else 0
                        metrics["lift"] = lift
                        metrics["lift_percentage"] = lift * 100
            
            # Statistical significance
            significance = self._calculate_statistical_significance(variant_metrics)
            
            return {
                "experiment_id": experiment_id,
                "variants": results,
                "statistical_significance": significance,
                "winner": self._determine_winner(results, significance)
            }
            
        except Exception as e:
            logger.error(f"Error getting A/B test metrics: {e}")
            return {"error": str(e)}
    
    async def generate_metrics_report(
        self,
        timeframe_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Generate comprehensive metrics report.
        
        Args:
            timeframe_hours: Hours to analyze
            
        Returns:
            Comprehensive report
        """
        try:
            # Get all metrics
            all_metrics = await self.get_aggregated_metrics(
                timeframe_hours=timeframe_hours
            )
            
            # Get model comparisons
            model_comparison = await self.get_model_comparison_metrics(
                model_types=["objection", "needs", "conversion"],
                timeframe_hours=timeframe_hours
            )
            
            # Get active alerts
            alerts = await self._get_active_alerts()
            
            # Calculate health score
            health_score = self._calculate_ml_health_score(all_metrics, alerts)
            
            # Generate insights
            insights = self._generate_insights(all_metrics, model_comparison)
            
            return {
                "report_timestamp": datetime.now().isoformat(),
                "timeframe_hours": timeframe_hours,
                "overall_metrics": all_metrics,
                "model_comparison": model_comparison,
                "active_alerts": alerts,
                "health_score": health_score,
                "insights": insights,
                "recommendations": self._generate_recommendations(health_score, insights)
            }
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    
    async def _aggregate_buffer(
        self,
        buffer_key: str
    ) -> None:
        """
        Aggregate and store buffer data.
        
        Args:
            buffer_key: Buffer identifier
        """
        try:
            if not self.metric_buffers[buffer_key]:
                return
            
            # Parse buffer key
            metric_name, tags_str = buffer_key.split(":", 1)
            tags = json.loads(tags_str) if tags_str else {}
            
            # Aggregate values
            values = [point["value"] for point in self.metric_buffers[buffer_key]]
            aggregations = self._calculate_aggregations(
                values,
                self.metric_definitions[metric_name]["aggregations"]
            )
            
            # Store aggregated data
            record = {
                "id": str(uuid.uuid4()),
                "metric_name": metric_name,
                "tags": tags,
                "aggregations": aggregations,
                "sample_count": len(values),
                "timestamp": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat()
            }
            
            await self.supabase.table("ml_experiments").insert({
                "name": f"metric_aggregation_{metric_name}",
                "status": "completed",
                "metrics": {metric_name: values},
                "tags": tags,
                "created_at": datetime.now().isoformat()
            }).execute()
            
            # Clear buffer
            self.metric_buffers[buffer_key].clear()
            
        except Exception as e:
            logger.error(f"Error aggregating buffer: {e}")
    
    async def _flush_all_buffers(self) -> None:
        """Flush all metric buffers."""
        buffer_keys = list(self.metric_buffers.keys())
        for key in buffer_keys:
            await self._aggregate_buffer(key)
    
    def _calculate_aggregations(
        self,
        values: List[float],
        aggregation_types: List[str]
    ) -> Dict[str, float]:
        """
        Calculate aggregations for values.
        
        Args:
            values: List of values
            aggregation_types: Types of aggregations to calculate
            
        Returns:
            Aggregation results
        """
        if not values:
            return {agg: 0.0 for agg in aggregation_types}
        
        results = {}
        values_array = np.array(values)
        
        for agg in aggregation_types:
            if agg == "avg":
                results[agg] = float(np.mean(values_array))
            elif agg == "min":
                results[agg] = float(np.min(values_array))
            elif agg == "max":
                results[agg] = float(np.max(values_array))
            elif agg == "p50":
                results[agg] = float(np.percentile(values_array, 50))
            elif agg == "p95":
                results[agg] = float(np.percentile(values_array, 95))
            elif agg == "p99":
                results[agg] = float(np.percentile(values_array, 99))
            elif agg == "value":
                results[agg] = float(values_array[-1])  # Latest value
        
        return results
    
    async def _check_metric_alerts(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]]
    ) -> None:
        """
        Check if metric value triggers alerts.
        
        Args:
            metric_name: Name of metric
            value: Metric value
            tags: Metric tags
        """
        # Check against thresholds
        for threshold_name, threshold_value in self.alert_thresholds.items():
            if metric_name in threshold_name:
                should_alert = False
                
                if "min" in threshold_name and value < threshold_value:
                    should_alert = True
                elif "max" in threshold_name and value > threshold_value:
                    should_alert = True
                
                if should_alert:
                    await self._create_alert(
                        metric_name=metric_name,
                        threshold_name=threshold_name,
                        current_value=value,
                        threshold_value=threshold_value,
                        tags=tags
                    )
    
    async def _create_alert(
        self,
        metric_name: str,
        threshold_name: str,
        current_value: float,
        threshold_value: float,
        tags: Optional[Dict[str, str]]
    ) -> None:
        """
        Create an alert.
        
        Args:
            metric_name: Name of metric
            threshold_name: Name of threshold
            current_value: Current metric value
            threshold_value: Threshold value
            tags: Metric tags
        """
        try:
            alert = {
                "id": str(uuid.uuid4()),
                "metric_name": metric_name,
                "threshold_name": threshold_name,
                "current_value": current_value,
                "threshold_value": threshold_value,
                "tags": tags,
                "severity": self._determine_alert_severity(metric_name, current_value, threshold_value),
                "timestamp": datetime.now().isoformat(),
                "status": "active"
            }
            
            # Store alert
            await self.supabase.table("ml_tracking_events").insert({
                "event_type": "metric_alert",
                "event_category": "alert",
                "data": json.dumps(alert),
                "created_at": datetime.now().isoformat()
            }).execute()
            
            logger.warning(f"Alert created: {metric_name} = {current_value} (threshold: {threshold_value})")
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
    
    def _determine_alert_severity(
        self,
        metric_name: str,
        current_value: float,
        threshold_value: float
    ) -> str:
        """
        Determine alert severity.
        
        Args:
            metric_name: Name of metric
            current_value: Current value
            threshold_value: Threshold value
            
        Returns:
            Severity level
        """
        # Calculate deviation percentage
        deviation = abs(current_value - threshold_value) / threshold_value if threshold_value != 0 else 1.0
        
        # Critical metrics
        if metric_name in ["conversion_rate", "model_accuracy"]:
            return "critical" if deviation > 0.5 else "high"
        
        # Performance metrics
        if metric_name in ["prediction_latency", "drift_score"]:
            return "high" if deviation > 0.3 else "medium"
        
        return "low"
    
    def _calculate_relative_performance(
        self,
        comparison: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate relative performance between models.
        
        Args:
            comparison: Model comparison data
            
        Returns:
            Relative performance scores
        """
        relative = {}
        
        # Get baseline (best performing) for each metric
        baselines = {}
        for model, metrics in comparison.items():
            for metric_name, values in metrics.items():
                if metric_name not in baselines:
                    baselines[metric_name] = values
                else:
                    # Update baseline if better
                    if "accuracy" in metric_name or "confidence" in metric_name:
                        if values.get("avg", 0) > baselines[metric_name].get("avg", 0):
                            baselines[metric_name] = values
                    elif "latency" in metric_name:
                        if values.get("avg", float('inf')) < baselines[metric_name].get("avg", float('inf')):
                            baselines[metric_name] = values
        
        # Calculate relative performance
        for model, metrics in comparison.items():
            relative[model] = {}
            for metric_name, values in metrics.items():
                if metric_name in baselines:
                    baseline_value = baselines[metric_name].get("avg", 1.0)
                    current_value = values.get("avg", 0)
                    
                    if baseline_value != 0:
                        relative[model][metric_name] = current_value / baseline_value
                    else:
                        relative[model][metric_name] = 1.0
        
        return relative
    
    def _identify_best_model(
        self,
        comparison: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Identify best performing model.
        
        Args:
            comparison: Model comparison data
            
        Returns:
            Name of best model
        """
        scores = {}
        
        for model, metrics in comparison.items():
            score = 0
            weight_sum = 0
            
            # Weight different metrics
            weights = {
                "model_accuracy": 0.4,
                "prediction_confidence": 0.3,
                "prediction_latency": 0.2,
                "drift_score": 0.1
            }
            
            for metric_name, weight in weights.items():
                if metric_name in metrics:
                    value = metrics[metric_name].get("avg", 0)
                    
                    # Normalize based on metric type
                    if "latency" in metric_name or "drift" in metric_name:
                        # Lower is better
                        normalized = 1.0 / (1.0 + value)
                    else:
                        # Higher is better
                        normalized = value
                    
                    score += normalized * weight
                    weight_sum += weight
            
            if weight_sum > 0:
                scores[model] = score / weight_sum
        
        return max(scores, key=scores.get) if scores else "unknown"
    
    def _calculate_statistical_significance(
        self,
        variant_metrics: Dict[str, Dict[str, int]]
    ) -> Dict[str, Any]:
        """
        Calculate statistical significance for A/B test.
        
        Args:
            variant_metrics: Metrics by variant
            
        Returns:
            Statistical significance results
        """
        # Simple z-test for proportions
        if "control" not in variant_metrics:
            return {"error": "No control group found"}
        
        control = variant_metrics["control"]
        results = {}
        
        for variant, metrics in variant_metrics.items():
            if variant == "control":
                continue
            
            # Calculate z-score
            p1 = control["conversions"] / control["exposures"] if control["exposures"] > 0 else 0
            p2 = metrics["conversions"] / metrics["exposures"] if metrics["exposures"] > 0 else 0
            n1 = control["exposures"]
            n2 = metrics["exposures"]
            
            if n1 == 0 or n2 == 0:
                results[variant] = {"significant": False, "p_value": 1.0}
                continue
            
            # Pooled proportion
            p_pooled = (control["conversions"] + metrics["conversions"]) / (n1 + n2)
            
            # Standard error
            se = np.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))
            
            # Z-score
            z = (p2 - p1) / se if se > 0 else 0
            
            # P-value (two-tailed)
            from scipy import stats
            p_value = 2 * (1 - stats.norm.cdf(abs(z)))
            
            results[variant] = {
                "z_score": z,
                "p_value": p_value,
                "significant": p_value < 0.05
            }
        
        return results
    
    def _determine_winner(
        self,
        results: Dict[str, Dict[str, Any]],
        significance: Dict[str, Any]
    ) -> Optional[str]:
        """
        Determine A/B test winner.
        
        Args:
            results: Test results by variant
            significance: Statistical significance
            
        Returns:
            Winner variant or None
        """
        # Find variant with highest conversion rate and significance
        best_variant = None
        best_rate = 0
        
        for variant, metrics in results.items():
            if variant == "control":
                continue
            
            # Check if significantly better than control
            if variant in significance and significance[variant]["significant"]:
                if metrics["conversion_rate"] > best_rate:
                    best_rate = metrics["conversion_rate"]
                    best_variant = variant
        
        # Also check if control is best
        if "control" in results:
            control_rate = results["control"]["conversion_rate"]
            if control_rate >= best_rate:
                best_variant = "control"
        
        return best_variant
    
    def _calculate_ml_health_score(
        self,
        metrics: Dict[str, Any],
        alerts: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate overall ML health score.
        
        Args:
            metrics: Current metrics
            alerts: Active alerts
            
        Returns:
            Health score (0-100)
        """
        score = 100.0
        
        # Deduct for alerts
        for alert in alerts:
            severity = alert.get("severity", "low")
            if severity == "critical":
                score -= 20
            elif severity == "high":
                score -= 10
            elif severity == "medium":
                score -= 5
        
        # Check metric values
        metric_values = metrics.get("metrics", {})
        
        # Model accuracy
        if "model_accuracy" in metric_values:
            accuracy = metric_values["model_accuracy"].get("avg", 0)
            if accuracy < 0.7:
                score -= 15
            elif accuracy < 0.8:
                score -= 10
        
        # Prediction latency
        if "prediction_latency" in metric_values:
            latency = metric_values["prediction_latency"].get("p95", 0)
            if latency > 1000:
                score -= 10
            elif latency > 500:
                score -= 5
        
        return max(0, min(100, score))
    
    def _generate_insights(
        self,
        metrics: Dict[str, Any],
        model_comparison: Dict[str, Any]
    ) -> List[str]:
        """
        Generate insights from metrics.
        
        Args:
            metrics: Overall metrics
            model_comparison: Model comparison data
            
        Returns:
            List of insights
        """
        insights = []
        
        # Check for performance issues
        metric_values = metrics.get("metrics", {})
        
        if "prediction_latency" in metric_values:
            p95_latency = metric_values["prediction_latency"].get("p95", 0)
            if p95_latency > 800:
                insights.append(f"High prediction latency detected (p95: {p95_latency:.0f}ms)")
        
        if "model_accuracy" in metric_values:
            accuracy = metric_values["model_accuracy"].get("avg", 0)
            if accuracy < 0.75:
                insights.append(f"Model accuracy below target ({accuracy:.1%} < 75%)")
        
        # Model comparison insights
        if "best_performing" in model_comparison:
            best_model = model_comparison["best_performing"]
            insights.append(f"Best performing model: {best_model}")
        
        if "improvement_opportunities" in model_comparison:
            for opportunity in model_comparison["improvement_opportunities"][:2]:
                insights.append(opportunity)
        
        return insights
    
    def _generate_recommendations(
        self,
        health_score: float,
        insights: List[str]
    ) -> List[str]:
        """
        Generate recommendations based on health and insights.
        
        Args:
            health_score: ML health score
            insights: Current insights
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if health_score < 50:
            recommendations.append("Critical: Immediate attention required for ML pipeline")
        elif health_score < 70:
            recommendations.append("Warning: Review and address ML performance issues")
        
        # Specific recommendations based on insights
        for insight in insights:
            if "latency" in insight.lower():
                recommendations.append("Consider model optimization or infrastructure upgrade")
            elif "accuracy" in insight.lower():
                recommendations.append("Retrain models with recent data")
            elif "drift" in insight.lower():
                recommendations.append("Investigate data distribution changes")
        
        return recommendations
    
    def _identify_improvement_opportunities(
        self,
        comparison: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """
        Identify improvement opportunities from model comparison.
        
        Args:
            comparison: Model comparison data
            
        Returns:
            List of opportunities
        """
        opportunities = []
        
        # Find underperforming models
        for model, metrics in comparison.items():
            if "model_accuracy" in metrics:
                accuracy = metrics["model_accuracy"].get("avg", 0)
                if accuracy < 0.7:
                    opportunities.append(f"{model} model needs improvement (accuracy: {accuracy:.1%})")
        
        return opportunities
    
    async def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """
        Get currently active alerts.
        
        Returns:
            List of active alerts
        """
        try:
            # Get alerts from last 24 hours
            since = datetime.now() - timedelta(hours=24)
            
            response = await self.supabase.table("ml_tracking_events").select(
                "data"
            ).eq(
                "event_category", "alert"
            ).gte(
                "timestamp", since.isoformat()
            ).execute()
            
            alerts = []
            for event in response.data or []:
                if event.get("data"):
                    alert_data = json.loads(event["data"])
                    if alert_data.get("status") == "active":
                        alerts.append(alert_data)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []