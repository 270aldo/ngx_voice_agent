"""
Centralized constants for the NGX Voice Sales Agent.

This module contains all magic numbers, thresholds, and configuration values
used throughout the application. Centralizing these values improves maintainability
and makes it easier to tune the system.
"""

from typing import Final


# Time Constants (in seconds)
class TimeConstants:
    """Time-related constants in seconds."""
    SECOND: Final[int] = 1
    MINUTE: Final[int] = 60
    HOUR: Final[int] = 3600
    DAY: Final[int] = 86400
    WEEK: Final[int] = 604800
    
    # Specific timeouts
    DEFAULT_TIMEOUT: Final[int] = 30
    LONG_TIMEOUT: Final[int] = 120
    API_TIMEOUT: Final[int] = 60
    CACHE_DEFAULT_TTL: Final[int] = 300  # 5 minutes
    CACHE_SHORT_TTL: Final[int] = 60    # 1 minute
    CACHE_LONG_TTL: Final[int] = 600    # 10 minutes
    JWT_ROTATION_CHECK: Final[int] = 3600  # 1 hour
    HEALTH_CHECK_INTERVAL: Final[int] = 30
    TASK_CLEANUP_INTERVAL: Final[int] = 60


# ML/AI Constants
class MLConstants:
    """Machine Learning related constants."""
    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD: Final[float] = 0.8
    MEDIUM_CONFIDENCE_THRESHOLD: Final[float] = 0.6
    LOW_CONFIDENCE_THRESHOLD: Final[float] = 0.3
    
    # Model parameters
    MIN_TRAINING_SAMPLES: Final[int] = 100
    BATCH_SIZE: Final[int] = 32
    MAX_SEQUENCE_LENGTH: Final[int] = 512
    EMBEDDING_DIM: Final[int] = 768
    
    # Drift detection
    KS_TEST_SIGNIFICANCE: Final[float] = 0.05
    PSI_WARNING_THRESHOLD: Final[float] = 0.1
    PSI_CRITICAL_THRESHOLD: Final[float] = 0.25
    PERFORMANCE_DROP_THRESHOLD: Final[float] = 0.05
    MIN_DRIFT_SAMPLES: Final[int] = 30
    DRIFT_CHECK_HOURS: Final[int] = 24
    
    # A/B Testing
    MIN_EXPERIMENT_SAMPLE_SIZE: Final[int] = 100
    CONFIDENCE_LEVEL: Final[float] = 0.95
    AUTO_DEPLOY_THRESHOLD: Final[float] = 0.95
    EXPERIMENT_MIN_DURATION_HOURS: Final[int] = 24


# API/HTTP Constants
class APIConstants:
    """API and HTTP related constants."""
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: Final[int] = 60
    RATE_LIMIT_PER_HOUR: Final[int] = 1000
    
    # Pagination
    DEFAULT_PAGE_SIZE: Final[int] = 20
    MAX_PAGE_SIZE: Final[int] = 100
    
    # Response codes
    HTTP_OK: Final[int] = 200
    HTTP_CREATED: Final[int] = 201
    HTTP_NO_CONTENT: Final[int] = 204
    HTTP_NOT_MODIFIED: Final[int] = 304
    HTTP_BAD_REQUEST: Final[int] = 400
    HTTP_UNAUTHORIZED: Final[int] = 401
    HTTP_FORBIDDEN: Final[int] = 403
    HTTP_NOT_FOUND: Final[int] = 404
    HTTP_CONFLICT: Final[int] = 409
    HTTP_UNPROCESSABLE_ENTITY: Final[int] = 422
    HTTP_TOO_MANY_REQUESTS: Final[int] = 429
    HTTP_INTERNAL_SERVER_ERROR: Final[int] = 500
    HTTP_SERVICE_UNAVAILABLE: Final[int] = 503
    
    # Request limits
    MAX_REQUEST_SIZE_MB: Final[int] = 10
    MAX_UPLOAD_SIZE_MB: Final[int] = 50
    MAX_JSON_DEPTH: Final[int] = 10


# Cache Constants
class CacheConstants:
    """Cache related constants."""
    # Cache namespaces
    HTTP_RESPONSE_NAMESPACE: Final[str] = "http_response"
    CONVERSATION_NAMESPACE: Final[str] = "conversation"
    ML_PREDICTION_NAMESPACE: Final[str] = "ml_prediction"
    
    # Cache settings
    DEFAULT_TTL_SECONDS: Final[int] = 300
    MAX_ENTRY_SIZE_MB: Final[int] = 10
    COMPRESSION_THRESHOLD_BYTES: Final[int] = 1024
    STALE_TTL_SECONDS: Final[int] = 3600
    MAX_TAGS_PER_ENTRY: Final[int] = 20
    CACHE_KEY_MAX_LENGTH: Final[int] = 250


# Circuit Breaker Constants
class CircuitBreakerConstants:
    """Circuit breaker related constants."""
    FAILURE_THRESHOLD: Final[int] = 5
    SUCCESS_THRESHOLD: Final[int] = 2
    TIMEOUT_SECONDS: Final[int] = 60
    HALF_OPEN_MAX_CALLS: Final[int] = 3
    
    # State durations
    OPEN_STATE_DURATION: Final[int] = 60
    HALF_OPEN_STATE_DURATION: Final[int] = 30


# Database Constants
class DatabaseConstants:
    """Database related constants."""
    # Connection pool
    MIN_POOL_SIZE: Final[int] = 5
    MAX_POOL_SIZE: Final[int] = 20
    CONNECTION_TIMEOUT: Final[int] = 30
    
    # Query limits
    MAX_BATCH_SIZE: Final[int] = 1000
    DEFAULT_QUERY_LIMIT: Final[int] = 100
    MAX_QUERY_LIMIT: Final[int] = 1000
    
    # Retry settings
    MAX_RETRIES: Final[int] = 3
    RETRY_DELAY_SECONDS: Final[float] = 0.5
    RETRY_BACKOFF_FACTOR: Final[float] = 2.0


# Conversation Constants
class ConversationConstants:
    """Conversation related constants."""
    # Message limits
    MAX_MESSAGE_LENGTH: Final[int] = 4000
    MAX_CONVERSATION_MESSAGES: Final[int] = 100
    MAX_CONTEXT_MESSAGES: Final[int] = 10
    
    # Timeouts
    IDLE_TIMEOUT_MINUTES: Final[int] = 30
    SESSION_TIMEOUT_HOURS: Final[int] = 24
    
    # Sales phases durations (estimates in seconds)
    GREETING_PHASE_DURATION: Final[int] = 60
    DISCOVERY_PHASE_DURATION: Final[int] = 300
    PRESENTATION_PHASE_DURATION: Final[int] = 600
    OBJECTION_PHASE_DURATION: Final[int] = 300
    CLOSING_PHASE_DURATION: Final[int] = 180


# System Health Constants
class HealthConstants:
    """System health monitoring constants."""
    # Thresholds
    CPU_THRESHOLD_PERCENT: Final[float] = 80.0
    MEMORY_THRESHOLD_PERCENT: Final[float] = 85.0
    DISK_THRESHOLD_PERCENT: Final[float] = 90.0
    RESPONSE_TIME_THRESHOLD_MS: Final[float] = 1000.0
    
    # Check intervals
    HEALTH_CHECK_INTERVAL_SECONDS: Final[int] = 30
    METRICS_COLLECTION_INTERVAL: Final[int] = 60


# Business Logic Constants
class BusinessConstants:
    """Business logic related constants."""
    # Tier pricing (in dollars)
    TIER_ESSENTIAL_PRICE: Final[int] = 79
    TIER_PRO_PRICE: Final[int] = 149
    TIER_ELITE_PRICE: Final[int] = 199
    TIER_PREMIUM_PRICE: Final[int] = 3997
    
    # Lead scoring
    HIGH_QUALITY_LEAD_SCORE: Final[float] = 0.8
    MEDIUM_QUALITY_LEAD_SCORE: Final[float] = 0.5
    LOW_QUALITY_LEAD_SCORE: Final[float] = 0.3
    
    # Conversion thresholds
    HIGH_CONVERSION_PROBABILITY: Final[float] = 0.7
    MEDIUM_CONVERSION_PROBABILITY: Final[float] = 0.4
    LOW_CONVERSION_PROBABILITY: Final[float] = 0.2
    
    # ROI multipliers
    MIN_ROI_MULTIPLIER: Final[float] = 2.0
    TARGET_ROI_MULTIPLIER: Final[float] = 10.0
    MAX_ROI_MULTIPLIER: Final[float] = 100.0


# Security Constants
class SecurityConstants:
    """Security related constants."""
    # Token settings
    ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = 30
    REFRESH_TOKEN_EXPIRE_DAYS: Final[int] = 7
    PASSWORD_RESET_TOKEN_HOURS: Final[int] = 24
    
    # Password requirements
    MIN_PASSWORD_LENGTH: Final[int] = 8
    MAX_PASSWORD_LENGTH: Final[int] = 128
    PASSWORD_SALT_ROUNDS: Final[int] = 12
    
    # Rate limiting
    MAX_LOGIN_ATTEMPTS: Final[int] = 5
    LOCKOUT_DURATION_MINUTES: Final[int] = 15
    
    # Session settings
    MAX_CONCURRENT_SESSIONS: Final[int] = 5
    SESSION_IDLE_TIMEOUT_MINUTES: Final[int] = 30


# Validation Constants
class ValidationConstants:
    """Input validation constants."""
    # String lengths
    MIN_NAME_LENGTH: Final[int] = 2
    MAX_NAME_LENGTH: Final[int] = 100
    MAX_EMAIL_LENGTH: Final[int] = 255
    MAX_PHONE_LENGTH: Final[int] = 20
    MAX_URL_LENGTH: Final[int] = 2000
    
    # Numeric ranges
    MIN_AGE: Final[int] = 18
    MAX_AGE: Final[int] = 120
    MIN_PRICE: Final[float] = 0.01
    MAX_PRICE: Final[float] = 1000000.0
    
    # File uploads
    MAX_FILE_SIZE_MB: Final[int] = 10
    ALLOWED_IMAGE_EXTENSIONS: Final[tuple] = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
    ALLOWED_DOCUMENT_EXTENSIONS: Final[tuple] = ('.pdf', '.doc', '.docx', '.txt')


# Monitoring Constants
class MonitoringConstants:
    """Monitoring and observability constants."""
    # Metrics
    METRICS_FLUSH_INTERVAL: Final[int] = 60
    METRICS_RETENTION_DAYS: Final[int] = 30
    
    # Logging
    LOG_ROTATION_SIZE_MB: Final[int] = 100
    LOG_RETENTION_DAYS: Final[int] = 30
    MAX_LOG_FILES: Final[int] = 10
    
    # Tracing
    TRACE_SAMPLE_RATE: Final[float] = 0.1
    TRACE_RETENTION_HOURS: Final[int] = 72


# Retry Constants
class RetryConstants:
    """Retry policy constants."""
    DEFAULT_MAX_ATTEMPTS: Final[int] = 3
    DEFAULT_BASE_DELAY: Final[float] = 1.0
    DEFAULT_MAX_DELAY: Final[float] = 60.0
    DEFAULT_EXPONENTIAL_BASE: Final[float] = 2.0
    DEFAULT_JITTER: Final[bool] = True


# Feature Flags (could be moved to config)
class FeatureFlags:
    """Feature flags for gradual rollout."""
    ENABLE_ML_DRIFT_DETECTION: Final[bool] = True
    ENABLE_HTTP_CACHING: Final[bool] = True
    ENABLE_CIRCUIT_BREAKER: Final[bool] = True
    ENABLE_A_B_TESTING: Final[bool] = True
    ENABLE_ADVANCED_EMPATHY: Final[bool] = True
    ENABLE_ASYNC_TASK_MANAGER: Final[bool] = True
    ENABLE_INPUT_VALIDATION: Final[bool] = True
    ENABLE_ERROR_SANITIZATION: Final[bool] = True


# Export all constant classes
__all__ = [
    'TimeConstants',
    'MLConstants',
    'APIConstants',
    'CacheConstants',
    'CircuitBreakerConstants',
    'DatabaseConstants',
    'ConversationConstants',
    'HealthConstants',
    'BusinessConstants',
    'SecurityConstants',
    'ValidationConstants',
    'MonitoringConstants',
    'RetryConstants',
    'FeatureFlags'
]