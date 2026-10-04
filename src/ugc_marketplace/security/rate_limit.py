"""Rate limiting middleware for UGC Marketplace."""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ugc_marketplace.config import get_settings

logger = structlog.get_logger(__name__)


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""

    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 60
    burst_size: int = 10
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    key_prefix: str = "ratelimit"


@dataclass
class RateLimitEntry:
    """Entry for tracking rate limit state."""

    requests: list[float] = field(default_factory=list)
    tokens: float = 0.0
    last_update: float = 0.0


class RateLimiter:
    """In-memory rate limiter with multiple strategies.

    Uses a sliding window algorithm by default. Entries are stored in memory
    and cleaned up periodically. For production use, consider using Redis
    as a backend.
    """

    def __init__(
        self,
        config: RateLimitConfig | None = None,
    ) -> None:
        self.config = config or RateLimitConfig()
        self._storage: dict[str, RateLimitEntry] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # Cleanup every 60 seconds

    def _get_key(self, request: Request) -> str:
        """Generate a rate limit key for a request.

        Uses the client IP address and the authenticated user ID if available.

        Args:
            request: The incoming request.

        Returns:
            The rate limit key.
        """
        client_ip = request.client.host if request.client else "unknown"
        user = getattr(request.state, "user", None)
        if user:
            return f"{self.config.key_prefix}:user:{user.user_id}"
        return f"{self.config.key_prefix}:ip:{client_ip}"

    def _cleanup(self) -> None:
        """Remove expired entries from storage."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        cutoff = now - 60  # Remove entries older than 60 seconds
        keys_to_remove = [
            key
            for key, entry in self._storage.items()
            if entry.requests and entry.requests[-1] < cutoff
        ]
        for key in keys_to_remove:
            del self._storage[key]

        self._last_cleanup = now

    def _is_allowed_fixed_window(self, key: str) -> tuple[bool, dict[str, Any]]:
        """Check if request is allowed using fixed window strategy.

        Args:
            key: The rate limit key.

        Returns:
            Tuple of (allowed, metadata).
        """
        now = time.time()
        window_start = int(now / 60) * 60

        entry = self._storage.get(key)
        if entry is None or entry.last_update < window_start:
            self._storage[key] = RateLimitEntry(requests=[now], last_update=now)
            return True, {"remaining": self.config.requests_per_minute - 1, "reset": window_start + 60}

        if len(entry.requests) >= self.config.requests_per_minute:
            return False, {"remaining": 0, "reset": window_start + 60}

        entry.requests.append(now)
        entry.last_update = now
        remaining = self.config.requests_per_minute - len(entry.requests)
        return True, {"remaining": remaining, "reset": window_start + 60}

    def _is_allowed_sliding_window(self, key: str) -> tuple[bool, dict[str, Any]]:
        """Check if request is allowed using sliding window strategy.

        Args:
            key: The rate limit key.

        Returns:
            Tuple of (allowed, metadata).
        """
        now = time.time()
        window_start = now - 60

        entry = self._storage.get(key)
        if entry is None:
            self._storage[key] = RateLimitEntry(requests=[now], last_update=now)
            return True, {"remaining": self.config.requests_per_minute - 1, "reset": now + 60}

        # Remove requests outside the window
        entry.requests = [t for t in entry.requests if t > window_start]

        if len(entry.requests) >= self.config.requests_per_minute:
            reset_time = entry.requests[0] + 60 if entry.requests else now + 60
            return False, {"remaining": 0, "reset": reset_time}

        entry.requests.append(now)
        entry.last_update = now
        remaining = self.config.requests_per_minute - len(entry.requests)
        reset_time = entry.requests[0] + 60 if entry.requests else now + 60
        return True, {"remaining": remaining, "reset": reset_time}

    def _is_allowed_token_bucket(self, key: str) -> tuple[bool, dict[str, Any]]:
        """Check if request is allowed using token bucket strategy.

        Args:
            key: The rate limit key.

        Returns:
            Tuple of (allowed, metadata).
        """
        now = time.time()
        entry = self._storage.get(key)

        if entry is None:
            self._storage[key] = RateLimitEntry(
                tokens=self.config.burst_size - 1,
                last_update=now,
            )
            return True, {"remaining": self.config.burst_size - 1, "reset": now + 60}

        # Add tokens based on time passed
        time_passed = now - entry.last_update
        tokens_to_add = time_passed * (self.config.requests_per_minute / 60)
        entry.tokens = min(self.config.burst_size, entry.tokens + tokens_to_add)
        entry.last_update = now

        if entry.tokens < 1:
            reset_time = now + (1 - entry.tokens) / (self.config.requests_per_minute / 60)
            return False, {"remaining": 0, "reset": reset_time}

        entry.tokens -= 1
        return True, {"remaining": int(entry.tokens), "reset": now + 60}

    def is_allowed(self, request: Request) -> tuple[bool, dict[str, Any]]:
        """Check if a request is allowed under the rate limit.

        Args:
            request: The incoming request.

        Returns:
            Tuple of (allowed, metadata).
        """
        self._cleanup()
        key = self._get_key(request)

        if self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
            return self._is_allowed_fixed_window(key)
        elif self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return self._is_allowed_token_bucket(key)
        else:
            return self._is_allowed_sliding_window(key)


# Singleton rate limiter
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get the singleton RateLimiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        settings = get_settings()
        config = RateLimitConfig(
            requests_per_minute=getattr(settings, "rate_limit_requests_per_minute", 60),
            burst_size=getattr(settings, "rate_limit_burst_size", 10),
        )
        _rate_limiter = RateLimiter(config)
    return _rate_limiter


# ── Rate Limiting Middleware ────────────────────────────────────────────────


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits on incoming requests."""

    def __init__(
        self,
        app: ASGIApp,
        rate_limiter: RateLimiter | None = None,
        exclude_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.rate_limiter = rate_limiter or get_rate_limiter()
        self.exclude_paths = exclude_paths or {"/api/v1/health", "/api/v1/health/ready", "/api/v1/health/live"}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> JSONResponse:
        """Process the request through rate limiting.

        Args:
            request: The incoming request.
            call_next: The next handler in the middleware chain.

        Returns:
            The response from the next handler.
        """
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        allowed, metadata = self.rate_limiter.is_allowed(request)

        if not allowed:
            logger.warning(
                "Rate limit exceeded",
                path=request.url.path,
                method=request.method,
                client=request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please try again later."},
                headers={
                    "X-RateLimit-Limit": str(self.rate_limiter.config.requests_per_minute),
                    "X-RateLimit-Remaining": str(metadata.get("remaining", 0)),
                    "X-RateLimit-Reset": str(int(metadata.get("reset", time.time() + 60))),
                    "Retry-After": str(max(1, int(metadata.get("reset", time.time() + 60) - time.time())),
                },
            )

        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.config.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(metadata.get("remaining", 0))
        response.headers["X-RateLimit-Reset"] = str(int(metadata.get("reset", time.time() + 60)))

        return response


# ── Decorator for Route-Level Rate Limiting ─────────────────────────────────


def rate_limit(
    requests_per_minute: int = 60,
    burst_size: int = 10,
    key_func: Callable | None = None,
) -> Callable:
    """Decorator to apply rate limiting to a specific route.

    Args:
        requests_per_minute: Maximum requests per minute.
        burst_size: Maximum burst size.
        key_func: Optional function to generate a custom rate limit key.

    Returns:
        A decorator that applies rate limiting.
    """
    config = RateLimitConfig(
        requests_per_minute=requests_per_minute,
        burst_size=burst_size,
    )
    limiter = RateLimiter(config)

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get("request")

            if request is None:
                return await func(*args, **kwargs)

            if key_func:
                key = key_func(request)
            else:
                key = limiter._get_key(request)

            allowed, metadata = limiter._is_allowed_sliding_window(key)

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={
                        "X-RateLimit-Limit": str(requests_per_minute),
                        "X-RateLimit-Remaining": str(metadata.get("remaining", 0)),
                        "X-RateLimit-Reset": str(int(metadata.get("reset", time.time() + 60))),
                        "Retry-After": str(max(1, int(metadata.get("reset", time.time() + 60) - time.time())),
                    },
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
