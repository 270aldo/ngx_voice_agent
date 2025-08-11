"""
Metrics endpoint for Prometheus scraping.

This module provides endpoints for Prometheus to scrape metrics
from the NGX Voice Sales Agent.
"""

from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from typing import Dict, Any
import psutil
import asyncio

from src.utils.metrics import (
    system_health,
    api_availability,
    ml_model_accuracy,
    ml_model_version,
    tier_detection_accuracy
)
from src.services.ml_service_registry import MLServiceRegistry
from src.database.supabase_client import get_supabase_client


router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def get_metrics() -> Response:
    """
    Expose metrics in Prometheus format.
    
    This endpoint is scraped by Prometheus to collect metrics.
    """
    # Update dynamic metrics before serving
    await update_dynamic_metrics()
    
    # Generate metrics in Prometheus format
    metrics_data = generate_latest()
    
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@router.get("/ml")
async def get_ml_metrics() -> Dict[str, Any]:
    """
    Get detailed ML metrics in JSON format.
    
    This provides more detailed ML model information than
    the standard Prometheus metrics.
    """
    ml_registry = MLServiceRegistry()
    
    metrics = {
        "models": {},
        "performance": {
            "total_predictions": 0,
            "average_latency_ms": 0,
            "accuracy_scores": {}
        },
        "experiments": {
            "active_experiments": 0,
            "completed_experiments": 0
        }
    }
    
    # Get model information
    for model_name, model_info in ml_registry.get_all_models().items():
        metrics["models"][model_name] = {
            "version": model_info.get("version", "unknown"),
            "last_updated": model_info.get("last_updated", "unknown"),
            "accuracy": model_info.get("accuracy", 0),
            "prediction_count": model_info.get("prediction_count", 0)
        }
    
    # Get performance metrics from database
    try:
        supabase = await supabase_client
        
        # Get prediction statistics
        result = await supabase.from_("prediction_results").select(
            "model_type, prediction_time_ms, is_correct"
        ).execute()
        
        if result.data:
            total_predictions = len(result.data)
            total_latency = sum(r["prediction_time_ms"] for r in result.data if r["prediction_time_ms"])
            
            metrics["performance"]["total_predictions"] = total_predictions
            if total_predictions > 0:
                metrics["performance"]["average_latency_ms"] = total_latency / total_predictions
            
            # Calculate accuracy by model
            model_correct = {}
            model_total = {}
            
            for record in result.data:
                model = record["model_type"]
                if model not in model_correct:
                    model_correct[model] = 0
                    model_total[model] = 0
                
                model_total[model] += 1
                if record["is_correct"]:
                    model_correct[model] += 1
            
            for model in model_total:
                if model_total[model] > 0:
                    accuracy = model_correct[model] / model_total[model]
                    metrics["performance"]["accuracy_scores"][model] = accuracy
                    # Update Prometheus metric
                    ml_model_accuracy.labels(model_type=model).set(accuracy)
        
        # Get experiment statistics
        experiments = await supabase.from_("ml_experiments").select("status").execute()
        if experiments.data:
            metrics["experiments"]["active_experiments"] = sum(
                1 for e in experiments.data if e["status"] == "active"
            )
            metrics["experiments"]["completed_experiments"] = sum(
                1 for e in experiments.data if e["status"] == "completed"
            )
    
    except Exception as e:
        # Log error but don't fail the endpoint
        print(f"Error fetching ML metrics from database: {e}")
    
    return metrics


@router.get("/health/detailed")
async def get_detailed_health() -> Dict[str, Any]:
    """
    Get detailed health metrics in JSON format.
    
    This provides more detailed health information than
    the basic health check endpoint.
    """
    health_score = 100.0
    issues = []
    
    # Check system resources
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    if cpu_percent > 80:
        health_score -= 20
        issues.append(f"High CPU usage: {cpu_percent}%")
    
    if memory.percent > 85:
        health_score -= 20
        issues.append(f"High memory usage: {memory.percent}%")
    
    if disk.percent > 90:
        health_score -= 10
        issues.append(f"Low disk space: {disk.percent}% used")
    
    # Check external services
    services_status = await check_external_services()
    for service, status in services_status.items():
        if not status["available"]:
            health_score -= 30
            issues.append(f"{service} unavailable: {status['error']}")
    
    # Update Prometheus metric
    system_health.set(health_score)
    
    return {
        "health_score": health_score,
        "status": "healthy" if health_score >= 70 else "degraded" if health_score >= 40 else "unhealthy",
        "issues": issues,
        "resources": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / (1024**3)
        },
        "services": services_status
    }


async def update_dynamic_metrics():
    """Update metrics that need to be calculated dynamically."""
    try:
        # Update system health
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        # Simple health score calculation
        health_score = 100
        if cpu_percent > 80:
            health_score -= 20
        if memory.percent > 85:
            health_score -= 20
        
        system_health.set(health_score)
        
        # Update service availability
        services = await check_external_services()
        for service, status in services.items():
            api_availability.labels(service=service).set(
                1.0 if status["available"] else 0.0
            )
    
    except Exception as e:
        print(f"Error updating dynamic metrics: {e}")


async def check_external_services() -> Dict[str, Dict[str, Any]]:
    """Check availability of external services."""
    import httpx
    
    services = {}
    
    # Check OpenAI
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://api.openai.com/v1/models")
            services["openai"] = {
                "available": response.status_code == 200,
                "error": None if response.status_code == 200 else f"HTTP {response.status_code}"
            }
    except Exception as e:
        services["openai"] = {
            "available": False,
            "error": str(e)
        }
    
    # Check Supabase
    try:
        supabase = await supabase_client
        # Simple query to test connection
        result = await supabase.from_("conversations").select("id").limit(1).execute()
        services["supabase"] = {
            "available": True,
            "error": None
        }
    except Exception as e:
        services["supabase"] = {
            "available": False,
            "error": str(e)
        }
    
    # Check ElevenLabs (mock for now as we don't want to make unnecessary API calls)
    services["elevenlabs"] = {
        "available": True,  # Assume available
        "error": None
    }
    
    return services