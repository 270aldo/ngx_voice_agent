"""
Complete Circuit Breaker implementation for NGX Voice Sales Agent.
Provides fault tolerance and prevents cascading failures.
"""

import asyncio
import functools
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional, Union
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"         # Circuit is broken, requests fail immediately
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5          # Failures before opening circuit
    recovery_timeout: int = 60          # Seconds before trying recovery
    expected_exception: type = Exception  # Exception types to catch
    success_threshold: int = 2          # Successes needed to close circuit
    half_open_max_calls: int = 3       # Max calls allowed in half-open state
    exclude_exceptions: tuple = ()      # Exceptions that don't count as failures
    
    def __post_init__(self):
        """Validate configuration."""
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if self.recovery_timeout < 1:
            raise ValueError("recovery_timeout must be at least 1")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be at least 1")


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker monitoring."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: list = field(default_factory=list)
    call_durations: list = field(default_factory=list)
    
    def add_call_duration(self, duration: float, max_history: int = 100):
        """Track call duration for performance monitoring."""
        self.call_durations.append(duration)
        if len(self.call_durations) > max_history:
            self.call_durations.pop(0)
    
    def get_average_duration(self) -> float:
        """Get average call duration."""
        if not self.call_durations:
            return 0.0
        return sum(self.call_durations) / len(self.call_durations)
    
    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls


class CircuitBreaker:
    """
    Circuit Breaker implementation with three states:
    - CLOSED: Normal operation
    - OPEN: Failing fast to prevent cascading failures
    - HALF_OPEN: Testing if the service has recovered
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0
        self._lock = Lock()
        self.metrics = CircuitBreakerMetrics()
        
        logger.info(f"Circuit breaker '{name}' initialized with config: {self.config}")
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for automatic transitions."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
            return self._state
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        return (
            self._last_failure_time and
            datetime.now() >= self._last_failure_time + timedelta(seconds=self.config.recovery_timeout)
        )
    
    def _transition_to_half_open(self):
        """Transition from OPEN to HALF_OPEN state."""
        logger.info(f"Circuit breaker '{self.name}' transitioning from OPEN to HALF_OPEN")
        self._state = CircuitState.HALF_OPEN
        self._half_open_calls = 0
        self._success_count = 0
        self.metrics.state_changes.append({
            "from": CircuitState.OPEN,
            "to": CircuitState.HALF_OPEN,
            "timestamp": datetime.now()
        })
    
    def _transition_to_open(self):
        """Transition to OPEN state."""
        logger.warning(f"Circuit breaker '{self.name}' transitioning to OPEN state")
        self._state = CircuitState.OPEN
        self._last_failure_time = datetime.now()
        self._failure_count = 0
        self.metrics.state_changes.append({
            "from": self._state,
            "to": CircuitState.OPEN,
            "timestamp": datetime.now()
        })
    
    def _transition_to_closed(self):
        """Transition to CLOSED state."""
        logger.info(f"Circuit breaker '{self.name}' transitioning to CLOSED state")
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self.metrics.state_changes.append({
            "from": self._state,
            "to": CircuitState.CLOSED,
            "timestamp": datetime.now()
        })
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        return asyncio.run(self.async_call(func, *args, **kwargs))
    
    async def async_call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function through circuit breaker."""
        with self._lock:
            if self.state == CircuitState.OPEN:
                self.metrics.rejected_calls += 1
                self.metrics.total_calls += 1
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN"
                )
            
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    self.metrics.rejected_calls += 1
                    self.metrics.total_calls += 1
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is HALF_OPEN and max calls reached"
                    )
                self._half_open_calls += 1
        
        # Execute the function
        start_time = time.time()
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            duration = time.time() - start_time
            
            with self._lock:
                self._on_success(duration)
            
            return result
            
        except self.config.exclude_exceptions:
            # These exceptions don't count as failures
            raise
            
        except self.config.expected_exception as e:
            duration = time.time() - start_time
            
            with self._lock:
                self._on_failure(duration)
            
            raise
    
    def _on_success(self, duration: float):
        """Handle successful call."""
        self.metrics.total_calls += 1
        self.metrics.successful_calls += 1
        self.metrics.last_success_time = datetime.now()
        self.metrics.add_call_duration(duration)
        
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._transition_to_closed()
        else:
            self._failure_count = 0  # Reset failure count on success
    
    def _on_failure(self, duration: float):
        """Handle failed call."""
        self.metrics.total_calls += 1
        self.metrics.failed_calls += 1
        self.metrics.last_failure_time = datetime.now()
        self.metrics.add_call_duration(duration)
        
        self._failure_count += 1
        
        if self._state == CircuitState.CLOSED:
            if self._failure_count >= self.config.failure_threshold:
                self._transition_to_open()
        elif self._state == CircuitState.HALF_OPEN:
            self._transition_to_open()
    
    def reset(self):
        """Manually reset the circuit breaker."""
        with self._lock:
            self._transition_to_closed()
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status and metrics."""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "metrics": {
                    "total_calls": self.metrics.total_calls,
                    "successful_calls": self.metrics.successful_calls,
                    "failed_calls": self.metrics.failed_calls,
                    "rejected_calls": self.metrics.rejected_calls,
                    "success_rate": self.metrics.get_success_rate(),
                    "average_duration": self.metrics.get_average_duration(),
                    "last_failure": self.metrics.last_failure_time.isoformat() if self.metrics.last_failure_time else None,
                    "last_success": self.metrics.last_success_time.isoformat() if self.metrics.last_success_time else None,
                },
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_timeout": self.config.recovery_timeout,
                    "success_threshold": self.config.success_threshold,
                }
            }


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


# Global registry of circuit breakers
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_registry_lock = Lock()


def get_circuit_breaker(
    name: str, 
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    with _registry_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(name, config)
        return _circuit_breakers[name]


def circuit_breaker(
    name: Optional[str] = None,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception,
    success_threshold: int = 2,
    exclude_exceptions: tuple = ()
):
    """
    Decorator to apply circuit breaker pattern to a function.
    
    Args:
        name: Circuit breaker name (defaults to function name)
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exception types to catch
        success_threshold: Successful calls needed to close circuit
        exclude_exceptions: Exceptions that don't count as failures
    
    Example:
        @circuit_breaker(name="external_api", failure_threshold=3)
        async def call_external_api():
            return await external_service.fetch_data()
    """
    def decorator(func: Callable) -> Callable:
        cb_name = name or f"{func.__module__}.{func.__name__}"
        config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            success_threshold=success_threshold,
            exclude_exceptions=exclude_exceptions
        )
        
        cb = get_circuit_breaker(cb_name, config)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await cb.async_call(func, *args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def get_all_circuit_breakers() -> Dict[str, Dict[str, Any]]:
    """Get status of all circuit breakers."""
    with _registry_lock:
        return {
            name: cb.get_status()
            for name, cb in _circuit_breakers.items()
        }


def reset_all_circuit_breakers():
    """Reset all circuit breakers to closed state."""
    with _registry_lock:
        for cb in _circuit_breakers.values():
            cb.reset()
    logger.info("All circuit breakers have been reset")


# Example usage for critical services
@circuit_breaker(
    name="openai_api",
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=(ConnectionError, TimeoutError)
)
async def call_openai_api(*args, **kwargs):
    """Example protected OpenAI API call."""
    # This would be imported from the actual service
    pass


@circuit_breaker(
    name="supabase_db",
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=(ConnectionError, TimeoutError)
)
async def query_database(*args, **kwargs):
    """Example protected database query."""
    # This would be imported from the actual service
    pass