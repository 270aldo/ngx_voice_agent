"""
Custom metrics collection for Prometheus monitoring.

This module provides metrics for monitoring the NGX Voice Sales Agent,
including API performance, ML model metrics, and business KPIs.
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from functools import wraps
import time
from typing import Callable, Any


# API Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'handler', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'handler'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# Conversation Metrics
conversations_total = Counter(
    'conversations_total',
    'Total number of conversations started',
    ['source', 'tier']
)

conversations_active = Gauge(
    'conversations_active',
    'Number of active conversations'
)

conversations_duration_seconds = Histogram(
    'conversations_duration_seconds',
    'Conversation duration in seconds',
    ['tier', 'outcome'],
    buckets=(30, 60, 120, 300, 600, 900, 1200, 1800, 3600)
)

messages_total = Counter(
    'messages_total',
    'Total messages exchanged',
    ['direction', 'tier']  # direction: user/agent
)

# ML Model Metrics
ml_predictions_total = Counter(
    'ml_predictions_total',
    'Total ML predictions made',
    ['model_type', 'prediction_type']
)

ml_prediction_duration_seconds = Histogram(
    'ml_prediction_duration_seconds',
    'Time taken for ML predictions',
    ['model_type'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0)
)

ml_model_accuracy = Gauge(
    'ml_model_accuracy',
    'Current ML model accuracy',
    ['model_type']
)

ml_model_version = Info(
    'ml_model_info',
    'Information about deployed ML models'
)

# Business Metrics
conversion_success_total = Counter(
    'conversion_success_total',
    'Successful conversions',
    ['tier', 'archetype']
)

conversion_value_dollars = Counter(
    'conversion_value_dollars',
    'Total conversion value in dollars',
    ['tier']
)

tier_detection_accuracy = Gauge(
    'tier_detection_accuracy',
    'Accuracy of tier detection'
)

abandonment_total = Counter(
    'abandonment_total',
    'Conversations abandoned',
    ['stage', 'reason']
)

# External Service Metrics
openai_api_calls_total = Counter(
    'openai_api_calls_total',
    'Total OpenAI API calls',
    ['endpoint', 'status']
)

openai_api_duration_seconds = Histogram(
    'openai_api_duration_seconds',
    'OpenAI API call duration',
    ['endpoint'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

openai_tokens_used_total = Counter(
    'openai_tokens_used_total',
    'Total OpenAI tokens consumed',
    ['model', 'type']  # type: prompt/completion
)

elevenlabs_api_calls_total = Counter(
    'elevenlabs_api_calls_total',
    'Total ElevenLabs API calls',
    ['voice', 'status']
)

supabase_queries_total = Counter(
    'supabase_queries_total',
    'Total Supabase queries',
    ['table', 'operation', 'status']
)

supabase_query_duration_seconds = Histogram(
    'supabase_query_duration_seconds',
    'Supabase query duration',
    ['table', 'operation'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0)
)

# System Health Metrics
system_health = Gauge(
    'system_health',
    'Overall system health score (0-100)'
)

api_availability = Gauge(
    'api_availability',
    'API availability status',
    ['service']
)


# Decorators for automatic metric collection
def track_request_metrics(handler: str):
    """
    Decorator to automatically track HTTP request metrics.
    
    Args:
        handler: The name of the handler/endpoint
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            status = 500  # Default to error
            
            try:
                result = await func(*args, **kwargs)
                # Extract status from response
                if hasattr(result, 'status_code'):
                    status = result.status_code
                elif isinstance(result, dict) and 'status_code' in result:
                    status = result['status_code']
                else:
                    status = 200  # Assume success if no status
                
                return result
            except Exception as e:
                status = 500
                raise
            finally:
                # Record metrics
                method = kwargs.get('request', {}).get('method', 'UNKNOWN')
                http_requests_total.labels(
                    method=method,
                    handler=handler,
                    status=str(status)
                ).inc()
                
                duration = time.time() - start_time
                http_request_duration_seconds.labels(
                    method=method,
                    handler=handler
                ).observe(duration)
        
        return wrapper
    return decorator


def track_ml_prediction(model_type: str):
    """
    Decorator to track ML prediction metrics.
    
    Args:
        model_type: The type of ML model being used
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Track prediction
                ml_predictions_total.labels(
                    model_type=model_type,
                    prediction_type=kwargs.get('prediction_type', 'unknown')
                ).inc()
                
                # Track duration
                duration = time.time() - start_time
                ml_prediction_duration_seconds.labels(
                    model_type=model_type
                ).observe(duration)
                
                return result
            except Exception as e:
                # Track failed predictions
                ml_predictions_total.labels(
                    model_type=model_type,
                    prediction_type='error'
                ).inc()
                raise
        
        return wrapper
    return decorator


def track_external_api_call(service: str, endpoint: str):
    """
    Decorator to track external API calls.
    
    Args:
        service: The external service name (openai, elevenlabs, etc.)
        endpoint: The specific endpoint being called
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            status = 'error'
            
            try:
                result = await func(*args, **kwargs)
                status = 'success'
                return result
            except Exception as e:
                status = 'error'
                raise
            finally:
                duration = time.time() - start_time
                
                if service == 'openai':
                    openai_api_calls_total.labels(
                        endpoint=endpoint,
                        status=status
                    ).inc()
                    openai_api_duration_seconds.labels(
                        endpoint=endpoint
                    ).observe(duration)
                elif service == 'elevenlabs':
                    elevenlabs_api_calls_total.labels(
                        voice=kwargs.get('voice', 'default'),
                        status=status
                    ).inc()
        
        return wrapper
    return decorator


# Helper functions for manual metric updates
def track_conversation_started(source: str, tier: str):
    """Track a new conversation start."""
    conversations_total.labels(source=source, tier=tier).inc()
    conversations_active.inc()


def track_conversation_ended(tier: str, outcome: str, duration: float):
    """Track conversation end."""
    conversations_active.dec()
    conversations_duration_seconds.labels(tier=tier, outcome=outcome).observe(duration)


def track_conversion(tier: str, archetype: str, value: float):
    """Track successful conversion."""
    conversion_success_total.labels(tier=tier, archetype=archetype).inc()
    conversion_value_dollars.labels(tier=tier).inc(value)


def track_message(direction: str, tier: str):
    """Track message exchange."""
    messages_total.labels(direction=direction, tier=tier).inc()


def update_model_accuracy(model_type: str, accuracy: float):
    """Update ML model accuracy metric."""
    ml_model_accuracy.labels(model_type=model_type).set(accuracy)


def update_system_health(score: float):
    """Update overall system health score (0-100)."""
    system_health.set(max(0, min(100, score)))