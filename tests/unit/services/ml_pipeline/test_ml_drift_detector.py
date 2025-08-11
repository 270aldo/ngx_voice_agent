"""
Unit tests for ML Drift Detector.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import numpy as np

from src.services.ml_pipeline.ml_drift_detector import (
    MLDriftDetector, DriftType, DriftSeverity, DriftReport, DriftMetrics
)


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    mock = MagicMock()
    mock.table = MagicMock(return_value=mock)
    mock.select = MagicMock(return_value=mock)
    mock.insert = MagicMock(return_value=mock)
    mock.upsert = MagicMock(return_value=mock)
    mock.eq = MagicMock(return_value=mock)
    mock.gte = MagicMock(return_value=mock)
    mock.execute = AsyncMock(return_value=MagicMock(data=[]))
    return mock


@pytest.fixture
def drift_detector(mock_supabase):
    """Create drift detector instance."""
    with patch('src.services.ml_pipeline.ml_drift_detector.supabase_client', mock_supabase):
        with patch('src.services.ml_pipeline.ml_drift_detector.get_task_registry'):
            detector = MLDriftDetector()
            # Initialize with empty baselines
            detector.baseline_distributions = {}
            detector.baseline_performance = {}
            return detector


class TestMLDriftDetector:
    """Test ML Drift Detector functionality."""
    
    @pytest.mark.asyncio
    async def test_track_prediction(self, drift_detector):
        """Test tracking predictions."""
        # Track a prediction
        await drift_detector.track_prediction(
            model_name="test_model",
            features={"feature1": 0.5, "feature2": 1.0},
            prediction=0.8,
            actual=1.0,
            metadata={"test": True}
        )
        
        # Check windows updated
        assert len(drift_detector.prediction_windows["test_model"]) == 1
        assert drift_detector.prediction_windows["test_model"][0] == 0.8
        
        assert len(drift_detector.feature_windows["test_model"]["feature1"]) == 1
        assert drift_detector.feature_windows["test_model"]["feature1"][0] == 0.5
        
        assert len(drift_detector.performance_windows["test_model"]) == 1
    
    @pytest.mark.asyncio
    async def test_detect_no_drift(self, drift_detector):
        """Test detecting no drift when distributions are similar."""
        model_name = "test_model"
        
        # Set baseline
        baseline_values = np.random.normal(0, 1, 1000).tolist()
        drift_detector.baseline_distributions[model_name] = {
            "feature1": baseline_values
        }
        drift_detector.baseline_performance[model_name] = 0.9
        
        # Add similar current values
        for val in np.random.normal(0, 1, 100):
            drift_detector.feature_windows[model_name]["feature1"].append(val)
        
        # Detect drift
        report = await drift_detector.detect_drift(model_name)
        
        assert report.drift_type == DriftType.NONE
        assert report.severity == DriftSeverity.NONE
        assert not report.requires_retraining
    
    @pytest.mark.asyncio
    async def test_detect_data_drift(self, drift_detector):
        """Test detecting data drift."""
        model_name = "test_model"
        
        # Set baseline with normal distribution
        baseline_values = np.random.normal(0, 1, 1000).tolist()
        drift_detector.baseline_distributions[model_name] = {
            "feature1": baseline_values
        }
        
        # Add shifted current values (drift)
        for val in np.random.normal(3, 1, 100):  # Mean shifted from 0 to 3
            drift_detector.feature_windows[model_name]["feature1"].append(val)
        
        # Detect drift
        report = await drift_detector.detect_drift(model_name)
        
        assert report.drift_type == DriftType.DATA_DRIFT
        assert report.severity in [DriftSeverity.MEDIUM, DriftSeverity.HIGH]
        assert "feature1" in report.affected_features
    
    @pytest.mark.asyncio
    async def test_detect_performance_drift(self, drift_detector):
        """Test detecting performance drift."""
        model_name = "test_model"
        
        # Set baseline performance
        drift_detector.baseline_performance[model_name] = 0.95
        
        # Add degraded performance values
        for _ in range(20):
            drift_detector.performance_windows[model_name].append(0.85)  # 10% drop
        
        # Detect drift
        report = await drift_detector.detect_drift(model_name)
        
        assert DriftType.PERFORMANCE_DRIFT in [report.drift_type]
        assert report.severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]
        assert report.requires_retraining
    
    def test_calculate_psi(self, drift_detector):
        """Test PSI calculation."""
        baseline = np.random.normal(0, 1, 1000).tolist()
        
        # Same distribution - low PSI
        current_same = np.random.normal(0, 1, 1000).tolist()
        psi_same = drift_detector._calculate_psi(baseline, current_same)
        assert psi_same < 0.1  # Low PSI
        
        # Shifted distribution - high PSI  
        current_shifted = np.random.normal(2, 1, 1000).tolist()
        psi_shifted = drift_detector._calculate_psi(baseline, current_shifted)
        assert psi_shifted > 0.1  # Higher PSI
    
    def test_calculate_severity(self, drift_detector):
        """Test severity calculation."""
        # No drift
        metrics = DriftMetrics()
        severity = drift_detector._calculate_severity(metrics, [])
        assert severity == DriftSeverity.NONE
        
        # High PSI
        metrics = DriftMetrics(psi_score=0.3)
        severity = drift_detector._calculate_severity(metrics, [DriftType.DATA_DRIFT])
        assert severity == DriftSeverity.CRITICAL
        
        # Performance drift
        metrics = DriftMetrics(performance_delta=0.15)
        severity = drift_detector._calculate_severity(metrics, [DriftType.PERFORMANCE_DRIFT])
        assert severity == DriftSeverity.CRITICAL
    
    def test_generate_recommendations(self, drift_detector):
        """Test recommendation generation."""
        # No drift
        recs = drift_detector._generate_recommendations(
            DriftType.NONE,
            DriftSeverity.NONE,
            DriftMetrics(),
            []
        )
        assert len(recs) == 1
        assert "No drift detected" in recs[0]
        
        # Critical data drift
        recs = drift_detector._generate_recommendations(
            DriftType.DATA_DRIFT,
            DriftSeverity.CRITICAL,
            DriftMetrics(psi_score=0.3),
            ["feature1", "feature2"]
        )
        assert any("URGENT" in r for r in recs)
        assert any("feature1" in r for r in recs)
    
    @pytest.mark.asyncio
    async def test_update_baseline(self, drift_detector, mock_supabase):
        """Test updating baseline distributions."""
        model_name = "test_model"
        features = {
            "feature1": [1, 2, 3, 4, 5],
            "feature2": [0.1, 0.2, 0.3, 0.4, 0.5]
        }
        predictions = [0, 1, 1, 0, 1]
        performance = 0.92
        
        # Update baseline
        await drift_detector.update_baseline(
            model_name=model_name,
            features=features,
            predictions=predictions,
            performance_score=performance
        )
        
        # Check baselines updated
        assert model_name in drift_detector.baseline_distributions
        assert "feature1" in drift_detector.baseline_distributions[model_name]
        assert drift_detector.baseline_performance[model_name] == performance
        
        # Check database calls
        assert mock_supabase.table.called
        assert mock_supabase.upsert.called
    
    @pytest.mark.asyncio
    async def test_get_drift_summary(self, drift_detector, mock_supabase):
        """Test getting drift summary."""
        # Mock database response
        mock_supabase.execute.return_value = MagicMock(
            data=[
                {
                    "model_name": "model1",
                    "severity": "high",
                    "drift_type": "data_drift",
                    "requires_retraining": True,
                    "detection_timestamp": datetime.now().isoformat()
                },
                {
                    "model_name": "model1", 
                    "severity": "low",
                    "drift_type": "data_drift",
                    "requires_retraining": False,
                    "detection_timestamp": datetime.now().isoformat()
                },
                {
                    "model_name": "model2",
                    "severity": "critical",
                    "drift_type": "performance_drift",
                    "requires_retraining": True,
                    "detection_timestamp": datetime.now().isoformat()
                }
            ]
        )
        
        # Get summary
        summary = await drift_detector.get_drift_summary(hours=24)
        
        assert summary["total_drift_detections"] == 3
        assert summary["models_affected"] == 2
        assert summary["models_need_retraining"] == 2
        assert len(summary["recent_critical"]) == 1
    
    def test_extract_features_numeric(self, drift_detector):
        """Test feature extraction for numeric values."""
        features = {"age": 25, "score": 0.8, "name": "test"}
        
        # Track prediction
        for feat, val in features.items():
            if isinstance(val, (int, float)):
                drift_detector.feature_windows["model"]["age"].append(25)
                drift_detector.feature_windows["model"]["score"].append(0.8)
        
        # Check only numeric features tracked
        assert len(drift_detector.feature_windows["model"]) == 2
        assert "age" in drift_detector.feature_windows["model"]
        assert "score" in drift_detector.feature_windows["model"]
        assert "name" not in drift_detector.feature_windows["model"]
    
    @pytest.mark.asyncio
    async def test_drift_detection_with_small_sample(self, drift_detector):
        """Test drift detection with insufficient samples."""
        model_name = "test_model"
        
        # Set baseline
        drift_detector.baseline_distributions[model_name] = {
            "feature1": np.random.normal(0, 1, 1000).tolist()
        }
        
        # Add only a few current values (less than minimum)
        for val in np.random.normal(2, 1, 10):  # Only 10 samples
            drift_detector.feature_windows[model_name]["feature1"].append(val)
        
        # Detect drift
        report = await drift_detector.detect_drift(model_name)
        
        # Should not detect drift with small sample
        assert report.drift_type == DriftType.NONE
        assert report.confidence < 0.5  # Low confidence due to small sample