"""
Infrastructure Service - Consolidated system infrastructure functionality.

This service consolidates functionality from:
- circuit_breaker_service.py
- encryption_service.py
- jwt_rotation_service.py
- compatibility_wrappers.py

Provides:
- Circuit breaker patterns for resilience
- Encryption and decryption services
- JWT token management and rotation
- System compatibility wrappers
- Health checking and monitoring
- Error handling and recovery
- Security utilities
"""

import logging
import asyncio
import hashlib
import hmac
import secrets
import time
import base64
from typing import Dict, List, Any, Optional, Callable, Union, TypeVar
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import json
from contextlib import asynccontextmanager
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import jwt

from src.config import settings
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)

T = TypeVar('T')


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class EncryptionLevel(str, Enum):
    """Encryption security levels."""
    STANDARD = "standard"  # AES-256
    HIGH = "high"         # AES-256 + additional layers
    PII = "pii"           # Specialized for PII data


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: type = Exception
    fallback_function: Optional[Callable] = None


@dataclass
class CircuitBreakerState:
    """Current state of a circuit breaker."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    total_requests: int = 0
    successful_requests: int = 0


@dataclass
class JWTConfig:
    """JWT configuration."""
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    issuer: str = "ngx-voice-agent"
    audience: str = "ngx-api"


class InfrastructureService:
    """
    Unified infrastructure service for system reliability and security.
    
    Features:
    - Circuit breaker patterns for fault tolerance
    - Advanced encryption/decryption capabilities
    - JWT token management with rotation
    - Health monitoring and diagnostics
    - Error handling and recovery mechanisms
    - Security utilities and compliance helpers
    """
    
    def __init__(self):
        """Initialize infrastructure service."""
        # Circuit breaker registry
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.circuit_configs: Dict[str, CircuitBreakerConfig] = {}
        
        # Encryption setup
        self.encryption_keys: Dict[EncryptionLevel, bytes] = {}
        self._initialize_encryption()
        
        # JWT configuration
        self.jwt_config = self._initialize_jwt_config()
        self.active_tokens: Dict[str, Dict[str, Any]] = {}  # token_id -> token_info
        
        # Health monitoring
        self.health_metrics: Dict[str, Any] = {
            "start_time": datetime.now(),
            "total_requests": 0,
            "failed_requests": 0,
            "circuit_breaker_trips": 0
        }
        
        # Compatibility wrappers registry
        self.compatibility_wrappers: Dict[str, Callable] = {}
        
        logger.info("InfrastructureService initialized")
    
    def _initialize_encryption(self) -> None:
        """Initialize encryption keys for different security levels."""
        # Generate or load encryption keys
        master_key = getattr(settings, 'ENCRYPTION_KEY', None)
        
        if not master_key:
            # Generate a new master key (in production, this should be from secure storage)
            master_key = base64.urlsafe_b64encode(secrets.token_bytes(32))
            logger.warning("Generated new encryption key - store securely for production")
        
        if isinstance(master_key, str):
            master_key = master_key.encode()
        
        # Derive keys for different encryption levels
        self.encryption_keys[EncryptionLevel.STANDARD] = self._derive_key(master_key, b"standard")
        self.encryption_keys[EncryptionLevel.HIGH] = self._derive_key(master_key, b"high_security")
        self.encryption_keys[EncryptionLevel.PII] = self._derive_key(master_key, b"pii_protection")
    
    def _derive_key(self, master_key: bytes, salt: bytes) -> bytes:
        """Derive encryption key using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(master_key)
    
    def _initialize_jwt_config(self) -> JWTConfig:
        """Initialize JWT configuration."""
        secret_key = getattr(settings, 'JWT_SECRET_KEY', None)
        
        if not secret_key:
            secret_key = secrets.token_urlsafe(32)
            logger.warning("Generated new JWT secret - configure JWT_SECRET_KEY for production")
        
        return JWTConfig(
            secret_key=secret_key,
            algorithm=getattr(settings, 'JWT_ALGORITHM', 'HS256'),
            access_token_expire_minutes=getattr(settings, 'JWT_ACCESS_TOKEN_EXPIRE_MINUTES', 30),
            refresh_token_expire_days=getattr(settings, 'JWT_REFRESH_TOKEN_EXPIRE_DAYS', 7)
        )
    
    # Circuit Breaker Implementation
    
    def circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        fallback: Optional[Callable] = None
    ):
        """
        Circuit breaker decorator for protecting against cascading failures.
        
        Args:
            name: Unique name for the circuit breaker
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            fallback: Fallback function to call when circuit is open
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            # Register circuit breaker
            if name not in self.circuit_breakers:
                self.circuit_breakers[name] = CircuitBreakerState()
                self.circuit_configs[name] = CircuitBreakerConfig(
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    fallback_function=fallback
                )
            
            @wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                return await self._execute_with_circuit_breaker(name, func, *args, **kwargs)
            
            return wrapper
        
        return decorator
    
    async def _execute_with_circuit_breaker(
        self,
        name: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with circuit breaker protection."""
        breaker_state = self.circuit_breakers[name]
        config = self.circuit_configs[name]
        
        # Check circuit state
        current_state = await self._get_circuit_state(name)
        
        if current_state == CircuitState.OPEN:
            # Circuit is open - use fallback or raise exception
            if config.fallback_function:
                logger.warning(f"Circuit breaker {name} is OPEN, using fallback")
                return await config.fallback_function(*args, **kwargs)
            else:
                logger.error(f"Circuit breaker {name} is OPEN, no fallback available")
                raise Exception(f"Service {name} is currently unavailable")
        
        # Circuit is closed or half-open - attempt execution
        breaker_state.total_requests += 1
        self.health_metrics["total_requests"] += 1
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset failure count
            breaker_state.failure_count = 0
            breaker_state.last_success_time = datetime.now()
            breaker_state.successful_requests += 1
            
            # Transition from half-open to closed
            if current_state == CircuitState.HALF_OPEN:
                breaker_state.state = CircuitState.CLOSED
                logger.info(f"Circuit breaker {name} transitioned to CLOSED")
            
            return result
            
        except Exception as e:
            # Failure - increment failure count
            breaker_state.failure_count += 1
            breaker_state.last_failure_time = datetime.now()
            self.health_metrics["failed_requests"] += 1
            
            # Check if we should open the circuit
            if breaker_state.failure_count >= config.failure_threshold:
                breaker_state.state = CircuitState.OPEN
                self.health_metrics["circuit_breaker_trips"] += 1
                logger.error(f"Circuit breaker {name} OPENED after {breaker_state.failure_count} failures")
            
            raise e
    
    async def _get_circuit_state(self, name: str) -> CircuitState:
        """Get current state of circuit breaker."""
        breaker_state = self.circuit_breakers[name]
        config = self.circuit_configs[name]
        
        if breaker_state.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if (breaker_state.last_failure_time and 
                datetime.now() - breaker_state.last_failure_time > timedelta(seconds=config.recovery_timeout)):
                breaker_state.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker {name} transitioned to HALF_OPEN for testing")
        
        return breaker_state.state
    
    async def reset_circuit_breaker(self, name: str) -> bool:
        """Manually reset a circuit breaker."""
        if name in self.circuit_breakers:
            breaker_state = self.circuit_breakers[name]
            breaker_state.state = CircuitState.CLOSED
            breaker_state.failure_count = 0
            breaker_state.last_failure_time = None
            logger.info(f"Circuit breaker {name} manually reset")
            return True
        return False
    
    async def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """Get statistics for all circuit breakers."""
        stats = {}
        
        for name, breaker_state in self.circuit_breakers.items():
            success_rate = 0.0
            if breaker_state.total_requests > 0:
                success_rate = breaker_state.successful_requests / breaker_state.total_requests
            
            stats[name] = {
                "state": breaker_state.state.value,
                "total_requests": breaker_state.total_requests,
                "successful_requests": breaker_state.successful_requests,
                "failure_count": breaker_state.failure_count,
                "success_rate": success_rate,
                "last_failure_time": breaker_state.last_failure_time.isoformat() if breaker_state.last_failure_time else None,
                "last_success_time": breaker_state.last_success_time.isoformat() if breaker_state.last_success_time else None
            }
        
        return stats
    
    # Encryption Services
    
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
        
        # Get encryption key
        encryption_key = self.encryption_keys[level]
        fernet = Fernet(base64.urlsafe_b64encode(encryption_key))
        
        # Encrypt data
        encrypted_bytes = fernet.encrypt(data_bytes)
        
        # Return base64 encoded result
        return base64.b64encode(encrypted_bytes).decode('utf-8')
    
    async def decrypt_data(
        self,
        encrypted_data: str,
        level: EncryptionLevel = EncryptionLevel.STANDARD,
        return_json: bool = False
    ) -> Union[str, bytes, dict]:
        """
        Decrypt data with specified security level.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            level: Encryption security level used for encryption
            return_json: Whether to return as JSON dict
            
        Returns:
            Decrypted data
        """
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Get decryption key
            decryption_key = self.encryption_keys[level]
            fernet = Fernet(base64.urlsafe_b64encode(decryption_key))
            
            # Decrypt data
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            
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
        """
        Encrypt PII data with highest security level.
        
        Args:
            pii_data: Dictionary containing PII fields
            
        Returns:
            Dictionary with encrypted PII values
        """
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
        """
        Decrypt PII data.
        
        Args:
            encrypted_pii: Dictionary with encrypted PII values
            
        Returns:
            Dictionary with decrypted PII values
        """
        decrypted_pii = {}
        
        for field, encrypted_value in encrypted_pii.items():
            if encrypted_value is not None:
                try:
                    decrypted_value = await self.decrypt_data(
                        encrypted_value,
                        level=EncryptionLevel.PII
                    )
                    decrypted_pii[field] = decrypted_value
                except Exception as e:
                    logger.error(f"Failed to decrypt PII field {field}: {e}")
                    decrypted_pii[field] = None
            else:
                decrypted_pii[field] = None
        
        return decrypted_pii
    
    # JWT Token Management
    
    async def create_access_token(
        self,
        subject: str,
        claims: Optional[Dict[str, Any]] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token.
        
        Args:
            subject: Token subject (usually user ID)
            claims: Additional claims to include
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT token
        """
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
        self.active_tokens[token_id] = {
            "subject": subject,
            "type": "access",
            "issued_at": datetime.utcnow(),
            "expires_at": expire,
            "revoked": False
        }
        
        return token
    
    async def create_refresh_token(
        self,
        subject: str,
        claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create JWT refresh token.
        
        Args:
            subject: Token subject
            claims: Additional claims
            
        Returns:
            Encoded JWT refresh token
        """
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
        self.active_tokens[token_id] = {
            "subject": subject,
            "type": "refresh",
            "issued_at": datetime.utcnow(),
            "expires_at": expire,
            "revoked": False
        }
        
        return token
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_config.secret_key,
                algorithms=[self.jwt_config.algorithm],
                audience=self.jwt_config.audience,
                issuer=self.jwt_config.issuer
            )
            
            token_id = payload.get("jti")
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
        """
        Revoke a JWT token.
        
        Args:
            token: Token to revoke
            
        Returns:
            Success status
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_config.secret_key,
                algorithms=[self.jwt_config.algorithm],
                options={"verify_exp": False}  # Don't verify expiration for revocation
            )
            
            token_id = payload.get("jti")
            if token_id and token_id in self.active_tokens:
                self.active_tokens[token_id]["revoked"] = True
                logger.info(f"Token {token_id} revoked")
                return True
            
        except jwt.InvalidTokenError:
            pass
        
        return False
    
    async def rotate_jwt_secret(self, new_secret: Optional[str] = None) -> str:
        """
        Rotate JWT secret key.
        
        Args:
            new_secret: New secret key, or None to generate one
            
        Returns:
            New secret key
        """
        old_secret = self.jwt_config.secret_key
        new_secret = new_secret or secrets.token_urlsafe(32)
        
        self.jwt_config.secret_key = new_secret
        
        # Revoke all existing tokens
        for token_id, token_info in self.active_tokens.items():
            token_info["revoked"] = True
        
        logger.info("JWT secret rotated - all existing tokens revoked")
        return new_secret
    
    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired token records.
        
        Returns:
            Number of tokens cleaned up
        """
        current_time = datetime.utcnow()
        expired_tokens = []
        
        for token_id, token_info in self.active_tokens.items():
            if token_info["expires_at"] < current_time:
                expired_tokens.append(token_id)
        
        for token_id in expired_tokens:
            del self.active_tokens[token_id]
        
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")
        
        return len(expired_tokens)
    
    # Compatibility Wrappers
    
    def register_compatibility_wrapper(
        self,
        name: str,
        wrapper_func: Callable
    ) -> None:
        """
        Register a compatibility wrapper function.
        
        Args:
            name: Wrapper name
            wrapper_func: Wrapper function
        """
        self.compatibility_wrappers[name] = wrapper_func
        logger.debug(f"Registered compatibility wrapper: {name}")
    
    async def execute_with_wrapper(
        self,
        wrapper_name: str,
        target_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with compatibility wrapper.
        
        Args:
            wrapper_name: Name of wrapper to use
            target_func: Function to wrap
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        if wrapper_name not in self.compatibility_wrappers:
            logger.warning(f"Compatibility wrapper {wrapper_name} not found, executing directly")
            return await target_func(*args, **kwargs)
        
        wrapper = self.compatibility_wrappers[wrapper_name]
        return await wrapper(target_func, *args, **kwargs)
    
    # Health Monitoring
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Returns:
            Health status information
        """
        current_time = datetime.now()
        uptime = current_time - self.health_metrics["start_time"]
        
        # Calculate success rate
        total_requests = self.health_metrics["total_requests"]
        failed_requests = self.health_metrics["failed_requests"]
        success_rate = 1.0
        if total_requests > 0:
            success_rate = (total_requests - failed_requests) / total_requests
        
        # Check circuit breaker status
        circuit_status = {}
        for name, state in self.circuit_breakers.items():
            circuit_status[name] = state.state.value
        
        health_status = {
            "status": "healthy" if success_rate > 0.95 else "degraded",
            "uptime_seconds": uptime.total_seconds(),
            "total_requests": total_requests,
            "failed_requests": failed_requests,
            "success_rate": success_rate,
            "circuit_breaker_trips": self.health_metrics["circuit_breaker_trips"],
            "circuit_breakers": circuit_status,
            "active_tokens": len(self.active_tokens),
            "encryption_levels": list(EncryptionLevel),
            "timestamp": current_time.isoformat()
        }
        
        return health_status
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        return {
            "circuit_breakers_count": len(self.circuit_breakers),
            "encryption_levels_supported": len(EncryptionLevel),
            "active_jwt_tokens": len(self.active_tokens),
            "compatibility_wrappers": len(self.compatibility_wrappers),
            "health_metrics": self.health_metrics,
            "jwt_config": {
                "algorithm": self.jwt_config.algorithm,
                "access_token_expire_minutes": self.jwt_config.access_token_expire_minutes,
                "refresh_token_expire_days": self.jwt_config.refresh_token_expire_days
            }
        }