"""Lightweight circuit-breaker decorator for external service calls.

Uses a simple closed/open/half-open state machine with configurable failure
threshold, timeout, and retry logic.  No external dependencies required, which
keeps the dependency tree minimal (carbon-conscious).
"""

import functools
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional, Tuple

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"


class CircuitBreakerError(Exception):
    """Raised when the circuit is open and the call is blocked."""


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: Tuple[type, ...] = (Exception,),
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if self._last_failure_time and (time.monotonic() - self._last_failure_time) >= self.timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("[CircuitBreaker] %s: OPEN -> HALF_OPEN", self.name)
        return self._state

    def call(self, func: Callable, *args, **kwargs) -> Any:
        state = self.state
        if state == CircuitState.OPEN:
            raise CircuitBreakerError(f"Circuit breaker '{self.name}' is OPEN")
        try:
            result = func(*args, **kwargs)
            if state == CircuitState.HALF_OPEN:
                self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure(e)
            raise

    def _on_success(self):
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_time = None
        logger.info("[CircuitBreaker] %s: reset to CLOSED", self.name)

    def _on_failure(self, exc: Exception):
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        logger.warning(
            "[CircuitBreaker] %s: failure %d/%d - %s",
            self.name, self._failure_count, self.failure_threshold, exc,
        )
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.error("[CircuitBreaker] %s: OPEN (threshold reached)", self.name)


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    timeout: float = 60.0,
    expected_exception: Tuple[type, ...] = (Exception,),
):
    """Decorator that wraps a function with circuit-breaker protection.

    Example:
        @circuit_breaker("github-api", failure_threshold=3, timeout=30)
        def fetch_repo(owner, repo):
            ...
    """
    cb = CircuitBreaker(
        name=name,
        failure_threshold=failure_threshold,
        timeout=timeout,
        expected_exception=expected_exception,
    )

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)
        wrapper.__circuit_breaker__ = cb  # type: ignore
        return wrapper
    return decorator
