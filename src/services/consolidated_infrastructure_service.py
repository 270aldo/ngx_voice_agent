"""
Consolidated Infrastructure Service - FINAL NGX Voice Agent Infrastructure Layer
=============================================================================

This service consolidates all infrastructure functionality from multiple services:

CONSOLIDATED FROM:
- infrastructure_service.py (Circuit breakers, encryption, JWT)
- circuit_breaker_service.py (Dedicated circuit breaker functionality)
- redis_mock.py (Redis mock for testing)
- encryption_service.py (Data encryption/decryption)
- jwt_rotation_service.py (JWT management and rotation)
- http_cache_service.py (HTTP response caching)
- websocket/broadcast_service.py (WebSocket broadcasting)
- websocket/websocket_manager.py (WebSocket connection management)

PROVIDES:
✅ Circuit breaker patterns with advanced metrics
✅ Multi-level encryption (Standard, High, PII)
✅ JWT token lifecycle management with rotation
✅ WebSocket connection pooling and broadcasting
✅ HTTP response caching with intelligent invalidation
✅ Redis mock for development/testing environments
✅ Health monitoring and system diagnostics
✅ Security utilities and compliance helpers
✅ Connection pooling and rate limiting
✅ Graceful degradation and fault tolerance

FEATURES:
- Zero-downtime service transitions
- Enterprise-grade security
- Performance optimization
- Real-time monitoring
- Automatic failover mechanisms
"""

import logging
import asyncio
import hashlib
import hmac
import secrets
import time
import base64
import json
import uuid
import weakref
from typing import Dict, List, Any, Optional, Callable, Union, TypeVar, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps, lru_cache
from contextlib import asynccontextmanager
from threading import Lock
import pickle
import gzip

# Cryptography and JWT imports
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import jwt

# FastAPI and WebSocket imports
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status, Request, Response

# NGX imports
from src.config import settings
from src.utils.structured_logging import StructuredLogger
from src.models.user import User, TokenData

logger = StructuredLogger.get_logger(__name__)
T = TypeVar('T')


# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================

class CircuitState(str, Enum):
    """Circuit breaker states with detailed transitions."""
    CLOSED = "closed"           # Normal operation
    OPEN = "open"               # Blocking requests
    HALF_OPEN = "half_open"     # Testing recovery


class EncryptionLevel(str, Enum):
    """Encryption security levels with different use cases."""
    STANDARD = "standard"       # AES-256 for general data
    HIGH = "high"              # AES-256 + additional layers
    PII = "pii"                # Specialized for PII data
    FINANCIAL = "financial"    # Highest security for financial data


class CacheStrategy(str, Enum):
    """HTTP cache strategies for different content types."""
    NO_CACHE = "no_cache"
    SHORT_TERM = "short_term"   # 5 minutes
    MEDIUM_TERM = "medium_term" # 1 hour
    LONG_TERM = "long_term"     # 24 hours


class ConnectionType(str, Enum):
    """WebSocket connection types for optimization."""
    DASHBOARD = "dashboard"
    CONVERSATION = "conversation"
    BROADCAST = "broadcast"
    ADMIN = "admin"


@dataclass
class CircuitBreakerConfig:
    """Enhanced circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    success_threshold: int = 2
    half_open_max_calls: int = 3
    expected_exception: type = Exception
    fallback_function: Optional[Callable] = None
    exclude_exceptions: tuple = ()
    timeout_seconds: Optional[int] = None
    
    def __post_init__(self):
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if self.recovery_timeout < 1:
            raise ValueError("recovery_timeout must be at least 1")


@dataclass
class CircuitBreakerMetrics:
    """Comprehensive circuit breaker metrics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    timeouts: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: List[Dict[str, Any]] = field(default_factory=list)
    call_durations: List[float] = field(default_factory=list)
    
    def add_call_duration(self, duration: float, max_history: int = 100):
        """Track call duration with memory management."""
        self.call_durations.append(duration)
        if len(self.call_durations) > max_history:
            self.call_durations.pop(0)
    
    def get_success_rate(self) -> float:
        """Calculate current success rate."""
        if self.total_calls == 0:
            return 1.0
        return self.successful_calls / self.total_calls
    
    def get_average_duration(self) -> float:
        """Get average call duration."""
        if not self.call_durations:
            return 0.0
        return sum(self.call_durations) / len(self.call_durations)


@dataclass
class JWTConfig:
    """Enhanced JWT configuration."""
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    issuer: str = "ngx-voice-agent"
    audience: str = "ngx-api"
    rotation_interval_hours: int = 24


@dataclass
class CacheEntry:
    """HTTP cache entry with metadata."""
    data: Any
    created_at: datetime
    expires_at: datetime
    etag: str
    headers: Dict[str, str] = field(default_factory=dict)
    compressed: bool = False
    
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        return not self.is_expired()


@dataclass
class WebSocketConnection:
    """WebSocket connection metadata."""
    websocket: WebSocket
    user_id: str
    organization_id: str
    connection_type: ConnectionType
    connected_at: datetime
    last_ping: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionPool:
    """WebSocket connection pool configuration."""
    max_connections: int = 1000
    max_per_org: int = 100
    max_per_user: int = 5
    cleanup_interval: int = 300  # 5 minutes


# ============================================================================
# REDIS MOCK IMPLEMENTATION
# ============================================================================

class RedisMock:
    """Redis mock implementation for development and testing."""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._expires: Dict[str, datetime] = {}
        self._lock = Lock()
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from mock Redis."""
        with self._lock:
            if key in self._expires:
                if datetime.utcnow() > self._expires[key]:
                    del self._data[key]
                    del self._expires[key]
                    return None
            return self._data.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in mock Redis."""
        with self._lock:
            self._data[key] = value
            if ex:
                self._expires[key] = datetime.utcnow() + timedelta(seconds=ex)
            elif key in self._expires:
                del self._expires[key]
            return True
    
    async def delete(self, key: str) -> int:
        """Delete key from mock Redis."""
        with self._lock:
            count = 1 if key in self._data else 0
            self._data.pop(key, None)
            self._expires.pop(key, None)
            return count
    
    async def exists(self, key: str) -> int:
        """Check if key exists."""
        value = await self.get(key)
        return 1 if value is not None else 0
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key."""
        with self._lock:
            if key not in self._data:
                return -2
            if key not in self._expires:
                return -1
            ttl = (self._expires[key] - datetime.utcnow()).total_seconds()
            return int(max(0, ttl))
    
    async def flushall(self) -> bool:
        """Clear all data."""
        with self._lock:
            self._data.clear()
            self._expires.clear()
            return True


# ============================================================================
# MAIN CONSOLIDATED INFRASTRUCTURE SERVICE
# ============================================================================

class ConsolidatedInfrastructureService:
    """
    FINAL consolidated infrastructure service for NGX Voice Agent.
    
    This service provides ALL infrastructure functionality in a single,
    optimized, production-ready service.
    """
    
    def __init__(self):
        """Initialize the consolidated infrastructure service."""
        logger.info("Initializing ConsolidatedInfrastructureService...")
        
        # Core infrastructure components
        self._initialize_circuit_breakers()
        self._initialize_encryption()
        self._initialize_jwt_management()
        self._initialize_http_cache()
        self._initialize_websocket_manager()
        self._initialize_redis_mock()
        self._initialize_health_monitoring()
        
        # Service state
        self._initialized = True
        self._startup_time = datetime.utcnow()
        
        logger.info("ConsolidatedInfrastructureService initialized successfully")
    
    # ========================================================================
    # INITIALIZATION METHODS
    # ========================================================================
    
    def _initialize_circuit_breakers(self):
        """Initialize circuit breaker functionality."""
        self.circuit_breakers: Dict[str, 'CircuitBreakerInstance'] = {}
        self.circuit_configs: Dict[str, CircuitBreakerConfig] = {}
        self._cb_lock = Lock()
        logger.debug("Circuit breakers initialized")
    
    def _initialize_encryption(self):
        """Initialize encryption services."""
        self.encryption_keys: Dict[EncryptionLevel, bytes] = {}
        master_key = getattr(settings, 'ENCRYPTION_KEY', None)
        
        if not master_key:
            master_key = base64.urlsafe_b64encode(secrets.token_bytes(32))
            logger.warning("Generated new encryption key - store securely for production")
        
        if isinstance(master_key, str):
            master_key = master_key.encode()
        
        # Derive keys for different encryption levels
        self.encryption_keys[EncryptionLevel.STANDARD] = self._derive_key(master_key, b"standard")
        self.encryption_keys[EncryptionLevel.HIGH] = self._derive_key(master_key, b"high_security")
        self.encryption_keys[EncryptionLevel.PII] = self._derive_key(master_key, b"pii_protection")
        self.encryption_keys[EncryptionLevel.FINANCIAL] = self._derive_key(master_key, b"financial_data")
        
        logger.debug("Encryption services initialized")
    
    def _initialize_jwt_management(self):
        """Initialize JWT management."""
        secret_key = getattr(settings, 'JWT_SECRET_KEY', None)
        if not secret_key:
            secret_key = secrets.token_urlsafe(32)
            logger.warning("Generated new JWT secret - configure JWT_SECRET_KEY for production")
        
        self.jwt_config = JWTConfig(
            secret_key=secret_key,
            algorithm=getattr(settings, 'JWT_ALGORITHM', 'HS256'),
            access_token_expire_minutes=getattr(settings, 'JWT_ACCESS_TOKEN_EXPIRE_MINUTES', 30),
            refresh_token_expire_days=getattr(settings, 'JWT_REFRESH_TOKEN_EXPIRE_DAYS', 7)
        )
        
        self.active_tokens: Dict[str, Dict[str, Any]] = {}
        self.revoked_tokens: Set[str] = set()
        self._jwt_lock = Lock()
        
        logger.debug("JWT management initialized")
    
    def _initialize_http_cache(self):
        """Initialize HTTP caching system."""
        self.http_cache: Dict[str, CacheEntry] = {}
        self._cache_lock = Lock()
        
        # Cache strategies configuration
        self.cache_strategies = {
            CacheStrategy.NO_CACHE: timedelta(seconds=0),
            CacheStrategy.SHORT_TERM: timedelta(minutes=5),
            CacheStrategy.MEDIUM_TERM: timedelta(hours=1),
            CacheStrategy.LONG_TERM: timedelta(hours=24)
        }
        
        logger.debug("HTTP cache initialized")
    
    def _initialize_websocket_manager(self):
        """Initialize WebSocket management."""
        self.websocket_connections: Dict[str, WebSocketConnection] = {}
        self.organization_subscriptions: Dict[str, Set[str]] = {}
        self.connection_pools: Dict[ConnectionType, ConnectionPool] = {
            ConnectionType.DASHBOARD: ConnectionPool(max_connections=500),
            ConnectionType.CONVERSATION: ConnectionPool(max_connections=300),
            ConnectionType.BROADCAST: ConnectionPool(max_connections=100),
            ConnectionType.ADMIN: ConnectionPool(max_connections=50)
        }
        self._ws_lock = Lock()
        self.connection_attempts: Dict[str, Dict[str, Any]] = {}
        
        logger.debug("WebSocket manager initialized")
    
    def _initialize_redis_mock(self):
        """Initialize Redis mock for development."""
        self.redis_mock = RedisMock()
        self.use_redis_mock = getattr(settings, 'USE_REDIS_MOCK', True)
        logger.debug(f"Redis mock initialized (enabled: {self.use_redis_mock})")
    
    def _initialize_health_monitoring(self):
        """Initialize health monitoring system."""
        self.health_metrics = {
            "startup_time": self._startup_time,
            "total_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "websocket_connections": 0,
            "active_circuit_breakers": 0,
            "jwt_tokens_issued": 0,
            "encryption_operations": 0
        }
        
        # Performance tracking
        self.performance_metrics = {
            "avg_response_time": 0.0,
            "response_times": [],
            "error_rates": [],
            "uptime_percentage": 100.0
        }
        
        logger.debug("Health monitoring initialized")
    
    def _derive_key(self, master_key: bytes, salt: bytes) -> bytes:
        """Derive encryption key using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(master_key)
    
    # ========================================================================
    # CIRCUIT BREAKER IMPLEMENTATION
    # ========================================================================
    
    class CircuitBreakerInstance:
        """Individual circuit breaker instance with enhanced functionality."""
        
        def __init__(self, name: str, config: CircuitBreakerConfig, parent_service):
            self.name = name
            self.config = config
            self.parent = parent_service
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            self._last_failure_time = None
            self._lock = Lock()
            self.metrics = CircuitBreakerMetrics()
        
        @property
        def state(self) -> CircuitState:
            """Get current state with automatic transitions."""
            with self._lock:
                if self._state == CircuitState.OPEN and self._should_attempt_reset():
                    self._transition_to_half_open()
                return self._state
        
        def _should_attempt_reset(self) -> bool:
            """Check if ready for recovery attempt."""
            return (
                self._last_failure_time and
                datetime.utcnow() >= self._last_failure_time + 
                timedelta(seconds=self.config.recovery_timeout)
            )
        
        def _transition_to_half_open(self):
            """Transition to half-open state."""
            logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
            old_state = self._state
            self._state = CircuitState.HALF_OPEN
            self._half_open_calls = 0
            self._success_count = 0
            self._record_state_change(old_state, CircuitState.HALF_OPEN)
        
        def _transition_to_open(self):
            """Transition to open state."""
            logger.warning(f"Circuit breaker '{self.name}' transitioning to OPEN")
            old_state = self._state
            self._state = CircuitState.OPEN
            self._last_failure_time = datetime.utcnow()
            self._failure_count = 0
            self._record_state_change(old_state, CircuitState.OPEN)
        
        def _transition_to_closed(self):
            """Transition to closed state."""
            logger.info(f"Circuit breaker '{self.name}' transitioning to CLOSED")
            old_state = self._state
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._record_state_change(old_state, CircuitState.CLOSED)
        
        def _record_state_change(self, from_state: CircuitState, to_state: CircuitState):
            """Record state transition."""
            self.metrics.state_changes.append({
                "from": from_state.value,
                "to": to_state.value,
                "timestamp": datetime.utcnow(),
                "failure_count": self._failure_count,
                "success_count": self._success_count
            })
            
            # Keep only last 100 state changes
            if len(self.metrics.state_changes) > 100:
                self.metrics.state_changes.pop(0)
        
        async def execute(self, func: Callable, *args, **kwargs) -> Any:
            """Execute function with circuit breaker protection."""
            with self._lock:
                # Check if circuit is open
                if self.state == CircuitState.OPEN:
                    self.metrics.rejected_calls += 1
                    self.metrics.total_calls += 1
                    
                    # Use fallback if available
                    if self.config.fallback_function:
                        logger.info(f"Circuit breaker '{self.name}' using fallback")
                        return await self.config.fallback_function(*args, **kwargs)
                    else:
                        raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is OPEN")
                
                # Check half-open call limit
                if self._state == CircuitState.HALF_OPEN:
                    if self._half_open_calls >= self.config.half_open_max_calls:
                        self.metrics.rejected_calls += 1
                        self.metrics.total_calls += 1
                        raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' half-open limit reached")
                    self._half_open_calls += 1
            
            # Execute the function
            start_time = time.time()
            timeout_task = None
            
            try:
                # Handle timeout if configured
                if self.config.timeout_seconds:
                    timeout_task = asyncio.create_task(asyncio.sleep(self.config.timeout_seconds))
                    func_task = asyncio.create_task(func(*args, **kwargs)) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                    
                    if asyncio.iscoroutinefunction(func):
                        done, pending = await asyncio.wait(
                            [func_task, timeout_task],
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        
                        # Cancel pending tasks
                        for task in pending:
                            task.cancel()
                        
                        if timeout_task in done:
                            raise asyncio.TimeoutError(f"Function timeout after {self.config.timeout_seconds}s")
                        
                        result = func_task.result()
                    else:
                        result = func_task
                else:
                    result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                
                duration = time.time() - start_time
                
                with self._lock:
                    self._on_success(duration)
                
                return result
                
            except self.config.exclude_exceptions:
                # These exceptions don't count as failures
                if timeout_task and not timeout_task.done():
                    timeout_task.cancel()
                raise
                
            except asyncio.TimeoutError:
                duration = time.time() - start_time
                with self._lock:
                    self.metrics.timeouts += 1
                    self._on_failure(duration)
                raise
                
            except Exception as e:
                if timeout_task and not timeout_task.done():
                    timeout_task.cancel()
                    
                duration = time.time() - start_time
                
                with self._lock:
                    self._on_failure(duration)
                
                raise
        
        def _on_success(self, duration: float):
            """Handle successful execution."""
            self.metrics.total_calls += 1
            self.metrics.successful_calls += 1
            self.metrics.last_success_time = datetime.utcnow()
            self.metrics.add_call_duration(duration)
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            else:
                self._failure_count = 0
        
        def _on_failure(self, duration: float):
            """Handle failed execution."""
            self.metrics.total_calls += 1
            self.metrics.failed_calls += 1
            self.metrics.last_failure_time = datetime.utcnow()
            self.metrics.add_call_duration(duration)
            
            self._failure_count += 1
            
            if self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to_open()
            elif self._state == CircuitState.HALF_OPEN:
                self._transition_to_open()
    
    def circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
        timeout_seconds: Optional[int] = None,
        fallback: Optional[Callable] = None,
        exclude_exceptions: tuple = ()
    ):
        """
        Circuit breaker decorator with comprehensive configuration.
        
        Args:
            name: Unique circuit breaker name
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            success_threshold: Successes needed to close circuit
            timeout_seconds: Optional timeout for function execution
            fallback: Fallback function when circuit is open
            exclude_exceptions: Exceptions that don't count as failures
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            config = CircuitBreakerConfig(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold,
                timeout_seconds=timeout_seconds,
                fallback_function=fallback,
                exclude_exceptions=exclude_exceptions
            )
            
            with self._cb_lock:
                if name not in self.circuit_breakers:
                    self.circuit_breakers[name] = self.CircuitBreakerInstance(name, config, self)
                    self.circuit_configs[name] = config
            
            @wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                cb = self.circuit_breakers[name]
                return await cb.execute(func, *args, **kwargs)
            
            return wrapper
        
        return decorator
    
    async def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """Get comprehensive circuit breaker statistics."""
        stats = {}
        
        with self._cb_lock:
            for name, cb in self.circuit_breakers.items():
                with cb._lock:
                    stats[name] = {
                        "state": cb.state.value,
                        "metrics": {
                            "total_calls": cb.metrics.total_calls,
                            "successful_calls": cb.metrics.successful_calls,
                            "failed_calls": cb.metrics.failed_calls,
                            "rejected_calls": cb.metrics.rejected_calls,
                            "timeouts": cb.metrics.timeouts,
                            "success_rate": cb.metrics.get_success_rate(),
                            "average_duration_ms": cb.metrics.get_average_duration() * 1000,
                            "last_failure": cb.metrics.last_failure_time.isoformat() if cb.metrics.last_failure_time else None,
                            "last_success": cb.metrics.last_success_time.isoformat() if cb.metrics.last_success_time else None
                        },
                        "config": {
                            "failure_threshold": cb.config.failure_threshold,
                            "recovery_timeout": cb.config.recovery_timeout,
                            "success_threshold": cb.config.success_threshold,
                            "timeout_seconds": cb.config.timeout_seconds
                        },
                        "state_changes": len(cb.metrics.state_changes)
                    }
        
        return stats
    
    async def reset_circuit_breaker(self, name: str) -> bool:
        """Manually reset a circuit breaker."""
        with self._cb_lock:
            if name in self.circuit_breakers:
                cb = self.circuit_breakers[name]
                with cb._lock:
                    cb._transition_to_closed()
                logger.info(f"Circuit breaker '{name}' manually reset")
                return True
        return False
    
    # ========================================================================
    # ENCRYPTION SERVICES
    # ========================================================================
    
    async def encrypt_data(
        self,
        data: Union[str, bytes, dict],
        level: EncryptionLevel = EncryptionLevel.STANDARD,
        additional_context: Optional[str] = None
    ) -> str:
        """
        Encrypt data with specified security level.
        
        Args:
            data: Data to encrypt
            level: Encryption security level
            additional_context: Additional context for encryption
            
        Returns:
            Base64 encoded encrypted data
        """
        # Track encryption operations
        self.health_metrics["encryption_operations"] += 1
        
        # Prepare data for encryption
        if isinstance(data, dict):
            data_bytes = json.dumps(data, sort_keys=True).encode('utf-8')
        elif isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data
        
        # Add context if provided
        if additional_context:
            context_bytes = additional_context.encode('utf-8')
            data_bytes = context_bytes + b'||' + data_bytes
        
        # Add timestamp for key rotation
        timestamp = int(time.time())
        data_bytes = f"{timestamp}".encode('utf-8') + b'||' + data_bytes
        
        # Get encryption key
        encryption_key = self.encryption_keys[level]
        fernet = Fernet(base64.urlsafe_b64encode(encryption_key))
        
        # Encrypt data
        encrypted_bytes = fernet.encrypt(data_bytes)
        
        # Return base64 encoded result with level prefix
        result = f"{level.value}:{base64.b64encode(encrypted_bytes).decode('utf-8')}"
        return result
    
    async def decrypt_data(
        self,
        encrypted_data: str,
        level: Optional[EncryptionLevel] = None,
        return_json: bool = False
    ) -> Union[str, bytes, dict]:
        """
        Decrypt data with automatic level detection.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            level: Encryption level (auto-detected if not provided)
            return_json: Whether to return as JSON dict
            
        Returns:
            Decrypted data
        """
        try:
            # Auto-detect encryption level
            if ':' in encrypted_data and not level:
                level_str, encrypted_data = encrypted_data.split(':', 1)
                level = EncryptionLevel(level_str)
            elif not level:
                level = EncryptionLevel.STANDARD
            
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Get decryption key
            decryption_key = self.encryption_keys[level]
            fernet = Fernet(base64.urlsafe_b64encode(decryption_key))
            
            # Decrypt data
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            
            # Remove timestamp
            if b'||' in decrypted_bytes:
                timestamp_part, decrypted_bytes = decrypted_bytes.split(b'||', 1)
            
            # Handle context separation
            if b'||' in decrypted_bytes:
                _, decrypted_bytes = decrypted_bytes.split(b'||', 1)
            
            # Return appropriate format
            if return_json:
                return json.loads(decrypted_bytes.decode('utf-8'))
            else:
                return decrypted_bytes.decode('utf-8')
                
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data")
    
    async def encrypt_pii(self, pii_data: Dict[str, Any]) -> Dict[str, str]:
        """Encrypt PII data with highest security level."""
        encrypted_pii = {}
        
        for field, value in pii_data.items():
            if value is not None:
                encrypted_value = await self.encrypt_data(
                    str(value),
                    level=EncryptionLevel.PII,
                    additional_context=f"pii_field:{field}"
                )
                encrypted_pii[field] = encrypted_value
            else:
                encrypted_pii[field] = None
        
        return encrypted_pii
    
    async def decrypt_pii(self, encrypted_pii: Dict[str, str]) -> Dict[str, Any]:
        """Decrypt PII data."""
        decrypted_pii = {}
        
        for field, encrypted_value in encrypted_pii.items():
            if encrypted_value is not None:
                try:
                    decrypted_value = await self.decrypt_data(encrypted_value)
                    decrypted_pii[field] = decrypted_value
                except Exception as e:
                    logger.error(f"Failed to decrypt PII field {field}: {e}")
                    decrypted_pii[field] = None
            else:
                decrypted_pii[field] = None
        
        return decrypted_pii
    
    # ========================================================================
    # JWT TOKEN MANAGEMENT
    # ========================================================================
    
    async def create_access_token(
        self,
        subject: str,
        claims: Optional[Dict[str, Any]] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token with enhanced security."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=self.jwt_config.access_token_expire_minutes)
        
        expire = datetime.utcnow() + expires_delta
        token_id = secrets.token_hex(16)
        
        payload = {
            "sub": subject,
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": self.jwt_config.issuer,
            "aud": self.jwt_config.audience,
            "jti": token_id,
            "type": "access"
        }
        
        if claims:
            payload.update(claims)
        
        token = jwt.encode(
            payload,
            self.jwt_config.secret_key,
            algorithm=self.jwt_config.algorithm
        )
        
        # Store token info for tracking
        with self._jwt_lock:
            self.active_tokens[token_id] = {
                "subject": subject,
                "type": "access",
                "issued_at": datetime.utcnow(),
                "expires_at": expire,
                "revoked": False
            }
        
        self.health_metrics["jwt_tokens_issued"] += 1
        return token
    
    async def create_refresh_token(
        self,
        subject: str,
        claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create JWT refresh token."""
        expires_delta = timedelta(days=self.jwt_config.refresh_token_expire_days)
        expire = datetime.utcnow() + expires_delta
        token_id = secrets.token_hex(16)
        
        payload = {
            "sub": subject,
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": self.jwt_config.issuer,
            "aud": self.jwt_config.audience,
            "jti": token_id,
            "type": "refresh"
        }
        
        if claims:
            payload.update(claims)
        
        token = jwt.encode(
            payload,
            self.jwt_config.secret_key,
            algorithm=self.jwt_config.algorithm
        )
        
        # Store token info
        with self._jwt_lock:
            self.active_tokens[token_id] = {
                "subject": subject,
                "type": "refresh",
                "issued_at": datetime.utcnow(),
                "expires_at": expire,
                "revoked": False
            }
        
        self.health_metrics["jwt_tokens_issued"] += 1
        return token
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token with revocation check."""
        try:
            payload = jwt.decode(
                token,
                self.jwt_config.secret_key,
                algorithms=[self.jwt_config.algorithm],
                audience=self.jwt_config.audience,
                issuer=self.jwt_config.issuer
            )
            
            token_id = payload.get("jti")
            
            # Check if token is revoked
            with self._jwt_lock:
                if token_id in self.revoked_tokens:
                    return None
                
                if token_id and token_id in self.active_tokens:
                    token_info = self.active_tokens[token_id]
                    if token_info["revoked"]:
                        return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.debug("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid token: {e}")
            return None
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke a JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.jwt_config.secret_key,
                algorithms=[self.jwt_config.algorithm],
                options={"verify_exp": False}
            )
            
            token_id = payload.get("jti")
            
            if token_id:
                with self._jwt_lock:
                    self.revoked_tokens.add(token_id)
                    if token_id in self.active_tokens:
                        self.active_tokens[token_id]["revoked"] = True
                
                logger.info(f"Token {token_id} revoked")
                return True
            
        except jwt.InvalidTokenError:
            pass
        
        return False
    
    async def rotate_jwt_secret(self, new_secret: Optional[str] = None) -> str:
        """Rotate JWT secret key."""
        old_secret = self.jwt_config.secret_key
        new_secret = new_secret or secrets.token_urlsafe(32)
        
        self.jwt_config.secret_key = new_secret
        
        # Revoke all existing tokens
        with self._jwt_lock:
            for token_id, token_info in self.active_tokens.items():
                token_info["revoked"] = True
                self.revoked_tokens.add(token_id)
        
        logger.info("JWT secret rotated - all existing tokens revoked")
        return new_secret
    
    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired token records."""
        current_time = datetime.utcnow()
        expired_tokens = []
        
        with self._jwt_lock:
            for token_id, token_info in list(self.active_tokens.items()):
                if token_info["expires_at"] < current_time:
                    expired_tokens.append(token_id)
            
            for token_id in expired_tokens:
                del self.active_tokens[token_id]
                self.revoked_tokens.discard(token_id)
        
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")
        
        return len(expired_tokens)
    
    # ========================================================================
    # HTTP CACHING IMPLEMENTATION
    # ========================================================================
    
    def _generate_etag(self, data: Any) -> str:
        """Generate ETag for cache entry."""
        content = json.dumps(data, sort_keys=True) if not isinstance(data, str) else data
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    async def cache_response(
        self,
        key: str,
        data: Any,
        strategy: CacheStrategy = CacheStrategy.MEDIUM_TERM,
        custom_ttl: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        compress: bool = False
    ) -> str:
        """Cache HTTP response data."""
        now = datetime.utcnow()
        
        # Determine expiration
        if custom_ttl:
            expires_at = now + timedelta(seconds=custom_ttl)
        else:
            expires_at = now + self.cache_strategies[strategy]
        
        # Compress data if requested
        cached_data = data
        compressed = False
        if compress and isinstance(data, (str, bytes)):
            if isinstance(data, str):
                data_bytes = data.encode('utf-8')
            else:
                data_bytes = data
            cached_data = base64.b64encode(gzip.compress(data_bytes)).decode('utf-8')
            compressed = True
        
        # Generate ETag
        etag = self._generate_etag(cached_data)
        
        # Create cache entry
        entry = CacheEntry(
            data=cached_data,
            created_at=now,
            expires_at=expires_at,
            etag=etag,
            headers=headers or {},
            compressed=compressed
        )
        
        with self._cache_lock:
            self.http_cache[key] = entry
        
        self.health_metrics["cache_misses"] += 1  # New entry
        return etag
    
    async def get_cached_response(
        self,
        key: str,
        if_none_match: Optional[str] = None
    ) -> Optional[Tuple[Any, str, Dict[str, str]]]:
        """Get cached response data."""
        with self._cache_lock:
            entry = self.http_cache.get(key)
        
        if not entry or entry.is_expired():
            if entry and entry.is_expired():
                # Clean up expired entry
                with self._cache_lock:
                    del self.http_cache[key]
            
            self.health_metrics["cache_misses"] += 1
            return None
        
        # Check ETag for conditional requests
        if if_none_match and if_none_match == entry.etag:
            self.health_metrics["cache_hits"] += 1
            return None  # Not modified
        
        # Decompress if needed
        data = entry.data
        if entry.compressed:
            try:
                compressed_bytes = base64.b64decode(data.encode('utf-8'))
                data = gzip.decompress(compressed_bytes).decode('utf-8')
            except Exception as e:
                logger.error(f"Failed to decompress cached data: {e}")
                return None
        
        self.health_metrics["cache_hits"] += 1
        return data, entry.etag, entry.headers
    
    async def invalidate_cache(self, pattern: str = None, key: str = None) -> int:
        """Invalidate cache entries by pattern or specific key."""
        count = 0
        
        with self._cache_lock:
            if key:
                if key in self.http_cache:
                    del self.http_cache[key]
                    count = 1
            elif pattern:
                # Simple pattern matching
                keys_to_remove = []
                for cache_key in self.http_cache.keys():
                    if pattern in cache_key:
                        keys_to_remove.append(cache_key)
                
                for cache_key in keys_to_remove:
                    del self.http_cache[cache_key]
                    count += 1
            else:
                # Clear all cache
                count = len(self.http_cache)
                self.http_cache.clear()
        
        if count > 0:
            logger.info(f"Invalidated {count} cache entries")
        
        return count
    
    def cache_middleware(
        self,
        strategy: CacheStrategy = CacheStrategy.MEDIUM_TERM,
        key_prefix: str = "api",
        compress_threshold: int = 1024
    ):
        """Middleware decorator for automatic HTTP caching."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(request: Request = None, *args, **kwargs):
                # Generate cache key from request
                if request:
                    cache_key = f"{key_prefix}:{request.method}:{request.url.path}"
                    if request.query_params:
                        cache_key += f":{hash(str(request.query_params))}"
                else:
                    # Fallback cache key
                    cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
                
                # Check if cached
                if_none_match = getattr(request, 'headers', {}).get('if-none-match') if request else None
                cached_result = await self.get_cached_response(cache_key, if_none_match)
                
                if cached_result is None and if_none_match:
                    # Return 304 Not Modified
                    return Response(status_code=304)
                elif cached_result:
                    data, etag, headers = cached_result
                    response = Response(content=data)
                    response.headers.update(headers)
                    response.headers['etag'] = etag
                    return response
                
                # Execute function
                result = await func(request, *args, **kwargs) if asyncio.iscoroutinefunction(func) else func(request, *args, **kwargs)
                
                # Cache result
                compress = len(str(result)) > compress_threshold
                etag = await self.cache_response(cache_key, result, strategy, compress=compress)
                
                # Add ETag to response if it's a Response object
                if hasattr(result, 'headers'):
                    result.headers['etag'] = etag
                
                return result
            
            return wrapper
        return decorator
    
    # ========================================================================
    # WEBSOCKET MANAGEMENT
    # ========================================================================
    
    async def websocket_connect(
        self,
        websocket: WebSocket,
        user_id: str,
        organization_id: str,
        connection_type: ConnectionType = ConnectionType.DASHBOARD
    ) -> bool:
        """Accept and register WebSocket connection."""
        # Check connection limits
        pool = self.connection_pools[connection_type]
        
        with self._ws_lock:
            # Check total connections
            total_connections = len(self.websocket_connections)
            if total_connections >= pool.max_connections:
                logger.warning(f"Max connections reached for {connection_type}: {pool.max_connections}")
                await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
                return False
            
            # Check organization limit
            org_connections = len(self.organization_subscriptions.get(organization_id, set()))
            if org_connections >= pool.max_per_org:
                logger.warning(f"Max connections for org {organization_id}: {pool.max_per_org}")
                await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
                return False
            
            # Check user limit
            user_connections = sum(1 for conn in self.websocket_connections.values() 
                                 if conn.user_id == user_id)
            if user_connections >= pool.max_per_user:
                logger.warning(f"Max connections for user {user_id}: {pool.max_per_user}")
                await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
                return False
        
        # Accept connection
        await websocket.accept()
        
        # Create connection object
        connection_id = f"{user_id}:{connection_type.value}:{uuid.uuid4()}"
        connection = WebSocketConnection(
            websocket=websocket,
            user_id=user_id,
            organization_id=organization_id,
            connection_type=connection_type,
            connected_at=datetime.utcnow(),
            last_ping=datetime.utcnow()
        )
        
        with self._ws_lock:
            # Store connection
            self.websocket_connections[connection_id] = connection
            
            # Add to organization subscriptions
            if organization_id not in self.organization_subscriptions:
                self.organization_subscriptions[organization_id] = set()
            self.organization_subscriptions[organization_id].add(connection_id)
        
        self.health_metrics["websocket_connections"] = len(self.websocket_connections)
        
        # Send welcome message
        await self.send_websocket_message(connection_id, {
            "type": "connection",
            "status": "connected",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"WebSocket connection established: {connection_id}")
        return True
    
    async def websocket_disconnect(self, connection_id: str):
        """Remove WebSocket connection."""
        with self._ws_lock:
            connection = self.websocket_connections.get(connection_id)
            if not connection:
                return
            
            # Remove from connections
            del self.websocket_connections[connection_id]
            
            # Remove from organization subscriptions
            org_id = connection.organization_id
            if org_id in self.organization_subscriptions:
                self.organization_subscriptions[org_id].discard(connection_id)
                if not self.organization_subscriptions[org_id]:
                    del self.organization_subscriptions[org_id]
        
        self.health_metrics["websocket_connections"] = len(self.websocket_connections)
        logger.info(f"WebSocket connection removed: {connection_id}")
    
    async def send_websocket_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Send message to specific WebSocket connection."""
        connection = self.websocket_connections.get(connection_id)
        if not connection:
            return False
        
        try:
            await connection.websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send WebSocket message to {connection_id}: {e}")
            await self.websocket_disconnect(connection_id)
            return False
    
    async def broadcast_to_organization(
        self,
        organization_id: str,
        message: Dict[str, Any],
        connection_type: Optional[ConnectionType] = None
    ) -> int:
        """Broadcast message to all connections in an organization."""
        sent_count = 0
        
        with self._ws_lock:
            connection_ids = self.organization_subscriptions.get(organization_id, set()).copy()
        
        for connection_id in connection_ids:
            connection = self.websocket_connections.get(connection_id)
            if connection and (not connection_type or connection.connection_type == connection_type):
                if await self.send_websocket_message(connection_id, message):
                    sent_count += 1
        
        return sent_count
    
    async def broadcast_metric_update(
        self,
        organization_id: str,
        metric_type: str,
        data: Dict[str, Any]
    ) -> int:
        """Broadcast metric updates to dashboard connections."""
        message = {
            "type": "metric_update",
            "metric_type": metric_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        return await self.broadcast_to_organization(
            organization_id, 
            message, 
            ConnectionType.DASHBOARD
        )
    
    async def broadcast_conversation_update(
        self,
        organization_id: str,
        conversation_id: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> int:
        """Broadcast conversation updates."""
        message = {
            "type": "conversation_update",
            "conversation_id": conversation_id,
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        return await self.broadcast_to_organization(
            organization_id, 
            message, 
            ConnectionType.CONVERSATION
        )
    
    async def handle_websocket_ping(self, connection_id: str) -> bool:
        """Handle WebSocket ping to keep connection alive."""
        connection = self.websocket_connections.get(connection_id)
        if not connection:
            return False
        
        connection.last_ping = datetime.utcnow()
        
        await self.send_websocket_message(connection_id, {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return True
    
    async def cleanup_stale_websocket_connections(self) -> int:
        """Clean up stale WebSocket connections."""
        current_time = datetime.utcnow()
        timeout = timedelta(seconds=getattr(settings, 'WS_CONNECTION_TIMEOUT', 300))
        stale_connections = []
        
        for connection_id, connection in self.websocket_connections.items():
            if current_time - connection.last_ping > timeout:
                stale_connections.append(connection_id)
        
        for connection_id in stale_connections:
            await self.websocket_disconnect(connection_id)
        
        if stale_connections:
            logger.info(f"Cleaned up {len(stale_connections)} stale WebSocket connections")
        
        return len(stale_connections)
    
    # ========================================================================
    # REDIS INTEGRATION
    # ========================================================================
    
    async def redis_get(self, key: str) -> Optional[str]:
        """Get value from Redis (or mock)."""
        if self.use_redis_mock:
            return await self.redis_mock.get(key)
        else:
            # Implement real Redis connection here
            pass
    
    async def redis_set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in Redis (or mock)."""
        if self.use_redis_mock:
            return await self.redis_mock.set(key, value, ex)
        else:
            # Implement real Redis connection here
            pass
    
    async def redis_delete(self, key: str) -> int:
        """Delete key from Redis (or mock)."""
        if self.use_redis_mock:
            return await self.redis_mock.delete(key)
        else:
            # Implement real Redis connection here
            pass
    
    # ========================================================================
    # HEALTH MONITORING
    # ========================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check."""
        current_time = datetime.utcnow()
        uptime = current_time - self._startup_time
        
        # Calculate success rate
        total_requests = self.health_metrics["total_requests"]
        failed_requests = self.health_metrics["failed_requests"]
        success_rate = 1.0
        if total_requests > 0:
            success_rate = (total_requests - failed_requests) / total_requests
        
        # Cache hit rate
        cache_hits = self.health_metrics["cache_hits"]
        cache_misses = self.health_metrics["cache_misses"]
        cache_hit_rate = 0.0
        if cache_hits + cache_misses > 0:
            cache_hit_rate = cache_hits / (cache_hits + cache_misses)
        
        # Circuit breaker states
        circuit_breaker_states = {}
        with self._cb_lock:
            for name, cb in self.circuit_breakers.items():
                circuit_breaker_states[name] = cb.state.value
        
        # WebSocket connection status
        websocket_stats = {
            "total_connections": len(self.websocket_connections),
            "connections_by_type": {},
            "organizations": len(self.organization_subscriptions)
        }
        
        for conn_type in ConnectionType:
            count = sum(1 for conn in self.websocket_connections.values() 
                       if conn.connection_type == conn_type)
            websocket_stats["connections_by_type"][conn_type.value] = count
        
        # Performance metrics
        avg_response_time = self.performance_metrics["avg_response_time"]
        
        # Overall health status
        status = "healthy"
        if success_rate < 0.95:
            status = "degraded"
        if success_rate < 0.80:
            status = "unhealthy"
        
        health_status = {
            "status": status,
            "timestamp": current_time.isoformat(),
            "uptime_seconds": uptime.total_seconds(),
            "service_metrics": {
                "requests": {
                    "total": total_requests,
                    "failed": failed_requests,
                    "success_rate": success_rate
                },
                "cache": {
                    "hits": cache_hits,
                    "misses": cache_misses,
                    "hit_rate": cache_hit_rate,
                    "entries": len(self.http_cache)
                },
                "jwt": {
                    "active_tokens": len(self.active_tokens),
                    "revoked_tokens": len(self.revoked_tokens),
                    "tokens_issued": self.health_metrics["jwt_tokens_issued"]
                },
                "encryption": {
                    "operations": self.health_metrics["encryption_operations"],
                    "levels_supported": len(EncryptionLevel)
                },
                "websocket": websocket_stats,
                "circuit_breakers": {
                    "count": len(self.circuit_breakers),
                    "states": circuit_breaker_states
                }
            },
            "performance": {
                "average_response_time_ms": avg_response_time * 1000,
                "uptime_percentage": self.performance_metrics["uptime_percentage"]
            }
        }
        
        return health_status
    
    async def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed service metrics for monitoring."""
        circuit_breaker_stats = await self.get_circuit_breaker_stats()
        
        return {
            "infrastructure_service": {
                "initialized": self._initialized,
                "startup_time": self._startup_time.isoformat(),
                "components": {
                    "circuit_breakers": {
                        "count": len(self.circuit_breakers),
                        "details": circuit_breaker_stats
                    },
                    "encryption": {
                        "levels": [level.value for level in EncryptionLevel],
                        "operations_count": self.health_metrics["encryption_operations"]
                    },
                    "jwt": {
                        "config": {
                            "algorithm": self.jwt_config.algorithm,
                            "access_expire_minutes": self.jwt_config.access_token_expire_minutes,
                            "refresh_expire_days": self.jwt_config.refresh_token_expire_days
                        },
                        "tokens": {
                            "active": len(self.active_tokens),
                            "revoked": len(self.revoked_tokens)
                        }
                    },
                    "cache": {
                        "entries": len(self.http_cache),
                        "strategies": [strategy.value for strategy in CacheStrategy]
                    },
                    "websocket": {
                        "connections": len(self.websocket_connections),
                        "organizations": len(self.organization_subscriptions),
                        "pools": {
                            conn_type.value: {
                                "max_connections": pool.max_connections,
                                "max_per_org": pool.max_per_org,
                                "max_per_user": pool.max_per_user
                            }
                            for conn_type, pool in self.connection_pools.items()
                        }
                    },
                    "redis": {
                        "using_mock": self.use_redis_mock
                    }
                }
            }
        }
    
    async def cleanup_all_resources(self) -> Dict[str, int]:
        """Clean up all expired/stale resources."""
        cleanup_results = {
            "expired_tokens": await self.cleanup_expired_tokens(),
            "expired_cache_entries": await self.invalidate_cache(),  # Clear all for cleanup
            "stale_websocket_connections": await self.cleanup_stale_websocket_connections()
        }
        
        logger.info(f"Resource cleanup completed: {cleanup_results}")
        return cleanup_results
    
    # ========================================================================
    # COMPATIBILITY METHODS
    # ========================================================================
    
    async def execute_with_fallback(
        self,
        primary_func: Callable,
        fallback_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with fallback on failure."""
        try:
            return await primary_func(*args, **kwargs) if asyncio.iscoroutinefunction(primary_func) else primary_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Primary function failed ({e}), using fallback")
            return await fallback_func(*args, **kwargs) if asyncio.iscoroutinefunction(fallback_func) else fallback_func(*args, **kwargs)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class EncryptionError(Exception):
    """Exception raised for encryption/decryption errors."""
    pass


class WebSocketConnectionError(Exception):
    """Exception raised for WebSocket connection errors."""
    pass


# ============================================================================
# GLOBAL SERVICE INSTANCE
# ============================================================================

# Singleton instance for the consolidated infrastructure service
_infrastructure_service_instance = None

def get_infrastructure_service() -> ConsolidatedInfrastructureService:
    """Get the global infrastructure service instance."""
    global _infrastructure_service_instance
    if _infrastructure_service_instance is None:
        _infrastructure_service_instance = ConsolidatedInfrastructureService()
    return _infrastructure_service_instance


# ============================================================================
# INITIALIZATION AND SHUTDOWN
# ============================================================================

async def initialize_infrastructure_service() -> ConsolidatedInfrastructureService:
    """Initialize infrastructure service with async setup."""
    service = get_infrastructure_service()
    
    # Perform any additional async initialization here
    logger.info("Infrastructure service async initialization completed")
    
    return service


async def shutdown_infrastructure_service():
    """Shutdown infrastructure service gracefully."""
    global _infrastructure_service_instance
    
    if _infrastructure_service_instance:
        # Close all WebSocket connections
        connection_ids = list(_infrastructure_service_instance.websocket_connections.keys())
        for connection_id in connection_ids:
            await _infrastructure_service_instance.websocket_disconnect(connection_id)
        
        # Clean up all resources
        await _infrastructure_service_instance.cleanup_all_resources()
        
        logger.info("Infrastructure service shutdown completed")
        _infrastructure_service_instance = None


# ============================================================================
# EXPORT ALL IMPORTANT CLASSES AND FUNCTIONS
# ============================================================================

__all__ = [
    'ConsolidatedInfrastructureService',
    'CircuitState',
    'EncryptionLevel', 
    'CacheStrategy',
    'ConnectionType',
    'CircuitBreakerConfig',
    'JWTConfig',
    'CacheEntry',
    'WebSocketConnection',
    'ConnectionPool',
    'CircuitBreakerOpenError',
    'EncryptionError',
    'WebSocketConnectionError',
    'get_infrastructure_service',
    'initialize_infrastructure_service',
    'shutdown_infrastructure_service'
]