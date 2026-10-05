"""Base integration infrastructure: retry, rate limiting, error recovery."""
import asyncio
import functools
import inspect
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Tuple, Type


class IntegrationError(Exception):
    """Base exception for integration errors."""
    pass


class RateLimitError(IntegrationError):
    """Rate limit exceeded error."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)


@dataclass
class RateLimiter:
    """Token bucket rate limiter."""
    max_requests: int
    window_seconds: float
    _requests: list = field(default_factory=list)

    async def acquire(self):
        """Acquire a rate limit token, waiting if necessary."""
        now = time.monotonic()
        # Remove expired timestamps
        self._requests = [t for t in self._requests if now - t < self.window_seconds]
        
        if len(self._requests) >= self.max_requests:
            # Wait until the oldest request expires
            oldest = self._requests[0]
            wait_time = self.window_seconds - (now - oldest)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            now = time.monotonic()
            self._requests = [t for t in self._requests if now - t < self.window_seconds]
        
        self._requests.append(now)


async def retry_with_backoff(
    operation: Callable,
    config: Optional[RetryConfig] = None,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    **kwargs,
) -> Any:
    """Execute an operation with exponential backoff retry logic."""
    if config is None:
        config = RetryConfig()
    
    # Override config with explicit parameters
    if max_retries is not None:
        config.max_retries = max_retries
    if base_delay is not None:
        config.base_delay = base_delay
    if max_delay is not None:
        config.max_delay = max_delay
    
    exceptions = retryable_exceptions or config.retryable_exceptions
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            result = operation(**kwargs)
            if inspect.isawaitable(result):
                return await result
            return result
        except exceptions as e:
            last_exception = e
            if attempt < config.max_retries:
                delay = min(
                    config.base_delay * (config.exponential_base ** attempt),
                    config.max_delay,
                )
                await asyncio.sleep(delay)
    
    if last_exception is not None:
        raise last_exception
    raise RuntimeError("Unexpected: no exception captured during retries")


class BaseIntegration(ABC):
    """Abstract base class for platform integrations."""
    
    def __init_subclass__(cls, **kwargs):
        """Wrap post() with retry logic for all subclasses."""
        super().__init_subclass__(**kwargs)
        original_post = cls.__dict__.get("post")
        if original_post is not None and not getattr(original_post, "_retry_wrapped", False):
            cls.post = cls._wrap_with_retry(original_post)
    
    @staticmethod
    def _wrap_with_retry(post_method):
        """Wrap a post method with retry logic."""
        @functools.wraps(post_method)
        async def wrapper(self, content: dict) -> dict:
            if self.rate_limiter:
                await self.rate_limiter.acquire()
            return await retry_with_backoff(
                lambda: post_method(self, content),
                config=self.retry_config,
            )
        wrapper._retry_wrapped = True
        return wrapper
    
    def __init__(self, retry_config: Optional[RetryConfig] = None):
        self.retry_config = retry_config or RetryConfig()
        self.rate_limiter: Optional[RateLimiter] = None
    
    @abstractmethod
    async def post(self, content: dict) -> dict:
        """Post content to the platform."""
        pass
    
    @abstractmethod
    async def health_check(self) -> dict:
        """Check platform connectivity."""
        pass
    
    async def execute_with_retry(self, operation: Callable, **kwargs) -> Any:
        """Execute an operation with retry logic."""
        return await retry_with_backoff(
            operation,
            config=self.retry_config,
            **kwargs,
        )
