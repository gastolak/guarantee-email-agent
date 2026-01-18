"""Circuit breaker pattern for external service resilience.

Implements circuit breaker to prevent cascading failures when external
services are down. Each integration (Gmail, Warranty API, Ticketing) has
an independent circuit breaker.
"""

import logging
import time
from enum import Enum
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Circuit breaker for external service calls.

    Opens after consecutive failures, preventing further calls.
    Automatically attempts recovery after timeout period.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ):
        """Initialize circuit breaker.

        Args:
            name: Circuit breaker name (e.g., "gmail", "warranty_api")
            failure_threshold: Number of consecutive failures before opening (default: 5)
            recovery_timeout: Seconds to wait before attempting recovery (default: 60)
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

        logger.info(
            f"Circuit breaker initialized: {name} "
            f"(threshold={failure_threshold}, timeout={recovery_timeout}s)"
        )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func execution

        Raises:
            CircuitBreakerError: If circuit is open
        """
        # Check if circuit should transition states
        self._check_state_transition()

        if self.state == CircuitState.OPEN:
            logger.warning(
                f"Circuit breaker OPEN for {self.name} - failing fast"
            )
            raise CircuitBreakerError(
                f"Circuit breaker open for {self.name} "
                f"(failed {self.failure_count} times)"
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise

    def _check_state_transition(self) -> None:
        """Check if circuit should transition to different state."""
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.recovery_timeout:
                    logger.info(
                        f"Circuit breaker {self.name}: OPEN → HALF_OPEN "
                        f"(recovery timeout elapsed: {elapsed:.1f}s)"
                    )
                    self.state = CircuitState.HALF_OPEN

    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            # Recovery successful - close circuit
            logger.info(
                f"Circuit breaker {self.name}: HALF_OPEN → CLOSED "
                f"(service recovered)"
            )
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None

        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                logger.debug(
                    f"Circuit breaker {self.name}: Reset failure count "
                    f"({self.failure_count} → 0)"
                )
                self.failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Failed during recovery - reopen circuit
            logger.warning(
                f"Circuit breaker {self.name}: HALF_OPEN → OPEN "
                f"(recovery attempt failed)"
            )
            self.state = CircuitState.OPEN

        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                # Threshold reached - open circuit
                logger.error(
                    f"Circuit breaker {self.name}: CLOSED → OPEN "
                    f"(failure threshold reached: {self.failure_count})"
                )
                self.state = CircuitState.OPEN
            else:
                logger.warning(
                    f"Circuit breaker {self.name}: Failure {self.failure_count}/"
                    f"{self.failure_threshold}"
                )

    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        logger.info(f"Circuit breaker {self.name}: Manual reset to CLOSED")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        self._check_state_transition()
        return self.state == CircuitState.OPEN


def with_circuit_breaker(circuit_breaker: CircuitBreaker):
    """Decorator to wrap function with circuit breaker.

    Args:
        circuit_breaker: CircuitBreaker instance to use

    Example:
        @with_circuit_breaker(gmail_breaker)
        async def send_email(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return circuit_breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator
