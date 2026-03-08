"""Tests for the rate limiter."""

from unittest.mock import patch

from surfaced.engine.rate_limiter import RateLimiter


def test_min_interval_calculation():
    limiter = RateLimiter(rpm=60)
    assert limiter._min_interval == 1.0

    limiter2 = RateLimiter(rpm=30)
    assert limiter2._min_interval == 2.0


def test_rpm_zero_never_sleeps():
    limiter = RateLimiter(rpm=0)
    assert limiter._min_interval == 0.0
    with patch("surfaced.engine.rate_limiter.time") as mock_time:
        mock_time.time.return_value = 100.0
        limiter.wait()
        mock_time.sleep.assert_not_called()


def test_first_call_no_sleep():
    limiter = RateLimiter(rpm=60)
    with patch("surfaced.engine.rate_limiter.time") as mock_time:
        mock_time.time.return_value = 100.0
        limiter.wait()
        mock_time.sleep.assert_not_called()


def test_second_call_sleeps_if_too_soon():
    limiter = RateLimiter(rpm=60)
    limiter._last_request = 99.5  # 0.5s ago

    with patch("surfaced.engine.rate_limiter.time") as mock_time:
        mock_time.time.return_value = 100.0
        limiter.wait()
        # min_interval=1.0, elapsed=0.5, need to sleep 0.5s
        mock_time.sleep.assert_called_once_with(0.5)
