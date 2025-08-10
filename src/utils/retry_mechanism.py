"""
Enhanced Retry Mechanism with Exponential Backoff
Reduces error rates by automatically retrying transient failures
"""

import asyncio
import random
from typing import TypeVar, Callable, Optional, Dict, Any, List, Type
from functools import wraps
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryableError(Enum):
    """Errors that should trigger a retry."""
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    SERVICE_UNAVAILABLE = "service_unavailable"
    DATABASE_CONNECTION = "database_connection"
    TEMPORARY_FAILURE = "temporary_failure"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.1  # ±10% of delay
    retryable_errors: List[Type[Exception]] = None
    retryable_status_codes: List[int] = None
    
    def __post_init__(self):
        if self.retryable_errors is None:
            self.retryable_errors = [
                asyncio.TimeoutError,
                ConnectionError,
                OSError
            ]
        if self.retryable_status_codes is None:
            self.retryable_status_codes = [429, 500, 502, 503, 504]


@dataclass
class RetryStats:
    """Statistics about retry attempts."""
    total_attempts: int = 0
    successful_retries: int = 0
    failed_retries: int = 0
    total_delay_seconds: float = 0
    errors_by_type: Dict[str, int] = None
    
    def __post_init__(self):
        if self.errors_by_type is None:
            self.errors_by_type = {}


class RetryManager:
    """Manages retry logic with circuit breaker pattern."""
    
    def __init__(self):
        self.stats = RetryStats()
        self.circuit_breaker_state: Dict[str, Dict[str, Any]] = {}
        
    def calculate_delay(
        self, 
        attempt: int, 
        config: RetryConfig,
        error_type: Optional[RetryableError] = None
    ) -> float:
        """Calculate delay with exponential backoff and jitter."""
        # Special handling for rate limits
        if error_type == RetryableError.RATE_LIMIT:
            base_delay = config.initial_delay * 5  # Longer delay for rate limits
        else:
            base_delay = config.initial_delay
            
        # Exponential backoff
        delay = min(
            base_delay * (config.exponential_base ** (attempt - 1)),
            config.max_delay
        )
        
        # Add jitter to prevent thundering herd
        if config.jitter:
            jitter_amount = delay * config.jitter_range
            delay += random.uniform(-jitter_amount, jitter_amount)
            
        return max(0, delay)
    
    def should_retry(
        self, 
        error: Exception,
        attempt: int,
        config: RetryConfig,
        function_name: str
    ) -> tuple[bool, Optional[RetryableError]]:
        """Determine if an error should trigger a retry."""
        if attempt >= config.max_attempts:
            return False, None
            
        # Check circuit breaker
        if self.is_circuit_open(function_name):
            logger.warning(f"Circuit breaker open for {function_name}")
            return False, None
            
        # Check error type
        error_type = self.classify_error(error, config)
        if error_type:
            return True, error_type
            
        return False, None
    
    def classify_error(
        self, 
        error: Exception,
        config: RetryConfig
    ) -> Optional[RetryableError]:
        """Classify error type for retry decision."""
        error_str = str(error).lower()
        
        # Check for specific error types
        if isinstance(error, asyncio.TimeoutError):
            return RetryableError.TIMEOUT
        elif isinstance(error, ConnectionError):
            return RetryableError.NETWORK_ERROR
        elif isinstance(error, OSError) and error.errno in [104, 111]:
            return RetryableError.NETWORK_ERROR
            
        # Check error message patterns
        if "rate limit" in error_str:
            return RetryableError.RATE_LIMIT
        elif "timeout" in error_str:
            return RetryableError.TIMEOUT
        elif any(code in error_str for code in ["503", "unavailable"]):
            return RetryableError.SERVICE_UNAVAILABLE
        elif "database" in error_str or "connection" in error_str:
            return RetryableError.DATABASE_CONNECTION
            
        # Check if error type is in retryable list
        for retryable_type in config.retryable_errors:
            if isinstance(error, retryable_type):
                return RetryableError.TEMPORARY_FAILURE
                
        return None
    
    def is_circuit_open(self, function_name: str) -> bool:
        """Check if circuit breaker is open for a function."""
        if function_name not in self.circuit_breaker_state:
            return False
            
        state = self.circuit_breaker_state[function_name]
        if state["state"] == "open":
            # Check if cool-down period has passed
            if datetime.now() > state["open_until"]:
                state["state"] = "half-open"
                state["test_requests"] = 0
                return False
            return True
            
        return False
    
    def record_success(self, function_name: str):
        """Record successful execution."""
        if function_name in self.circuit_breaker_state:
            state = self.circuit_breaker_state[function_name]
            if state["state"] == "half-open":
                state["test_requests"] += 1
                if state["test_requests"] >= 3:
                    # Close circuit after successful test requests
                    state["state"] = "closed"
                    state["failure_count"] = 0
    
    def record_failure(self, function_name: str, error: Exception):
        """Record failed execution."""
        if function_name not in self.circuit_breaker_state:
            self.circuit_breaker_state[function_name] = {
                "state": "closed",
                "failure_count": 0,
                "last_failure": None
            }
            
        state = self.circuit_breaker_state[function_name]
        state["failure_count"] += 1
        state["last_failure"] = datetime.now()
        
        # Open circuit if too many failures
        if state["failure_count"] >= 5:
            state["state"] = "open"
            state["open_until"] = datetime.now() + timedelta(minutes=1)
            logger.warning(f"Circuit breaker opened for {function_name}")


# Global retry manager instance
retry_manager = RetryManager()


def with_retry(config: Optional[RetryConfig] = None):
    """Decorator for adding retry logic to async functions."""
    if config is None:
        config = RetryConfig()
        
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            function_name = f"{func.__module__}.{func.__name__}"
            last_error = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    # Execute function
                    result = await func(*args, **kwargs)
                    
                    # Record success
                    retry_manager.record_success(function_name)
                    if attempt > 1:
                        retry_manager.stats.successful_retries += 1
                        logger.info(f"Retry successful for {function_name} on attempt {attempt}")
                        
                    return result
                    
                except Exception as error:
                    last_error = error
                    retry_manager.stats.total_attempts += 1
                    
                    # Check if we should retry
                    should_retry, error_type = retry_manager.should_retry(
                        error, attempt, config, function_name
                    )
                    
                    if not should_retry:
                        retry_manager.record_failure(function_name, error)
                        retry_manager.stats.failed_retries += 1
                        raise
                        
                    # Calculate delay
                    delay = retry_manager.calculate_delay(attempt, config, error_type)
                    retry_manager.stats.total_delay_seconds += delay
                    
                    # Update error statistics
                    error_type_str = error_type.value if error_type else "unknown"
                    retry_manager.stats.errors_by_type[error_type_str] = \
                        retry_manager.stats.errors_by_type.get(error_type_str, 0) + 1
                    
                    logger.warning(
                        f"Retry {attempt}/{config.max_attempts} for {function_name} "
                        f"after {error_type_str}: {error}. Waiting {delay:.2f}s"
                    )
                    
                    # Wait before retry
                    await asyncio.sleep(delay)
                    
            # All retries exhausted
            retry_manager.record_failure(function_name, last_error)
            retry_manager.stats.failed_retries += 1
            raise last_error
            
        return wrapper
    return decorator


def with_retry_sync(config: Optional[RetryConfig] = None):
    """Decorator for adding retry logic to sync functions."""
    if config is None:
        config = RetryConfig()
        
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            function_name = f"{func.__module__}.{func.__name__}"
            last_error = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    if attempt > 1:
                        logger.info(f"Retry successful for {function_name} on attempt {attempt}")
                        
                    return result
                    
                except Exception as error:
                    last_error = error
                    
                    # Check if we should retry
                    should_retry = attempt < config.max_attempts and \
                                 any(isinstance(error, t) for t in config.retryable_errors)
                    
                    if not should_retry:
                        raise
                        
                    # Calculate delay
                    delay = retry_manager.calculate_delay(attempt, config)
                    
                    logger.warning(
                        f"Retry {attempt}/{config.max_attempts} for {function_name}: {error}. "
                        f"Waiting {delay:.2f}s"
                    )
                    
                    # Wait before retry
                    import time
                    time.sleep(delay)
                    
            raise last_error
            
        return wrapper
    return decorator


# Convenience functions for common retry patterns
async def retry_with_backoff(
    func: Callable[..., T],
    *args,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    **kwargs
) -> T:
    """Execute a function with retry and exponential backoff."""
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=initial_delay
    )
    
    @with_retry(config)
    async def wrapped():
        return await func(*args, **kwargs)
        
    return await wrapped()


def get_retry_stats() -> Dict[str, Any]:
    """Get current retry statistics."""
    return {
        "total_attempts": retry_manager.stats.total_attempts,
        "successful_retries": retry_manager.stats.successful_retries,
        "failed_retries": retry_manager.stats.failed_retries,
        "total_delay_seconds": retry_manager.stats.total_delay_seconds,
        "errors_by_type": dict(retry_manager.stats.errors_by_type),
        "circuit_breakers": {
            name: {
                "state": state["state"],
                "failure_count": state["failure_count"]
            }
            for name, state in retry_manager.circuit_breaker_state.items()
        }
    }


def reset_retry_stats():
    """Reset retry statistics."""
    retry_manager.stats = RetryStats()
    retry_manager.circuit_breaker_state.clear()