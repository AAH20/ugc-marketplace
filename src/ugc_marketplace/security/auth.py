"""Authentication middleware and JWT handling for UGC Marketplace."""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable
from enum import Enum
from typing import Any

import structlog
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ugc_marketplace.config import get_settings

logger = structlog.get_logger(__name__)


class UserRole(str, Enum):
    """User roles for authorization."""

    ADMIN = "admin"
    MODERATOR = "moderator"
    CREATOR = "creator"
    USER = "user"
    SERVICE = "service"


# ── JWT Token Management ────────────────────────────────────────────────────


class TokenManager:
    """Manage JWT token creation and validation."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.secret_key = self.settings.secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7

    def create_access_token(
        self,
        subject: str,
        roles: list[UserRole] | None = None,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """Create a new JWT access token.

        Args:
            subject: The subject (user ID) of the token.
            roles: List of user roles.
            extra_claims: Additional claims to include.

        Returns:
            Encoded JWT token string.
        """
        now = time.time()
        expires = now + (self.access_token_expire_minutes * 60)

        payload: dict[str, Any] = {
            "sub": subject,
            "iat": now,
            "exp": expires,
            "type": "access",
            "roles": [r.value for r in (roles or [UserRole.USER])],
        }

        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, subject: str) -> str:
        """Create a new JWT refresh token.

        Args:
            subject: The subject (user ID) of the token.

        Returns:
            Encoded JWT refresh token string.
        """
        now = time.time()
        expires = now + (self.refresh_token_expire_days * 24 * 60 * 60)

        payload: dict[str, Any] = {
            "sub": subject,
            "iat": now,
            "exp": expires,
            "type": "refresh",
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT token.

        Args:
            token: The JWT token string.

        Returns:
            Decoded token payload.

        Raises:
            HTTPException: If token is invalid or expired.
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as exc:
            logger.warning("Invalid token", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    def verify_access_token(self, token: str) -> dict[str, Any]:
        """Verify an access token and return its payload.

        Args:
            token: The JWT access token.

        Returns:
            Decoded token payload.

        Raises:
            HTTPException: If token is invalid, expired, or wrong type.
        """
        payload = self.decode_token(token)

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload


# Singleton token manager
_token_manager: TokenManager | None = None


def get_token_manager() -> TokenManager:
    """Get the singleton TokenManager instance."""
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager


# ── User Context ─────────────────────────────────────────────────────────────


class AuthenticatedUser:
    """Represents an authenticated user in the request context."""

    def __init__(
        self,
        user_id: str,
        roles: list[UserRole],
        email: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.user_id = user_id
        self.roles = roles
        self.email = email
        self.metadata = metadata or {}

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return UserRole.ADMIN in self.roles

    @property
    def is_moderator(self) -> bool:
        """Check if user has moderator role."""
        return UserRole.MODERATOR in self.roles

    @property
    def is_creator(self) -> bool:
        """Check if user has creator role."""
        return UserRole.CREATOR in self.roles

    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_any_role(self, roles: list[UserRole]) -> bool:
        """Check if user has any of the specified roles."""
        return any(r in self.roles for r in roles)


# ── Authentication Middleware ────────────────────────────────────────────────


# Paths that don't require authentication
PUBLIC_PATHS: set[str] = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/health",
    "/api/v1/health/ready",
    "/api/v1/health/live",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
}

# Path prefixes that don't require authentication
PUBLIC_PATH_PREFIXES: tuple[str, ...] = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/static",
)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to authenticate incoming requests via JWT tokens.

    Extracts the JWT token from the Authorization header, validates it,
    and attaches the authenticated user to the request state.
    """

    def __init__(
        self,
        app: ASGIApp,
        public_paths: set[str] | None = None,
        public_prefixes: tuple[str, ...] | None = None,
    ) -> None:
        super().__init__(app)
        self.public_paths = public_paths or PUBLIC_PATHS
        self.public_prefixes = public_prefixes or PUBLIC_PATH_PREFIXES
        self.token_manager = get_token_manager()

    def _is_public_path(self, path: str) -> bool:
        """Check if a path is public (doesn't require auth)."""
        if path in self.public_paths:
            return True
        return any(path.startswith(prefix) for prefix in self.public_prefixes)

    def _extract_token(self, request: Request) -> str | None:
        """Extract JWT token from the Authorization header.

        Args:
            request: The incoming request.

        Returns:
            The token string, or None if not found.
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        return parts[1]

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> JSONResponse:
        """Process the request through authentication.

        Args:
            request: The incoming request.
            call_next: The next handler in the middleware chain.

        Returns:
            The response from the next handler.
        """
        # Skip authentication for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)

        # Extract and validate token
        token = self._extract_token(request)
        if not token:
            logger.warning(
                "Missing authentication token",
                path=request.url.path,
                method=request.method,
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication required"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = self.token_manager.verify_access_token(token)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Token validation error", error=str(exc))
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create authenticated user and attach to request state
        user_id = payload.get("sub", "")
        roles = [UserRole(r) for r in payload.get("roles", ["user"])]
        email = payload.get("email")
        metadata = {
            k: v
            for k, v in payload.items()
            if k not in ("sub", "iat", "exp", "type", "roles", "email")
        }

        user = AuthenticatedUser(
            user_id=user_id,
            roles=roles,
            email=email,
            metadata=metadata,
        )
        request.state.user = user

        logger.debug(
            "Request authenticated",
            user_id=user_id,
            path=request.url.path,
            method=request.method,
        )

        return await call_next(request)


# ── Dependency Functions ────────────────────────────────────────────────────


def get_current_user(request: Request) -> AuthenticatedUser:
    """Get the authenticated user from the request.

    Args:
        request: The incoming request.

    Returns:
        The authenticated user.

    Raises:
        HTTPException: If no user is authenticated.
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_auth(request: Request) -> AuthenticatedUser:
    """Require authentication for a route.

    Args:
        request: The incoming request.

    Returns:
        The authenticated user.

    Raises:
        HTTPException: If not authenticated.
    """
    return get_current_user(request)


def require_roles(roles: list[UserRole]) -> Callable:
    """Create a dependency that requires specific roles.

    Args:
        roles: List of required roles.

    Returns:
        A dependency function that checks roles.
    """

    def role_checker(request: Request) -> AuthenticatedUser:
        user = get_current_user(request)
        if not user.has_any_role(roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_checker
