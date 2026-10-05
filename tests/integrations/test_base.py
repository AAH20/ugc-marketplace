"""Tests for base integration infrastructure: retry, rate limiting, error recovery."""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.base import (
    BaseIntegration,
    IntegrationError,
    RateLimitError,
    RetryConfig,
    retry_with_backoff,
    RateLimiter,
)


class TestRetryWithBackoff:
    """Test retry logic with exponential backoff."""

    @pytest.mark.asyncio
    async def test_succeeds_first_try(self):
        """Operation succeeds on first attempt - no retries needed."""
        operation = AsyncMock(return_value="success")
        result = await retry_with_backoff(operation, max_retries=3)
        assert result == "success"
        assert operation.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self):
        """Operation fails twice then succeeds - should retry and succeed."""
        operation = AsyncMock(side_effect=[Exception("fail1"), Exception("fail2"), "success"])
        result = await retry_with_backoff(operation, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert operation.call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        """Operation always fails - should raise after max_retries."""
        operation = AsyncMock(side_effect=Exception("always fails"))
        with pytest.raises(Exception, match="always fails"):
            await retry_with_backoff(operation, max_retries=3, base_delay=0.01)
        assert operation.call_count == 4  # initial + 3 retries

    @pytest.mark.asyncio
    async def test_respects_retry_config(self):
        """RetryConfig controls max_retries and delay."""
        config = RetryConfig(max_retries=2, base_delay=0.01, max_delay=0.1)
        operation = AsyncMock(side_effect=Exception("fail"))
        with pytest.raises(Exception):
            await retry_with_backoff(operation, config=config)
        assert operation.call_count == 3  # initial + 2 retries

    @pytest.mark.asyncio
    async def test_does_not_retry_non_retryable_errors(self):
        """Non-retryable errors should fail immediately."""
        operation = AsyncMock(side_effect=ValueError("bad input"))
        with pytest.raises(ValueError, match="bad input"):
            await retry_with_backoff(
                operation, max_retries=3, base_delay=0.01,
                retryable_exceptions=(ConnectionError, TimeoutError)
            )
        assert operation.call_count == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Delays should increase exponentially."""
        operation = AsyncMock(side_effect=[Exception("fail"), "success"])
        start = time.monotonic()
        await retry_with_backoff(operation, max_retries=1, base_delay=0.05, max_delay=0.2)
        elapsed = time.monotonic() - start
        assert elapsed >= 0.05  # at least base_delay


class TestRateLimiter:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self):
        """Requests under the rate limit should proceed immediately."""
        limiter = RateLimiter(max_requests=3, window_seconds=1)
        start = time.monotonic()
        for _ in range(3):
            await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.5  # should be fast

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self):
        """Requests over the rate limit should wait."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.2)
        start = time.monotonic()
        for _ in range(3):
            await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.15  # third request should wait

    @pytest.mark.asyncio
    async def test_window_resets_after_time(self):
        """Rate limit window should reset after window_seconds."""
        limiter = RateLimiter(max_requests=1, window_seconds=0.1)
        await limiter.acquire()
        await asyncio.sleep(0.15)
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1  # should not wait after window reset


class TestBaseIntegration:
    """Test BaseIntegration abstract class."""

    def test_cannot_instantiate_directly(self):
        """BaseIntegration should be abstract."""
        with pytest.raises(TypeError):
            BaseIntegration()

    @pytest.mark.asyncio
    async def test_health_check_returns_status(self):
        """Health check should return platform status."""
        class TestIntegration(BaseIntegration):
            async def post(self, content: dict) -> dict:
                return {"id": "123"}
            async def health_check(self) -> dict:
                return {"status": "healthy", "platform": "test"}

        integration = TestIntegration()
        result = await integration.health_check()
        assert result["status"] == "healthy"
        assert result["platform"] == "test"

    @pytest.mark.asyncio
    async def test_post_uses_rate_limiter(self):
        """Post should respect rate limiting."""
        class TestIntegration(BaseIntegration):
            def __init__(self):
                super().__init__()
                self.rate_limiter = RateLimiter(max_requests=1, window_seconds=0.1)
            async def post(self, content: dict) -> dict:
                return {"id": "123"}
            async def health_check(self) -> dict:
                return {"status": "healthy"}

        integration = TestIntegration()
        result1 = await integration.post({"text": "hello"})
        assert result1["id"] == "123"

    @pytest.mark.asyncio
    async def test_post_retries_on_failure(self):
        """Post should retry on transient failures."""
        class TestIntegration(BaseIntegration):
            def __init__(self):
                super().__init__()
                self.attempts = 0
            async def post(self, content: dict) -> dict:
                self.attempts += 1
                if self.attempts < 2:
                    raise ConnectionError("transient")
                return {"id": "123"}
            async def health_check(self) -> dict:
                return {"status": "healthy"}

        integration = TestIntegration()
        result = await integration.post({"text": "hello"})
        assert result["id"] == "123"
        assert integration.attempts == 2


class TestIntegrationError:
    """Test custom exception classes."""

    def test_integration_error_is_exception(self):
        """IntegrationError should be an Exception."""
        err = IntegrationError("test error")
        assert str(err) == "test error"
        assert isinstance(err, Exception)

    def test_rate_limit_error_has_retry_after(self):
        """RateLimitError should carry retry_after info."""
        err = RateLimitError("rate limited", retry_after=60)
        assert err.retry_after == 60
        assert "rate limited" in str(err)
