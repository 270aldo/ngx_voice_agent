"""
ML Drift Detection Service - Monitors model performance degradation.

This service detects various types of drift in ML models:
- Concept Drift: When the relationship between features and target changes
- Data Drift: When the distribution of input features changes
- Performance Drift: When model accuracy degrades over time

Key features:
- Statistical tests for distribution changes (KS test, Chi-square, PSI)
- Performance monitoring with sliding windows
- Automatic alerts when drift is detected
- Recommendations for model retraining
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
from scipy import stats
from collections import defaultdict, deque

from src.integrations.supabase.resilient_client import resilient_supabase_client as supabase_client
from src.utils.async_task_manager import AsyncTaskManager, get_task_registry
from src.core.constants import MLConstants, TimeConstants, DatabaseConstants

logger = logging.getLogger(__name__)


class DriftType(Enum):
    """Types of drift that can be detected."""
    NONE = "none"
    CONCEPT_DRIFT = "concept_drift"
    DATA_DRIFT = "data_drift"
    PERFORMANCE_DRIFT = "performance_drift"
    PREDICTION_DRIFT = "prediction_drift"


class DriftSeverity(Enum):
    """Severity levels for detected drift."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DriftMetrics:
    """Metrics for drift detection."""
    ks_statistic: float = 0.0
    ks_p_value: float = 1.0
    psi_score: float = 0.0
    wasserstein_distance: float = 0.0
    performance_delta: float = 0.0
    prediction_distribution_change: float = 0.0
    

@dataclass
class DriftReport:
    """Comprehensive drift detection report."""
    model_name: str
    detection_timestamp: datetime
    drift_type: DriftType
    severity: DriftSeverity
    metrics: DriftMetrics
    affected_features: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    requires_retraining: bool = False
    confidence: float = 0.0


class MLDriftDetector:
    """
    Detects and monitors drift in ML models.
    
    Uses multiple statistical methods to detect when models
    need retraining due to changing data patterns.
    """
    
    def __init__(self):
        """Initialize drift detector."""
        self.supabase = supabase_client
        self.task_manager: Optional[AsyncTaskManager] = None
        
        # Drift detection thresholds
        self.thresholds = {
            "ks_p_value": MLConstants.KS_TEST_SIGNIFICANCE,
            "psi_warning": MLConstants.PSI_WARNING_THRESHOLD,
            "psi_critical": MLConstants.PSI_CRITICAL_THRESHOLD,
            "performance_drop": MLConstants.PERFORMANCE_DROP_THRESHOLD,
            "wasserstein_warning": MLConstants.PSI_WARNING_THRESHOLD,
            "wasserstein_critical": MLConstants.PSI_WARNING_THRESHOLD * 2
        }
        
        # Sliding windows for monitoring
        self.performance_windows = defaultdict(lambda: deque(maxlen=MLConstants.MIN_TRAINING_SAMPLES))
        self.prediction_windows = defaultdict(lambda: deque(maxlen=DatabaseConstants.MAX_BATCH_SIZE))
        self.feature_windows = defaultdict(lambda: defaultdict(lambda: deque(maxlen=DatabaseConstants.MAX_BATCH_SIZE)))
        
        # Baseline distributions
        self.baseline_distributions = {}
        self.baseline_performance = {}
        
        # Initialize async components
        import asyncio
        asyncio.create_task(self._initialize_async())
        
        logger.info("MLDriftDetector initialized")
    
    async def _initialize_async(self):
        """Async initialization including task manager setup."""
        try:
            # Get task manager from registry
            registry = get_task_registry()
            self.task_manager = await registry.register_service("ml_drift_detector")
            
            # Start monitoring task
            if self.task_manager:
                await self.task_manager.create_task(
                    self._monitor_drift_periodically(),
                    name="drift_monitoring"
                )
            
            # Load baseline distributions
            await self._load_baseline_distributions()
            
            logger.info("MLDriftDetector async initialization complete")
        except Exception as e:
            logger.error(f"Failed to initialize MLDriftDetector async: {e}")
    
    async def track_prediction(
        self,
        model_name: str,
        features: Dict[str, Any],
        prediction: Any,
        actual: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Track a prediction for drift detection.
        
        Args:
            model_name: Name of the model
            features: Input features used
            prediction: Model prediction
            actual: Actual outcome (if available)
            metadata: Additional metadata
        """
        try:
            # Add to windows
            self.prediction_windows[model_name].append(prediction)
            
            # Track feature distributions
            for feature_name, value in features.items():
                if isinstance(value, (int, float)):
                    self.feature_windows[model_name][feature_name].append(value)
            
            # Track performance if actual outcome available
            if actual is not None:
                performance = self._calculate_performance(prediction, actual)
                self.performance_windows[model_name].append(performance)
            
            # Store in database for historical analysis
            await self._store_prediction_tracking(
                model_name=model_name,
                features=features,
                prediction=prediction,
                actual=actual,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error tracking prediction: {e}")
    
    async def detect_drift(
        self,
        model_name: str,
        check_all_types: bool = True
    ) -> DriftReport:
        """
        Detect drift for a specific model.
        
        Args:
            model_name: Name of the model to check
            check_all_types: Whether to check all drift types
            
        Returns:
            DriftReport with detection results
        """
        try:
            metrics = DriftMetrics()
            drift_types = []
            affected_features = []
            
            # Check data drift
            if check_all_types or True:
                data_drift, data_features = await self._check_data_drift(model_name, metrics)
                if data_drift:
                    drift_types.append(DriftType.DATA_DRIFT)
                    affected_features.extend(data_features)
            
            # Check prediction drift
            if check_all_types or True:
                pred_drift = await self._check_prediction_drift(model_name, metrics)
                if pred_drift:
                    drift_types.append(DriftType.PREDICTION_DRIFT)
            
            # Check performance drift
            if check_all_types or True:
                perf_drift = await self._check_performance_drift(model_name, metrics)
                if perf_drift:
                    drift_types.append(DriftType.PERFORMANCE_DRIFT)
            
            # Determine overall drift type and severity
            if DriftType.PERFORMANCE_DRIFT in drift_types:
                drift_type = DriftType.CONCEPT_DRIFT
            elif drift_types:
                drift_type = drift_types[0]
            else:
                drift_type = DriftType.NONE
            
            severity = self._calculate_severity(metrics, drift_types)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                drift_type=drift_type,
                severity=severity,
                metrics=metrics,
                affected_features=affected_features
            )
            
            # Create report
            report = DriftReport(
                model_name=model_name,
                detection_timestamp=datetime.now(),
                drift_type=drift_type,
                severity=severity,
                metrics=metrics,
                affected_features=list(set(affected_features)),
                recommendations=recommendations,
                requires_retraining=severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL],
                confidence=self._calculate_confidence(metrics, len(self.prediction_windows[model_name]))
            )
            
            # Store report
            await self._store_drift_report(report)
            
            # Alert if necessary
            if report.requires_retraining:
                await self._send_drift_alert(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error detecting drift: {e}")
            return DriftReport(
                model_name=model_name,
                detection_timestamp=datetime.now(),
                drift_type=DriftType.NONE,
                severity=DriftSeverity.NONE,
                metrics=DriftMetrics(),
                recommendations=["Error during drift detection"]
            )
    
    async def _check_data_drift(
        self,
        model_name: str,
        metrics: DriftMetrics
    ) -> Tuple[bool, List[str]]:
        """Check for data drift in features."""
        drift_detected = False
        affected_features = []
        
        if model_name not in self.baseline_distributions:
            return False, []
        
        for feature_name, current_values in self.feature_windows[model_name].items():
            if len(current_values) < MLConstants.MIN_DRIFT_SAMPLES:  # Need minimum samples
                continue
            
            if feature_name in self.baseline_distributions[model_name]:
                baseline = self.baseline_distributions[model_name][feature_name]
                
                # Kolmogorov-Smirnov test
                ks_stat, p_value = stats.ks_2samp(baseline, list(current_values))
                
                # Population Stability Index (PSI)
                psi = self._calculate_psi(baseline, current_values)
                
                # Wasserstein distance
                wasserstein = stats.wasserstein_distance(baseline, list(current_values))
                
                # Update metrics (keep maximum values)
                metrics.ks_statistic = max(metrics.ks_statistic, ks_stat)
                metrics.ks_p_value = min(metrics.ks_p_value, p_value)
                metrics.psi_score = max(metrics.psi_score, psi)
                metrics.wasserstein_distance = max(metrics.wasserstein_distance, wasserstein)
                
                # Check thresholds
                if p_value < self.thresholds["ks_p_value"] or psi > self.thresholds["psi_warning"]:
                    drift_detected = True
                    affected_features.append(feature_name)
        
        return drift_detected, affected_features
    
    async def _check_prediction_drift(
        self,
        model_name: str,
        metrics: DriftMetrics
    ) -> bool:
        """Check for drift in prediction distributions."""
        if model_name not in self.baseline_distributions:
            return False
        
        current_predictions = list(self.prediction_windows[model_name])
        if len(current_predictions) < MLConstants.MIN_DRIFT_SAMPLES:
            return False
        
        baseline_key = f"{model_name}_predictions"
        if baseline_key in self.baseline_distributions:
            baseline = self.baseline_distributions[baseline_key]
            
            # Calculate distribution change
            if isinstance(current_predictions[0], (int, float)):
                # Numerical predictions
                ks_stat, p_value = stats.ks_2samp(baseline, current_predictions)
                psi = self._calculate_psi(baseline, current_predictions)
                
                metrics.prediction_distribution_change = psi
                
                return p_value < self.thresholds["ks_p_value"] or psi > self.thresholds["psi_warning"]
            else:
                # Categorical predictions
                current_dist = self._get_category_distribution(current_predictions)
                baseline_dist = self._get_category_distribution(baseline)
                
                chi2, p_value = self._chi_square_test(baseline_dist, current_dist)
                
                return p_value < self.thresholds["ks_p_value"]
        
        return False
    
    async def _check_performance_drift(
        self,
        model_name: str,
        metrics: DriftMetrics
    ) -> bool:
        """Check for performance degradation."""
        if model_name not in self.baseline_performance:
            return False
        
        current_performance = list(self.performance_windows[model_name])
        if len(current_performance) < 10:  # Minimum sample size for performance
            return False
        
        baseline_perf = self.baseline_performance[model_name]
        current_avg = np.mean(current_performance)
        
        # Calculate performance delta
        performance_delta = baseline_perf - current_avg
        metrics.performance_delta = performance_delta
        
        # Check if significant degradation
        return performance_delta > self.thresholds["performance_drop"]
    
    def _calculate_psi(self, baseline: List[float], current: List[float]) -> float:
        """Calculate Population Stability Index."""
        try:
            # Create bins from baseline
            min_val = min(min(baseline), min(current))
            max_val = max(max(baseline), max(current))
            bins = np.linspace(min_val, max_val, 11)
            
            # Calculate distributions
            baseline_dist, _ = np.histogram(baseline, bins=bins)
            current_dist, _ = np.histogram(current, bins=bins)
            
            # Normalize
            baseline_dist = baseline_dist / len(baseline)
            current_dist = current_dist / len(current)
            
            # Add small epsilon to avoid log(0)
            epsilon = 1e-10
            baseline_dist = baseline_dist + epsilon
            current_dist = current_dist + epsilon
            
            # Calculate PSI
            psi = np.sum((current_dist - baseline_dist) * np.log(current_dist / baseline_dist))
            
            return float(psi)
            
        except Exception as e:
            logger.error(f"Error calculating PSI: {e}")
            return 0.0
    
    def _calculate_severity(
        self,
        metrics: DriftMetrics,
        drift_types: List[DriftType]
    ) -> DriftSeverity:
        """Calculate overall drift severity."""
        if not drift_types or DriftType.NONE in drift_types:
            return DriftSeverity.NONE
        
        # Performance drift is always high severity
        if DriftType.PERFORMANCE_DRIFT in drift_types:
            if metrics.performance_delta > MLConstants.PERFORMANCE_DROP_THRESHOLD * 2:  # 10% drop
                return DriftSeverity.CRITICAL
            else:
                return DriftSeverity.HIGH
        
        # Check PSI thresholds
        if metrics.psi_score > self.thresholds["psi_critical"]:
            return DriftSeverity.CRITICAL
        elif metrics.psi_score > self.thresholds["psi_warning"]:
            return DriftSeverity.MEDIUM
        
        # Check Wasserstein distance
        if metrics.wasserstein_distance > self.thresholds["wasserstein_critical"]:
            return DriftSeverity.HIGH
        elif metrics.wasserstein_distance > self.thresholds["wasserstein_warning"]:
            return DriftSeverity.MEDIUM
        
        # Default to low if drift detected but not severe
        return DriftSeverity.LOW
    
    def _calculate_confidence(self, metrics: DriftMetrics, sample_size: int) -> float:
        """Calculate confidence in drift detection."""
        # Base confidence on sample size
        size_confidence = min(1.0, sample_size / 100)
        
        # Statistical confidence from p-values
        stat_confidence = 1.0 - metrics.ks_p_value
        
        # Combined confidence
        confidence = (size_confidence + stat_confidence) / 2
        
        return round(confidence, 2)
    
    def _generate_recommendations(
        self,
        drift_type: DriftType,
        severity: DriftSeverity,
        metrics: DriftMetrics,
        affected_features: List[str]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if drift_type == DriftType.NONE:
            recommendations.append("No drift detected. Continue monitoring.")
            return recommendations
        
        # Severity-based recommendations
        if severity == DriftSeverity.CRITICAL:
            recommendations.append("🚨 URGENT: Immediate model retraining required")
            recommendations.append("Consider reverting to previous model version temporarily")
        elif severity == DriftSeverity.HIGH:
            recommendations.append(f"⚠️ Schedule model retraining within {MLConstants.DRIFT_CHECK_HOURS} hours")
            recommendations.append("Increase monitoring frequency")
        
        # Type-specific recommendations
        if drift_type == DriftType.DATA_DRIFT:
            recommendations.append(f"Investigate changes in features: {', '.join(affected_features[:3])}")
            recommendations.append("Check for data pipeline issues or business changes")
            
        elif drift_type == DriftType.CONCEPT_DRIFT:
            recommendations.append("Review and update training data with recent examples")
            recommendations.append("Consider ensemble methods or online learning")
            
        elif drift_type == DriftType.PERFORMANCE_DRIFT:
            recommendations.append(f"Performance degraded by {metrics.performance_delta*100:.1f}%")
            recommendations.append("Analyze prediction errors to identify patterns")
        
        # PSI-based recommendations
        if metrics.psi_score > self.thresholds["psi_warning"]:
            recommendations.append(f"High PSI score ({metrics.psi_score:.3f}) indicates distribution shift")
        
        return recommendations
    
    async def _load_baseline_distributions(self):
        """Load baseline distributions from database."""
        try:
            # Load baseline feature distributions
            response = await self.supabase.table("ml_baseline_distributions").select("*").execute()
            
            if response.data:
                for baseline in response.data:
                    model_name = baseline["model_name"]
                    feature_name = baseline["feature_name"]
                    distribution = json.loads(baseline["distribution"])
                    
                    if model_name not in self.baseline_distributions:
                        self.baseline_distributions[model_name] = {}
                    
                    self.baseline_distributions[model_name][feature_name] = distribution
            
            # Load baseline performance
            perf_response = await self.supabase.table("ml_baseline_performance").select("*").execute()
            
            if perf_response.data:
                for perf in perf_response.data:
                    self.baseline_performance[perf["model_name"]] = perf["baseline_score"]
            
            logger.info(f"Loaded baselines for {len(self.baseline_distributions)} models")
            
        except Exception as e:
            logger.error(f"Error loading baseline distributions: {e}")
    
    async def update_baseline(
        self,
        model_name: str,
        features: Optional[Dict[str, List[float]]] = None,
        predictions: Optional[List[Any]] = None,
        performance_score: Optional[float] = None
    ):
        """
        Update baseline distributions for a model.
        
        Should be called after model retraining or initial deployment.
        """
        try:
            timestamp = datetime.now().isoformat()
            
            # Update feature baselines
            if features:
                if model_name not in self.baseline_distributions:
                    self.baseline_distributions[model_name] = {}
                
                for feature_name, values in features.items():
                    self.baseline_distributions[model_name][feature_name] = values
                    
                    # Store in database
                    await self.supabase.table("ml_baseline_distributions").upsert({
                        "model_name": model_name,
                        "feature_name": feature_name,
                        "distribution": json.dumps(values),
                        "updated_at": timestamp
                    }).execute()
            
            # Update prediction baseline
            if predictions:
                baseline_key = f"{model_name}_predictions"
                self.baseline_distributions[baseline_key] = predictions
                
                await self.supabase.table("ml_baseline_distributions").upsert({
                    "model_name": model_name,
                    "feature_name": "_predictions",
                    "distribution": json.dumps(predictions),
                    "updated_at": timestamp
                }).execute()
            
            # Update performance baseline
            if performance_score is not None:
                self.baseline_performance[model_name] = performance_score
                
                await self.supabase.table("ml_baseline_performance").upsert({
                    "model_name": model_name,
                    "baseline_score": performance_score,
                    "updated_at": timestamp
                }).execute()
            
            logger.info(f"Updated baselines for model: {model_name}")
            
        except Exception as e:
            logger.error(f"Error updating baseline: {e}")
    
    async def _monitor_drift_periodically(self):
        """Periodically check all models for drift."""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                # Get list of active models
                models = list(self.prediction_windows.keys())
                
                for model_name in models:
                    # Check drift for each model
                    report = await self.detect_drift(model_name)
                    
                    if report.drift_type != DriftType.NONE:
                        logger.warning(
                            f"Drift detected in {model_name}: "
                            f"{report.drift_type.value} ({report.severity.value})"
                        )
                
            except Exception as e:
                logger.error(f"Error in drift monitoring: {e}")
    
    async def _store_prediction_tracking(
        self,
        model_name: str,
        features: Dict[str, Any],
        prediction: Any,
        actual: Optional[Any],
        metadata: Optional[Dict[str, Any]]
    ):
        """Store prediction tracking data."""
        try:
            await self.supabase.table("ml_prediction_tracking").insert({
                "model_name": model_name,
                "features": json.dumps(features),
                "prediction": json.dumps(prediction) if not isinstance(prediction, (str, int, float)) else prediction,
                "actual": json.dumps(actual) if actual and not isinstance(actual, (str, int, float)) else actual,
                "metadata": json.dumps(metadata) if metadata else None,
                "created_at": datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Error storing prediction tracking: {e}")
    
    async def _store_drift_report(self, report: DriftReport):
        """Store drift detection report."""
        try:
            await self.supabase.table("ml_drift_reports").insert({
                "model_name": report.model_name,
                "detection_timestamp": report.detection_timestamp.isoformat(),
                "drift_type": report.drift_type.value,
                "severity": report.severity.value,
                "metrics": {
                    "ks_statistic": report.metrics.ks_statistic,
                    "ks_p_value": report.metrics.ks_p_value,
                    "psi_score": report.metrics.psi_score,
                    "wasserstein_distance": report.metrics.wasserstein_distance,
                    "performance_delta": report.metrics.performance_delta
                },
                "affected_features": report.affected_features,
                "recommendations": report.recommendations,
                "requires_retraining": report.requires_retraining,
                "confidence": report.confidence
            }).execute()
        except Exception as e:
            logger.error(f"Error storing drift report: {e}")
    
    async def _send_drift_alert(self, report: DriftReport):
        """Send alert for critical drift detection."""
        try:
            # Log critical alert
            logger.critical(
                f"DRIFT ALERT - Model: {report.model_name}, "
                f"Type: {report.drift_type.value}, "
                f"Severity: {report.severity.value}, "
                f"Action: {'Retraining Required' if report.requires_retraining else 'Monitor'}"
            )
            
            # TODO: Implement actual alerting (email, Slack, etc.)
            
        except Exception as e:
            logger.error(f"Error sending drift alert: {e}")
    
    def _calculate_performance(self, prediction: Any, actual: Any) -> float:
        """Calculate performance metric based on prediction type."""
        try:
            if isinstance(prediction, bool) and isinstance(actual, bool):
                # Binary classification
                return 1.0 if prediction == actual else 0.0
            
            elif isinstance(prediction, (int, float)) and isinstance(actual, (int, float)):
                # Regression - use inverse of relative error
                if actual == 0:
                    return 1.0 if prediction == 0 else 0.0
                error = abs(prediction - actual) / abs(actual)
                return max(0.0, 1.0 - error)
            
            else:
                # Default accuracy
                return 1.0 if prediction == actual else 0.0
                
        except Exception:
            return 0.0
    
    def _get_category_distribution(self, values: List[Any]) -> Dict[Any, float]:
        """Get distribution of categorical values."""
        total = len(values)
        counts = defaultdict(int)
        
        for value in values:
            counts[value] += 1
        
        return {k: v/total for k, v in counts.items()}
    
    def _chi_square_test(
        self,
        expected: Dict[Any, float],
        observed: Dict[Any, float]
    ) -> Tuple[float, float]:
        """Perform chi-square test for categorical distributions."""
        categories = set(expected.keys()) | set(observed.keys())
        
        expected_counts = []
        observed_counts = []
        total_observed = sum(observed.values())
        
        for category in categories:
            expected_counts.append(expected.get(category, 0) * total_observed)
            observed_counts.append(observed.get(category, 0) * total_observed)
        
        # Perform chi-square test
        chi2, p_value = stats.chisquare(observed_counts, expected_counts)
        
        return chi2, p_value
    
    async def get_drift_summary(
        self,
        hours: int = MLConstants.DRIFT_CHECK_HOURS
    ) -> Dict[str, Any]:
        """
        Get summary of drift detection in the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Summary statistics
        """
        try:
            since = datetime.now() - timedelta(hours=hours)
            
            # Get recent drift reports
            response = await self.supabase.table("ml_drift_reports").select("*").gte(
                "detection_timestamp", since.isoformat()
            ).execute()
            
            reports = response.data if response.data else []
            
            # Aggregate by model and severity
            model_summary = defaultdict(lambda: {"total": 0, "by_severity": defaultdict(int)})
            
            for report in reports:
                model_name = report["model_name"]
                severity = report["severity"]
                
                model_summary[model_name]["total"] += 1
                model_summary[model_name]["by_severity"][severity] += 1
            
            # Count models requiring retraining
            models_need_retraining = sum(
                1 for report in reports
                if report.get("requires_retraining", False)
            )
            
            return {
                "time_period_hours": hours,
                "total_drift_detections": len(reports),
                "models_affected": len(model_summary),
                "models_need_retraining": models_need_retraining,
                "by_model": dict(model_summary),
                "recent_critical": [
                    {
                        "model": r["model_name"],
                        "type": r["drift_type"],
                        "timestamp": r["detection_timestamp"]
                    }
                    for r in reports
                    if r["severity"] == "critical"
                ][:5]
            }
            
        except Exception as e:
            logger.error(f"Error getting drift summary: {e}")
            return {"error": str(e)}
    
    async def cleanup(self):
        """
        Cleanup resources and stop background tasks.
        
        This should be called when shutting down the service.
        """
        logger.info("Cleaning up MLDriftDetector")
        
        try:
            # Unregister from task registry
            if self.task_manager:
                registry = get_task_registry()
                await registry.unregister_service("ml_drift_detector")
                self.task_manager = None
            
            logger.info("MLDriftDetector cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during MLDriftDetector cleanup: {e}")


# Usage in imports
import asyncio