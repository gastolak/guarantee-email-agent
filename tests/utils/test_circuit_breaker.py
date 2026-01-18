import pytest
import time
from guarantee_email_agent.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerError
)


def test_circuit_breaker_initialization():
    """Test circuit breaker initialization"""
    cb = CircuitBreaker("test_service", failure_threshold=3, recovery_timeout=5)
    assert cb.name == "test_service"
    assert cb.failure_threshold == 3
    assert cb.recovery_timeout == 5
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_successful_calls():
    """Test circuit remains closed on successful calls"""
    cb = CircuitBreaker("test_service")

    def success_func():
        return "success"

    result = cb.call(success_func)
    assert result == "success"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_opens_after_failures():
    """Test circuit opens after failure threshold"""
    cb = CircuitBreaker("test_service", failure_threshold=3)

    def failing_func():
        raise ValueError("Test error")

    # First 2 failures
    for i in range(2):
        with pytest.raises(ValueError):
            cb.call(failing_func)
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == i + 1

    # Third failure should open circuit
    with pytest.raises(ValueError):
        cb.call(failing_func)

    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 3


def test_circuit_breaker_fails_fast_when_open():
    """Test circuit breaker fails fast when open"""
    cb = CircuitBreaker("test_service", failure_threshold=2)

    def failing_func():
        raise ValueError("Test error")

    # Trigger failures to open circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(failing_func)

    assert cb.state == CircuitState.OPEN

    # Next call should fail fast with CircuitBreakerError
    with pytest.raises(CircuitBreakerError) as exc_info:
        cb.call(failing_func)

    assert "Circuit breaker open" in str(exc_info.value)


def test_circuit_breaker_transitions_to_half_open():
    """Test circuit transitions to half-open after recovery timeout"""
    cb = CircuitBreaker("test_service", failure_threshold=2, recovery_timeout=1)

    def failing_func():
        raise ValueError("Test error")

    # Open circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(failing_func)

    assert cb.state == CircuitState.OPEN

    # Wait for recovery timeout
    time.sleep(1.1)

    # Check state transition
    cb._check_state_transition()
    assert cb.state == CircuitState.HALF_OPEN


def test_circuit_breaker_closes_on_half_open_success():
    """Test circuit closes when half-open call succeeds"""
    cb = CircuitBreaker("test_service", failure_threshold=2, recovery_timeout=1)

    def failing_func():
        raise ValueError("Test error")

    def success_func():
        return "success"

    # Open circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(failing_func)

    assert cb.state == CircuitState.OPEN

    # Wait for recovery
    time.sleep(1.1)
    cb._check_state_transition()
    assert cb.state == CircuitState.HALF_OPEN

    # Successful call should close circuit
    result = cb.call(success_func)
    assert result == "success"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_reopens_on_half_open_failure():
    """Test circuit reopens when half-open call fails"""
    cb = CircuitBreaker("test_service", failure_threshold=2, recovery_timeout=1)

    def failing_func():
        raise ValueError("Test error")

    # Open circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(failing_func)

    assert cb.state == CircuitState.OPEN

    # Wait for recovery
    time.sleep(1.1)
    cb._check_state_transition()
    assert cb.state == CircuitState.HALF_OPEN

    # Failed call should reopen circuit
    with pytest.raises(ValueError):
        cb.call(failing_func)

    assert cb.state == CircuitState.OPEN


def test_circuit_breaker_manual_reset():
    """Test manual circuit breaker reset"""
    cb = CircuitBreaker("test_service", failure_threshold=2)

    def failing_func():
        raise ValueError("Test error")

    # Open circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(failing_func)

    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 2

    # Manual reset
    cb.reset()

    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
    assert cb.last_failure_time is None


def test_circuit_breaker_is_open_property():
    """Test is_open property"""
    cb = CircuitBreaker("test_service", failure_threshold=2)

    assert not cb.is_open

    def failing_func():
        raise ValueError("Test error")

    # Open circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(failing_func)

    assert cb.is_open
