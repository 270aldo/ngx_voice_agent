"""
Centralized configuration management for NGX Voice Sales Agent.

This module provides a single source of truth for all configuration
settings, with proper validation, type safety, and environment support.
"""

import os
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import Field, field_validator, SecretStr, ConfigDict, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Application environments."""
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """
    Application settings with validation and type safety.
    
    All settings can be overridden via environment variables.
    """
    
    # Application
    app_name: str = Field(default="NGX Voice Sales Agent", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: Environment = Field(default=Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # API Configuration
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT", ge=1, le=65535)
    api_workers: int = Field(default=1, env="API_WORKERS", ge=1)
    
    # Security
    jwt_secret: Optional[SecretStr] = Field(default=None, env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # CORS
    allowed_origins_str: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        alias="ALLOWED_ORIGINS"
    )
    allow_credentials: bool = Field(default=True, env="ALLOW_CREDENTIALS")
    allow_methods_str: str = Field(
        default="GET,POST,PUT,DELETE,OPTIONS",
        alias="ALLOW_METHODS"
    )
    allow_headers_str: str = Field(
        default="Authorization,Content-Type,Accept",
        alias="ALLOW_HEADERS"
    )
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(default=200, env="RATE_LIMIT_PER_MINUTE")  # Increased for beta
    rate_limit_per_hour: int = Field(default=5000, env="RATE_LIMIT_PER_HOUR")    # Increased for beta
    rate_limit_whitelist_ips_str: str = Field(default="", alias="RATE_LIMIT_WHITELIST_IPS")
    
    # CSRF Protection
    csrf_protection_enabled: bool = Field(default=True, env="CSRF_PROTECTION_ENABLED")
    csrf_secret_key: Optional[SecretStr] = Field(default=None, env="CSRF_SECRET_KEY")
    
    # Database
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE", ge=1)
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW", ge=0)
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    
    # Supabase
    supabase_url: Optional[str] = Field(default=None, env="SUPABASE_URL")
    supabase_anon_key: Optional[SecretStr] = Field(default=None, env="SUPABASE_ANON_KEY")
    supabase_service_role_key: Optional[SecretStr] = Field(default=None, env="SUPABASE_SERVICE_ROLE_KEY")
    
    # Redis
    redis_url: Optional[str] = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_pool_size: int = Field(default=10, env="REDIS_POOL_SIZE")
    redis_decode_responses: bool = Field(default=True, env="REDIS_DECODE_RESPONSES")
    
    # External APIs
    openai_api_key: Optional[SecretStr] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.85, env="OPENAI_TEMPERATURE", ge=0, le=2)
    openai_max_tokens: int = Field(default=2500, env="OPENAI_MAX_TOKENS", ge=1)
    openai_presence_penalty: float = Field(default=-0.2, env="OPENAI_PRESENCE_PENALTY", ge=-2, le=2)
    openai_frequency_penalty: float = Field(default=0.3, env="OPENAI_FREQUENCY_PENALTY", ge=-2, le=2)
    openai_top_p: float = Field(default=0.95, env="OPENAI_TOP_P", ge=0, le=1)
    
    elevenlabs_api_key: Optional[SecretStr] = Field(default=None, env="ELEVENLABS_API_KEY")
    elevenlabs_voice_id: str = Field(default="21m00Tcm4TlvDq8ikWAM", env="ELEVENLABS_VOICE_ID")
    
    # Logging
    log_level: LogLevel = Field(default=LogLevel.INFO, env="LOG_LEVEL")
    log_file: Optional[str] = Field(default="logs/api.log", env="LOG_FILE")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    log_include_stack_info: bool = Field(default=False, env="LOG_INCLUDE_STACK_INFO")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    enable_tracing: bool = Field(default=True, env="ENABLE_TRACING")
    jaeger_agent_host: str = Field(default="localhost", env="JAEGER_AGENT_HOST")
    jaeger_agent_port: int = Field(default=6831, env="JAEGER_AGENT_PORT")
    
    # Business Logic
    max_conversation_duration_minutes: int = Field(default=30, env="MAX_CONVERSATION_DURATION_MINUTES")
    max_messages_per_conversation: int = Field(default=100, env="MAX_MESSAGES_PER_CONVERSATION")
    conversation_cooldown_hours: int = Field(default=48, env="CONVERSATION_COOLDOWN_HOURS")
    
    # ML/AI Settings
    ml_model_cache_ttl: int = Field(default=3600, env="ML_MODEL_CACHE_TTL")
    ml_experiment_sample_rate: float = Field(default=0.1, env="ML_EXPERIMENT_SAMPLE_RATE", ge=0, le=1)
    ml_learning_enabled: bool = Field(default=True, env="ML_LEARNING_ENABLED")
    
    # Feature Flags
    feature_voice_synthesis: bool = Field(default=True, env="FEATURE_VOICE_SYNTHESIS")
    feature_ml_optimization: bool = Field(default=True, env="FEATURE_ML_OPTIMIZATION")
    feature_ab_testing: bool = Field(default=True, env="FEATURE_AB_TESTING")
    feature_trial_system: bool = Field(default=True, env="FEATURE_TRIAL_SYSTEM")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,  # Allow alias usage
        extra='ignore'  # Ignore extra environment variables
    )
        
    # Computed fields for List properties
    @computed_field
    @property
    def allowed_origins(self) -> List[str]:
        """Parse allowed origins from CSV string."""
        return [origin.strip() for origin in self.allowed_origins_str.split(",") if origin.strip()]
    
    @computed_field
    @property
    def allow_methods(self) -> List[str]:
        """Parse allowed methods from CSV string."""
        return [method.strip() for method in self.allow_methods_str.split(",") if method.strip()]
    
    @computed_field
    @property
    def allow_headers(self) -> List[str]:
        """Parse allowed headers from CSV string."""
        return [header.strip() for header in self.allow_headers_str.split(",") if header.strip()]
    
    @computed_field
    @property
    def rate_limit_whitelist_ips(self) -> List[str]:
        """Parse whitelist IPs from CSV string."""
        if not self.rate_limit_whitelist_ips_str:
            return []
        return [ip.strip() for ip in self.rate_limit_whitelist_ips_str.split(",") if ip.strip()]
    
    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: Optional[SecretStr], info) -> Optional[SecretStr]:
        """Validate JWT secret is set in production."""
        env = info.data.get("environment") if hasattr(info, 'data') else None
        if env == Environment.PRODUCTION and not v:
            raise ValueError("JWT_SECRET must be set in production environment")
        return v
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: Optional[str], info) -> Optional[str]:
        """Validate database URL is set in production."""
        env = info.data.get("environment") if hasattr(info, 'data') else None
        if env == Environment.PRODUCTION and not v:
            raise ValueError("DATABASE_URL must be set in production environment")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == Environment.DEVELOPMENT
    
    @property
    def is_test(self) -> bool:
        """Check if running in test."""
        return self.environment == Environment.TEST
    
    def get_database_url(self, masked: bool = False) -> str:
        """
        Get database URL with optional masking.
        
        Args:
            masked: Whether to mask sensitive parts
            
        Returns:
            Database URL
        """
        if not self.database_url:
            return ""
        
        if masked and self.is_production:
            # Mask password in production
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(self.database_url)
            if parsed.password:
                masked_password = f"{parsed.password[:2]}{'*' * 6}"
                netloc = f"{parsed.username}:{masked_password}@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                return urlunparse((
                    parsed.scheme,
                    netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))
        
        return self.database_url or ""
    
    def get_redis_url(self, masked: bool = False) -> str:
        """Get Redis URL with optional masking."""
        if not self.redis_url:
            return ""
        
        if masked and self.is_production:
            # Mask password if present
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(self.redis_url)
            if parsed.password:
                masked_password = f"{parsed.password[:2]}{'*' * 6}"
                netloc = f"{parsed.username}:{masked_password}@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                return urlunparse((
                    parsed.scheme,
                    netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))
        
        return self.redis_url or ""
    
    def dict_safe(self) -> Dict[str, Any]:
        """
        Get settings as dictionary with secrets masked.
        
        Returns:
            Settings dict with sensitive values replaced
        """
        data = self.dict()
        
        # Mask sensitive fields
        sensitive_fields = [
            "jwt_secret",
            "supabase_anon_key",
            "supabase_service_role_key",
            "openai_api_key",
            "elevenlabs_api_key",
        ]
        
        for field in sensitive_fields:
            if field in data and data[field]:
                data[field] = "***configured***"
        
        # Mask URLs
        if data.get("database_url"):
            data["database_url"] = self.get_database_url(masked=True)
        
        if data.get("redis_url"):
            data["redis_url"] = self.get_redis_url(masked=True)
        
        return data
    
    # Compatibility properties for backward compatibility with uppercase names
    @property
    def JWT_SECRET_KEY(self) -> str:
        """Backward compatibility: get JWT secret."""
        if self.jwt_secret:
            return self.jwt_secret.get_secret_value()
        return "your-secret-key-change-in-production"
    
    @property
    def JWT_ALGORITHM(self) -> str:
        """Backward compatibility: get JWT algorithm."""
        return self.jwt_algorithm
    
    @property
    def JWT_ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        """Backward compatibility: get JWT access token expiration."""
        return self.jwt_access_token_expire_minutes
    
    @property
    def JWT_REFRESH_TOKEN_EXPIRE_DAYS(self) -> int:
        """Backward compatibility: get JWT refresh token expiration."""
        return self.jwt_refresh_token_expire_days
    
    @property
    def SUPABASE_URL(self) -> str:
        """Backward compatibility: get Supabase URL."""
        return self.supabase_url or ""
    
    @property
    def SUPABASE_ANON_KEY(self) -> str:
        """Backward compatibility: get Supabase anon key."""
        if self.supabase_anon_key:
            return self.supabase_anon_key.get_secret_value()
        return ""
    
    @property
    def SUPABASE_SERVICE_KEY(self) -> str:
        """Backward compatibility: get Supabase service role key."""
        if self.supabase_service_role_key:
            return self.supabase_service_role_key.get_secret_value()
        return ""
    
    @property
    def OPENAI_API_KEY(self) -> str:
        """Backward compatibility: get OpenAI API key."""
        if self.openai_api_key:
            return self.openai_api_key.get_secret_value()
        return ""
    
    @property
    def OPENAI_MODEL(self) -> str:
        """Backward compatibility: get OpenAI model."""
        return self.openai_model
    
    @property
    def OPENAI_MAX_TOKENS(self) -> int:
        """Backward compatibility: get OpenAI max tokens."""
        return self.openai_max_tokens
    
    @property
    def OPENAI_TEMPERATURE(self) -> float:
        """Backward compatibility: get OpenAI temperature."""
        return self.openai_temperature
    
    @property
    def ELEVENLABS_API_KEY(self) -> Optional[str]:
        """Backward compatibility: get ElevenLabs API key."""
        if self.elevenlabs_api_key:
            return self.elevenlabs_api_key.get_secret_value()
        return None
    
    @property
    def ELEVENLABS_VOICE_ID(self) -> str:
        """Backward compatibility: get ElevenLabs voice ID."""
        return self.elevenlabs_voice_id
    
    @property
    def REDIS_URL(self) -> str:
        """Backward compatibility: get Redis URL."""
        return self.redis_url or "redis://localhost:6379"
    
    @property
    def REDIS_PASSWORD(self) -> Optional[str]:
        """Backward compatibility: get Redis password."""
        # Extract password from Redis URL if present
        if self.redis_url and "@" in self.redis_url:
            from urllib.parse import urlparse
            parsed = urlparse(self.redis_url)
            return parsed.password
        return None
    
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """Backward compatibility: get allowed origins."""
        return [origin.strip() for origin in self.allowed_origins_str.split(",") if origin.strip()]
    
    @property
    def API_PREFIX(self) -> str:
        """Backward compatibility: get API prefix."""
        return self.api_v1_prefix
    
    @property
    def APP_NAME(self) -> str:
        """Backward compatibility: get app name."""
        return self.app_name
    
    @property
    def APP_VERSION(self) -> str:
        """Backward compatibility: get app version."""
        return self.app_version
    
    @property
    def DEBUG(self) -> bool:
        """Backward compatibility: get debug flag."""
        return self.debug
    
    @property
    def ENVIRONMENT(self) -> str:
        """Backward compatibility: get environment."""
        return self.environment.value
    
    @property
    def BCRYPT_ROUNDS(self) -> int:
        """Backward compatibility: get bcrypt rounds."""
        return 12  # Default value from old config
    
    @property
    def RATE_LIMIT_REQUESTS(self) -> int:
        """Backward compatibility: get rate limit requests."""
        return self.rate_limit_per_minute
    
    @property
    def RATE_LIMIT_PERIOD(self) -> int:
        """Backward compatibility: get rate limit period."""
        return 60  # 1 minute in seconds
    
    @property
    def CSRF_PROTECTION_ENABLED(self) -> bool:
        """Backward compatibility: get CSRF protection flag."""
        return self.csrf_protection_enabled
    
    @property
    def CSRF_SECRET_KEY(self) -> Optional[str]:
        """Backward compatibility: get CSRF secret key."""
        if self.csrf_secret_key:
            return self.csrf_secret_key.get_secret_value()
        return None
    
    @property
    def WS_HEARTBEAT_INTERVAL(self) -> int:
        """Backward compatibility: get WebSocket heartbeat interval."""
        return 30  # Default from old config
    
    @property
    def WS_CONNECTION_TIMEOUT(self) -> int:
        """Backward compatibility: get WebSocket connection timeout."""
        return 60  # Default from old config
    
    @property
    def CACHE_TTL_SECONDS(self) -> int:
        """Backward compatibility: get cache TTL."""
        return self.ml_model_cache_ttl
    
    @property
    def CACHE_MAX_SIZE(self) -> int:
        """Backward compatibility: get cache max size."""
        return 1000  # Default from old config
    
    @property
    def ENABLE_METRICS(self) -> bool:
        """Backward compatibility: get metrics flag."""
        return self.enable_metrics
    
    @property
    def METRICS_PORT(self) -> int:
        """Backward compatibility: get metrics port."""
        return self.metrics_port
    
    @property
    def LOG_LEVEL(self) -> str:
        """Backward compatibility: get log level."""
        return self.log_level.value
    
    @property
    def LOG_FORMAT(self) -> str:
        """Backward compatibility: get log format."""
        return "json"  # Default from old config
    
    @property
    def ENABLE_ML_PIPELINE(self) -> bool:
        """Backward compatibility: get ML pipeline flag."""
        return self.ml_learning_enabled
    
    @property
    def ENABLE_A_B_TESTING(self) -> bool:
        """Backward compatibility: get A/B testing flag."""
        return self.feature_ab_testing
    
    @property
    def ENABLE_VOICE_SUPPORT(self) -> bool:
        """Backward compatibility: get voice support flag."""
        return self.feature_voice_synthesis
    
    def get_cors_origins(self) -> List[str]:
        """Backward compatibility: get CORS origins based on environment."""
        if self.is_production:
            return [
                "https://app.ngx.com",
                "https://ngx.com", 
                "https://dashboard.ngx.com"
            ]
        return [origin.strip() for origin in self.allowed_origins_str.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings instance
    """
    return Settings()


# Global settings instance
settings = get_settings()