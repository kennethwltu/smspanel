"""Token bucket rate limiter for SMS gateway throughput control."""

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger("smspanel")


class RateLimiter:
    """Thread-safe token bucket rate limiter.

    Implements a token bucket algorithm for rate limiting SMS gateway throughput.
    Tokens are added at a constant rate up to a maximum burst capacity.

    Args:
        rate_per_sec: Number of tokens to add per second (default: 2.0).
        burst_capacity: Maximum number of tokens that can be accumulated
            (default: equal to rate_per_sec).

    Example:
        >>> limiter = RateLimiter(rate_per_sec=2.0, burst_capacity=4)
        >>> if limiter.try_acquire():
        ...     # Token acquired, proceed with operation
        ...     pass
    """

    def __init__(
        self, rate_per_sec: float = 2.0, burst_capacity: Optional[float] = None
    ) -> None:
        self.rate_per_sec = rate_per_sec
        self.burst_capacity = burst_capacity if burst_capacity is not None else rate_per_sec

        self._tokens: float = self.burst_capacity
        self._last_update: float = time.monotonic()
        self._lock = threading.Lock()

    def _add_tokens(self) -> None:
        """Add tokens based on elapsed time since last update."""
        now = time.monotonic()
        elapsed = now - self._last_update

        if elapsed > 0:
            tokens_to_add = elapsed * self.rate_per_sec
            self._tokens = min(self.burst_capacity, self._tokens + tokens_to_add)
            self._last_update = now

    def try_acquire(self) -> bool:
        """Try to acquire a token without blocking.

        Returns:
            True if a token was acquired, False otherwise.
        """
        with self._lock:
            self._add_tokens()

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    def acquire(self, timeout: float = 10.0) -> bool:
        """Acquire a token, blocking if necessary.

        Blocks until a token is available or timeout expires.

        Args:
            timeout: Maximum time to wait in seconds (default: 10.0).

        Returns:
            True if a token was acquired, False if timeout expired.
        """
        start_time = time.monotonic()

        while True:
            with self._lock:
                self._add_tokens()

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True

            # Calculate wait time
            elapsed = time.monotonic() - start_time
            if elapsed >= timeout:
                return False

            # Wait for tokens to accumulate
            tokens_needed = 1.0 - self._tokens
            wait_time = tokens_needed / self.rate_per_sec

            # Don't wait longer than remaining timeout
            wait_time = min(wait_time, timeout - elapsed)

            if wait_time > 0:
                time.sleep(wait_time)

        # Unreachable, but makes mypy happy
        return False

    def get_tokens(self) -> float:
        """Get current number of available tokens.

        Returns:
            Current token count (may be fractional).
        """
        with self._lock:
            self._add_tokens()
            return self._tokens


# Global rate limiter instance for application-wide use
_rate_limiter: Optional[RateLimiter] = None


def init_rate_limiter(rate_per_sec: float = 2.0, burst_capacity: Optional[float] = None) -> RateLimiter:
    """Initialize the global rate limiter instance.

    Should be called during application startup.

    Args:
        rate_per_sec: Number of tokens to add per second (default: 2.0).
        burst_capacity: Maximum number of tokens that can be accumulated
            (default: equal to rate_per_sec).

    Returns:
        The initialized RateLimiter instance.
    """
    global _rate_limiter
    _rate_limiter = RateLimiter(rate_per_sec=rate_per_sec, burst_capacity=burst_capacity)
    logger.info(
        "Rate limiter initialized: rate=%.1f tokens/sec, burst=%s",
        rate_per_sec,
        burst_capacity if burst_capacity is not None else rate_per_sec,
    )
    return _rate_limiter


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance.

    Returns:
        The global RateLimiter instance.

    Raises:
        RuntimeError: If the rate limiter has not been initialized.
    """
    global _rate_limiter
    if _rate_limiter is None:
        raise RuntimeError(
            "Rate limiter not initialized. Call init_rate_limiter() first."
        )
    return _rate_limiter
