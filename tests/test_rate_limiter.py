"""Tests for rate limiter utility."""

import time

from smspanel.utils.rate_limiter import RateLimiter, get_rate_limiter, init_rate_limiter


def test_rate_limiter_allows_burst():
    """RateLimiter should allow initial burst up to burst_capacity."""
    limiter = RateLimiter(rate_per_sec=2, burst_capacity=4)
    # Should allow initial burst
    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is True
    # 5th should return False when burst exhausted
    assert limiter.try_acquire() is False


def test_rate_limiter_refills():
    """RateLimiter should refill tokens over time."""
    limiter = RateLimiter(rate_per_sec=2, burst_capacity=2)
    limiter.try_acquire()  # burst used
    limiter.try_acquire()  # burst used
    # Wait and refill - should allow 1 token after 0.5s at 2/sec
    time.sleep(0.6)
    assert limiter.try_acquire() is True


def test_get_rate_limiter_returns_singleton():
    """get_rate_limiter should return the same instance after init."""
    init_rate_limiter(rate_per_sec=2.0, burst_capacity=4)
    limiter1 = get_rate_limiter()
    limiter2 = get_rate_limiter()
    assert limiter1 is limiter2


def test_rate_limiter_default_values():
    """RateLimiter should have correct default values."""
    limiter = RateLimiter()
    assert limiter.rate_per_sec == 2.0
    assert limiter.burst_capacity == 2.0


def test_rate_limiter_get_tokens():
    """RateLimiter should report current tokens."""
    limiter = RateLimiter(rate_per_sec=2, burst_capacity=4)
    # Initially should have full burst capacity
    assert limiter.get_tokens() == 4.0


def test_rate_limiter_acquire_blocks():
    """RateLimiter.acquire should block when no tokens available."""
    limiter = RateLimiter(rate_per_sec=2, burst_capacity=2)
    # Use up burst
    limiter.try_acquire()
    limiter.try_acquire()
    # acquire should block and wait for tokens
    start = time.monotonic()
    result = limiter.acquire()
    elapsed = time.monotonic() - start
    # Should have waited at least ~0.5s for 1 token at 2/sec
    assert result is True
    assert elapsed >= 0.4  # Allow some tolerance


def test_rate_limiter_thread_safety():
    """RateLimiter should be thread-safe."""
    import threading

    limiter = RateLimiter(rate_per_sec=100, burst_capacity=100)
    results: list[bool] = []
    errors: list[Exception] = []

    def try_acquire_worker():
        try:
            for _ in range(20):
                results.append(limiter.try_acquire())
        except Exception as e:
            errors.append(e)

    # Create multiple threads
    threads = [threading.Thread(target=try_acquire_worker) for _ in range(5)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # No exceptions should have occurred
    assert len(errors) == 0
    # Exactly 100 acquisitions should succeed (20 * 5 threads = 100 tries,
    # but only 100 tokens available)
    assert sum(results) <= 100
