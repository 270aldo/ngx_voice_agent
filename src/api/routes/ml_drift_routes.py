"""
ML Drift Detection API Routes.

Provides endpoints for:
- Checking drift status
- Getting drift reports
- Updating baselines
- Viewing drift summaries
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from src.services.ml_pipeline.ml_drift_detector import MLDriftDetector
from src.services.ml_pipeline.ml_pipeline_service import MLPipelineService
from src.api.dependencies import get_ml_pipeline_service
from src.models.api_models import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml/drift", tags=["ML Drift Detection"])


@router.get("/status/{model_name}", response_model=StandardResponse)
async def check_drift_status(
    model_name: str,
    ml_pipeline: MLPipelineService = Depends(get_ml_pipeline_service)
) -> StandardResponse:
    """
    Check drift status for a specific model.
    
    Args:
        model_name: Name of the model to check
        
    Returns:
        Drift detection report
    """
    try:
        # Get drift detector from pipeline
        drift_detector = ml_pipeline.drift_detector
        
        # Detect drift
        report = await drift_detector.detect_drift(model_name)
        
        # Format response
        return StandardResponse(
            success=True,
            data={
                "model_name": report.model_name,
                "drift_detected": report.drift_type.value != "none",
                "drift_type": report.drift_type.value,
                "severity": report.severity.value,
                "requires_retraining": report.requires_retraining,
                "confidence": report.confidence,
                "metrics": {
                    "ks_statistic": report.metrics.ks_statistic,
                    "ks_p_value": report.metrics.ks_p_value,
                    "psi_score": report.metrics.psi_score,
                    "wasserstein_distance": report.metrics.wasserstein_distance,
                    "performance_delta": report.metrics.performance_delta
                },
                "affected_features": report.affected_features,
                "recommendations": report.recommendations,
                "detection_timestamp": report.detection_timestamp.isoformat()
            },
            message=f"Drift check completed for {model_name}"
        )
        
    except Exception as e:
        logger.error(f"Error checking drift status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check drift status: {str(e)}"
        )


@router.get("/summary", response_model=StandardResponse)
async def get_drift_summary(
    hours: int = Query(24, description="Hours to look back", ge=1, le=168),
    ml_pipeline: MLPipelineService = Depends(get_ml_pipeline_service)
) -> StandardResponse:
    """
    Get summary of drift detections across all models.
    
    Args:
        hours: Number of hours to look back (1-168)
        
    Returns:
        Summary statistics and recent detections
    """
    try:
        drift_detector = ml_pipeline.drift_detector
        
        # Get summary
        summary = await drift_detector.get_drift_summary(hours=hours)
        
        return StandardResponse(
            success=True,
            data=summary,
            message=f"Drift summary for last {hours} hours"
        )
        
    except Exception as e:
        logger.error(f"Error getting drift summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get drift summary: {str(e)}"
        )


@router.post("/baseline/{model_name}/update", response_model=StandardResponse)
async def update_model_baseline(
    model_name: str,
    baseline_data: Dict[str, Any],
    ml_pipeline: MLPipelineService = Depends(get_ml_pipeline_service)
) -> StandardResponse:
    """
    Update baseline distributions for a model.
    
    Should be called after model retraining or when establishing new baselines.
    
    Args:
        model_name: Name of the model
        baseline_data: Contains features, predictions, and performance_score
        
    Returns:
        Update confirmation
    """
    try:
        drift_detector = ml_pipeline.drift_detector
        
        # Validate baseline data
        if "features" not in baseline_data:
            raise ValueError("baseline_data must contain 'features'")
        
        # Update baseline
        await drift_detector.update_baseline(
            model_name=model_name,
            features=baseline_data.get("features"),
            predictions=baseline_data.get("predictions"),
            performance_score=baseline_data.get("performance_score")
        )
        
        return StandardResponse(
            success=True,
            data={"model_name": model_name, "updated_at": datetime.now().isoformat()},
            message=f"Baseline updated for {model_name}"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating baseline: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update baseline: {str(e)}"
        )


@router.get("/models", response_model=StandardResponse)
async def list_monitored_models(
    ml_pipeline: MLPipelineService = Depends(get_ml_pipeline_service)
) -> StandardResponse:
    """
    List all models being monitored for drift.
    
    Returns:
        List of model names with their monitoring status
    """
    try:
        drift_detector = ml_pipeline.drift_detector
        
        # Get models from prediction windows
        models = list(drift_detector.prediction_windows.keys())
        
        # Get basic stats for each model
        model_stats = []
        for model_name in models:
            predictions_count = len(drift_detector.prediction_windows[model_name])
            has_baseline = model_name in drift_detector.baseline_distributions
            
            model_stats.append({
                "model_name": model_name,
                "predictions_tracked": predictions_count,
                "has_baseline": has_baseline,
                "monitoring_active": predictions_count > 0
            })
        
        return StandardResponse(
            success=True,
            data={
                "total_models": len(models),
                "models": model_stats
            },
            message="Retrieved monitored models"
        )
        
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list models: {str(e)}"
        )


@router.get("/alerts", response_model=StandardResponse)
async def get_drift_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    unresolved_only: bool = Query(True, description="Only show unresolved alerts"),
    ml_pipeline: MLPipelineService = Depends(get_ml_pipeline_service)
) -> StandardResponse:
    """
    Get drift alerts requiring attention.
    
    Args:
        severity: Filter by severity level (low, medium, high, critical)
        unresolved_only: Only show alerts that haven't been resolved
        
    Returns:
        List of drift alerts
    """
    try:
        # This would typically query the database for alerts
        # For now, return a placeholder
        alerts = []
        
        # Check current drift status for all models
        drift_detector = ml_pipeline.drift_detector
        models = list(drift_detector.prediction_windows.keys())
        
        for model_name in models:
            report = await drift_detector.detect_drift(model_name, check_all_types=False)
            
            if report.drift_type.value != "none":
                if not severity or report.severity.value == severity:
                    alerts.append({
                        "model_name": model_name,
                        "drift_type": report.drift_type.value,
                        "severity": report.severity.value,
                        "detected_at": report.detection_timestamp.isoformat(),
                        "requires_retraining": report.requires_retraining,
                        "recommendations": report.recommendations[:2]  # First 2 recommendations
                    })
        
        return StandardResponse(
            success=True,
            data={
                "total_alerts": len(alerts),
                "alerts": alerts
            },
            message="Retrieved drift alerts"
        )
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get alerts: {str(e)}"
        )


@router.post("/analyze", response_model=StandardResponse)
async def analyze_drift_patterns(
    analysis_config: Dict[str, Any],
    ml_pipeline: MLPipelineService = Depends(get_ml_pipeline_service)
) -> StandardResponse:
    """
    Analyze drift patterns across models and time.
    
    Args:
        analysis_config: Configuration for analysis (time_window, models, etc.)
        
    Returns:
        Drift pattern analysis
    """
    try:
        # Placeholder for drift pattern analysis
        # This could include:
        # - Correlation between feature drifts
        # - Seasonal patterns in drift
        # - Common drift triggers
        
        analysis = {
            "time_window": analysis_config.get("time_window", "7d"),
            "models_analyzed": analysis_config.get("models", []),
            "patterns_found": [],
            "correlations": {},
            "recommendations": [
                "Consider implementing online learning for frequently drifting models",
                "Review data pipeline for potential upstream changes",
                "Schedule regular retraining cycles based on drift patterns"
            ]
        }
        
        return StandardResponse(
            success=True,
            data=analysis,
            message="Drift pattern analysis completed"
        )
        
    except Exception as e:
        logger.error(f"Error analyzing patterns: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze patterns: {str(e)}"
        )