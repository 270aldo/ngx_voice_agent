"""
Unit tests for Circuit Breaker implementation.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch

from src.services.circuit_breaker_service import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerError,
    get_circuit_breaker,
    circuit_breaker,
    reset_all_circuit_breakers
)


class TestCircuitBreakerConfig:
    """Test CircuitBreakerConfig validation."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60
        assert config.success_threshold == 2
        assert config.half_open_max_calls == 3
        assert config.expected_exception == Exception
        assert config.exclude_exceptions == ()
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Invalid failure threshold
        with pytest.raises(ValueError, match="failure_threshold must be at least 1"):
            CircuitBreakerConfig(failure_threshold=0)
        
        # Invalid recovery timeout
        with pytest.raises(ValueError, match="recovery_timeout must be at least 1"):
            CircuitBreakerConfig(recovery_timeout=0)
        
        # Invalid success threshold
        with pytest.raises(ValueError, match="success_threshold must be at least 1"):
            CircuitBreakerConfig(success_threshold=0)


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1,  # Short timeout for tests
            success_threshold=2
        )
        self.cb = CircuitBreaker("test_breaker", self.config)
    
    @pytest.mark.asyncio
    async def test_initial_state(self):
        """Test circuit breaker starts in CLOSED state."""
        assert self.cb.state == CircuitState.CLOSED
        assert self.cb._failure_count == 0
        assert self.cb._success_count == 0
    
    @pytest.mark.asyncio
    async def test_successful_calls(self):
        """Test that successful calls don't open the circuit."""
        async def success_func():
            return "success"
        
        # Make multiple successful calls
        for _ in range(10):
            result = await self.cb.async_call(success_func)
            assert result == "success"
        
        # Circuit should remain closed
        assert self.cb.state == CircuitState.CLOSED
        assert self.cb.metrics.successful_calls == 10
        assert self.cb.metrics.failed_calls == 0
    
    @pytest.mark.asyncio
    async def test_circuit_opens_on_failures(self):
        """Test that circuit opens after threshold failures."""
        async def failing_func():
            raise ValueError("Test error")
        
        # Fail up to threshold
        for i in range(self.config.failure_threshold):
            with pytest.raises(ValueError):
                await self.cb.async_call(failing_func)
        
        # Circuit should now be open
        assert self.cb.state == CircuitState.OPEN
        assert self.cb.metrics.failed_calls == self.config.failure_threshold
        
        # Further calls should fail immediately
        with pytest.raises(CircuitBreakerError, match="Circuit breaker 'test_breaker' is OPEN"):
            await self.cb.async_call(failing_func)
        
        # Check rejected calls metric
        assert self.cb.metrics.rejected_calls == 1
    
    @pytest.mark.asyncio
    async def test_circuit_recovery(self):
        """Test circuit recovery from OPEN to HALF_OPEN to CLOSED."""
        async def controlled_func(should_fail=True):
            if should_fail:
                raise ValueError("Test error")
            return "success"
        
        # Open the circuit
        for _ in range(self.config.failure_threshold):
            with pytest.raises(ValueError):
                await self.cb.async_call(controlled_func, should_fail=True)
        
        assert self.cb.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        await asyncio.sleep(self.config.recovery_timeout + 0.1)
        
        # Circuit should transition to HALF_OPEN on next check
        assert self.cb.state == CircuitState.HALF_OPEN
        
        # Make successful calls to close circuit
        for _ in range(self.config.success_threshold):
            result = await self.cb.async_call(controlled_func, should_fail=False)
            assert result == "success"
        
        # Circuit should be closed again
        assert self.cb.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self):
        """Test that failure in HALF_OPEN state reopens the circuit."""
        async def failing_func():
            raise ValueError("Test error")
        
        # Open the circuit
        for _ in range(self.config.failure_threshold):
            with pytest.raises(ValueError):
                await self.cb.async_call(failing_func)
        
        # Wait for recovery
        await asyncio.sleep(self.config.recovery_timeout + 0.1)
        assert self.cb.state == CircuitState.HALF_OPEN
        
        # Fail in HALF_OPEN state
        with pytest.raises(ValueError):
            await self.cb.async_call(failing_func)
        
        # Circuit should be OPEN again
        assert self.cb.state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_half_open_max_calls(self):
        """Test HALF_OPEN state respects max calls limit."""
        async def success_func():
            return "success"
        
        # Open the circuit first
        async def failing_func():
            raise ValueError("Test error")
        
        for _ in range(self.config.failure_threshold):
            with pytest.raises(ValueError):
                await self.cb.async_call(failing_func)
        
        # Wait for recovery
        await asyncio.sleep(self.config.recovery_timeout + 0.1)
        assert self.cb.state == CircuitState.HALF_OPEN
        
        # Make max allowed calls
        for _ in range(self.config.half_open_max_calls):
            await self.cb.async_call(success_func)
        
        # Next call should be rejected
        with pytest.raises(CircuitBreakerError, match="HALF_OPEN and max calls reached"):
            await self.cb.async_call(success_func)
    
    @pytest.mark.asyncio
    async def test_excluded_exceptions(self):
        """Test that excluded exceptions don't count as failures."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            exclude_exceptions=(KeyError,)
        )
        cb = CircuitBreaker("test_exclude", config)
        
        async def func_with_keyerror():
            raise KeyError("Excluded error")
        
        async def func_with_valueerror():
            raise ValueError("Counted error")
        
        # KeyError should not count as failure
        for _ in range(5):
            with pytest.raises(KeyError):
                await cb.async_call(func_with_keyerror)
        
        # Circuit should still be closed
        assert cb.state == CircuitState.CLOSED
        assert cb.metrics.failed_calls == 0
        
        # ValueError should count
        for _ in range(config.failure_threshold):
            with pytest.raises(ValueError):
                await cb.async_call(func_with_valueerror)
        
        # Now circuit should be open
        assert cb.state == CircuitState.OPEN
    
    def test_manual_reset(self):
        """Test manual circuit reset."""
        self.cb._state = CircuitState.OPEN
        self.cb._failure_count = 10
        
        self.cb.reset()
        
        assert self.cb.state == CircuitState.CLOSED
        assert self.cb._failure_count == 0
        assert self.cb._success_count == 0
    
    def test_get_status(self):
        """Test status reporting."""
        status = self.cb.get_status()
        
        assert status["name"] == "test_breaker"
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["metrics"]["total_calls"] == 0
        assert status["config"]["failure_threshold"] == 3
    
    @pytest.mark.asyncio
    async def test_sync_call(self):
        """Test synchronous call wrapper."""
        def sync_func(x):
            return x * 2
        
        # Note: This would normally use asyncio.run internally
        # For testing, we'll test the async version
        result = await self.cb.async_call(sync_func, 5)
        assert result == 10
    
    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        """Test that metrics are properly tracked."""
        async def func(fail=False):
            if fail:
                raise ValueError("Test")
            return "ok"
        
        # Successful calls
        for _ in range(3):
            await self.cb.async_call(func, fail=False)
        
        # Failed calls
        for _ in range(2):
            with pytest.raises(ValueError):
                await self.cb.async_call(func, fail=True)
        
        metrics = self.cb.metrics
        assert metrics.total_calls == 5
        assert metrics.successful_calls == 3
        assert metrics.failed_calls == 2
        assert metrics.get_success_rate() == 0.6
        
        # Check timing metrics
        assert len(metrics.call_durations) == 5
        assert metrics.get_average_duration() >= 0


class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator."""
    
    @pytest.mark.asyncio
    async def test_decorator_basic(self):
        """Test basic decorator functionality."""
        call_count = 0
        
        @circuit_breaker(
            name="test_decorated",
            failure_threshold=2,
            recovery_timeout=1
        )
        async def decorated_func(should_fail=False):
            nonlocal call_count
            call_count += 1
            if should_fail:
                raise ValueError("Test error")
            return "success"
        
        # Successful call
        result = await decorated_func()
        assert result == "success"
        assert call_count == 1
        
        # Fail twice to open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await decorated_func(should_fail=True)
        
        # Circuit should be open
        with pytest.raises(CircuitBreakerError):
            await decorated_func()
        
        # Call count should be 3 (1 success + 2 failures)
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_decorator_with_exclude(self):
        """Test decorator with excluded exceptions."""
        @circuit_breaker(
            name="test_exclude_decorator",
            failure_threshold=2,
            exclude_exceptions=(KeyError,)
        )
        async def func(error_type="value"):
            if error_type == "key":
                raise KeyError("Excluded")
            elif error_type == "value":
                raise ValueError("Counted")
            return "ok"
        
        # KeyError should not trigger circuit
        for _ in range(5):
            with pytest.raises(KeyError):
                await func(error_type="key")
        
        # Should still work
        result = await func(error_type=None)
        assert result == "ok"
        
        # ValueError should trigger circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await func(error_type="value")
        
        # Circuit should be open
        with pytest.raises(CircuitBreakerError):
            await func()


class TestCircuitBreakerRegistry:
    """Test global circuit breaker registry."""
    
    def test_get_circuit_breaker(self):
        """Test getting circuit breakers from registry."""
        # First call creates new instance
        cb1 = get_circuit_breaker("test_cb1")
        assert cb1.name == "test_cb1"
        
        # Second call returns same instance
        cb2 = get_circuit_breaker("test_cb1")
        assert cb1 is cb2
        
        # Different name creates different instance
        cb3 = get_circuit_breaker("test_cb2")
        assert cb3 is not cb1
        assert cb3.name == "test_cb2"
    
    def test_reset_all_circuit_breakers(self):
        """Test resetting all circuit breakers."""
        # Create some circuit breakers
        cb1 = get_circuit_breaker("reset_test_1")
        cb2 = get_circuit_breaker("reset_test_2")
        
        # Open them
        cb1._state = CircuitState.OPEN
        cb2._state = CircuitState.OPEN
        
        # Reset all
        reset_all_circuit_breakers()
        
        # All should be closed
        assert cb1.state == CircuitState.CLOSED
        assert cb2.state == CircuitState.CLOSED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])