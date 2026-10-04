"""Authentication API endpoints for UGC Marketplace."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from ugc_marketplace.security.auth import (
    AuthenticatedUser,
    TokenManager,
    UserRole,
    get_current_user,
    get_token_manager,
)

router = APIRouter()


# ── Pydantic Models ──────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """Request model for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")


class RegisterRequest(BaseModel):
    """Request model for user registration."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    full_name: str | None = Field(default=None, description="Full name")


class TokenResponse(BaseModel):
    """Response model for token endpoints."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class RefreshRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str = Field(..., description="JWT refresh token")


class UserResponse(BaseModel):
    """Response model for user information."""

    user_id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    username: str = Field(..., description="Username")
    roles: list[str] = Field(..., description="User roles")
    is_active: bool = Field(default=True, description="Whether the user is active")


class PasswordChangeRequest(BaseModel):
    """Request model for password change."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


# ── Mock User Store (replace with database in production) ────────────────────


class MockUserStore:
    """In-memory user store for demonstration. Replace with database in production."""

    def __init__(self) -> None:
        self._users: dict[str, dict[str, Any]] = {}
        self._email_index: dict[str, str] = {}
        self._init_default_users()

    def _hash_password(self, password: str, salt: str | None = None) -> tuple[str, str]:
        """Hash a password with a salt using PBKDF2.

        Args:
            password: The plain text password.
            salt: Optional salt. Generated if not provided.

        Returns:
            Tuple of (hashed_password, salt).
        """
        if salt is None:
            salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return hashed.hex(), salt

    def _verify_password(self, password: str, hashed: str, salt: str) -> bool:
        """Verify a password against its hash.

        Args:
            password: The plain text password.
            hashed: The stored hash.
            salt: The stored salt.

        Returns:
            True if the password matches.
        """
        computed, _ = self._hash_password(password, salt)
        return hmac.compare_digest(computed, hashed)

    def _init_default_users(self) -> None:
        """Initialize default users for testing."""
        # Admin user
        admin_id = "usr_admin_001"
        admin_hash, admin_salt = self._hash_password("AdminPass123!")
        self._users[admin_id] = {
            "user_id": admin_id,
            "email": "admin@ugc-marketplace.com",
            "username": "admin",
            "full_name": "System Administrator",
            "password_hash": admin_hash,
            "password_salt": admin_salt,
            "roles": [UserRole.ADMIN],
            "is_active": True,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._email_index["admin@ugc-marketplace.com"] = admin_id

        # Moderator user
        mod_id = "usr_mod_001"
        mod_hash, mod_salt = self._hash_password("ModPass123!")
        self._users[mod_id] = {
            "user_id": mod_id,
            "email": "moderator@ugc-marketplace.com",
            "username": "moderator",
            "full_name": "Content Moderator",
            "password_hash": mod_hash,
            "password_salt": mod_salt,
            "roles": [UserRole.MODERATOR],
            "is_active": True,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._email_index["moderator@ugc-marketplace.com"] = mod_id

        # Creator user
        creator_id = "usr_creator_001"
        creator_hash, creator_salt = self._hash_password("CreatorPass123!")
        self._users[creator_id] = {
            "user_id": creator_id,
            "email": "creator@ugc-marketplace.com",
            "username": "creator",
            "full_name": "Content Creator",
            "password_hash": creator_hash,
            "password_salt": creator_salt,
            "roles": [UserRole.CREATOR],
            "is_active": True,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._email_index["creator@ugc-marketplace.com"] = creator_id

        # Regular user
        user_id = "usr_user_001"
        user_hash, user_salt = self._hash_password("UserPass123!")
        self._users[user_id] = {
            "user_id": user_id,
            "email": "user@ugc-marketplace.com",
            "username": "user",
            "full_name": "Regular User",
            "password_hash": user_hash,
            "password_salt": user_salt,
            "roles": [UserRole.USER],
            "is_active": True,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._email_index["user@ugc-marketplace.com"] = user_id

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        """Get a user by email.

        Args:
            email: The user's email.

        Returns:
            The user dict, or None if not found.
        """
        user_id = self._email_index.get(email)
        if user_id is None:
            return None
        return self._users.get(user_id)

    def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Get a user by ID.

        Args:
            user_id: The user's ID.

        Returns:
            The user dict, or None if not found.
        """
        return self._users.get(user_id)

    def create_user(
        self,
        email: str,
        password: str,
        username: str,
        full_name: str | None = None,
        roles: list[UserRole] | None = None,
    ) -> dict[str, Any]:
        """Create a new user.

        Args:
            email: User email.
            password: Plain text password.
            username: Username.
            full_name: Optional full name.
            roles: Optional roles.

        Returns:
            The created user dict.

        Raises:
            HTTPException: If email or username already exists.
        """
        if email in self._email_index:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user_id = f"usr_{secrets.token_hex(8)}"
        password_hash, password_salt = self._hash_password(password)

        user = {
            "user_id": user_id,
            "email": email,
            "username": username,
            "full_name": full_name,
            "password_hash": password_hash,
            "password_salt": password_salt,
            "roles": roles or [UserRole.USER],
            "is_active": True,
            "created_at": datetime.now(UTC).isoformat(),
        }

        self._users[user_id] = user
        self._email_index[email] = user_id

        return user

    def verify_credentials(self, email: str, password: str) -> dict[str, Any] | None:
        """Verify user credentials.

        Args:
            email: User email.
            password: Plain text password.

        Returns:
            The user dict if credentials are valid, None otherwise.
        """
        user = self.get_by_email(email)
        if user is None:
            return None

        if not user.get("is_active", True):
            return None

        if self._verify_password(password, user["password_hash"], user["password_salt"]):
            return user

        return None


# Singleton user store
_user_store: MockUserStore | None = None


def get_user_store() -> MockUserStore:
    """Get the singleton MockUserStore instance."""
    global _user_store
    if _user_store is None:
        _user_store = MockUserStore()
    return _user_store


# ── Helper Functions ────────────────────────────────────────────────────────


def _user_to_response(user: dict[str, Any]) -> UserResponse:
    """Convert a user dict to a UserResponse.

    Args:
        user: The user dict.

    Returns:
        UserResponse model.
    """
    return UserResponse(
        user_id=user["user_id"],
        email=user["email"],
        username=user["username"],
        roles=[r.value if isinstance(r, UserRole) else r for r in user.get("roles", [])],
        is_active=user.get("is_active", True),
    )


def _create_tokens(user: dict[str, Any]) -> TokenResponse:
    """Create access and refresh tokens for a user.

    Args:
        user: The user dict.

    Returns:
        TokenResponse with tokens.
    """
    token_manager = get_token_manager()
    roles = user.get("roles", [UserRole.USER])
    if isinstance(roles[0], str):
        roles = [UserRole(r) for r in roles]

    access_token = token_manager.create_access_token(
        subject=user["user_id"],
        roles=roles,
        extra_claims={"email": user["email"], "username": user["username"]},
    )
    refresh_token = token_manager.create_refresh_token(subject=user["user_id"])

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=token_manager.access_token_expire_minutes * 60,
    )


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse, summary="User login")
async def login(request: LoginRequest) -> TokenResponse:
    """Authenticate a user and return JWT tokens.

    Args:
        request: Login request with email and password.

    Returns:
        TokenResponse with access and refresh tokens.

    Raises:
        HTTPException: If credentials are invalid.
    """
    store = get_user_store()
    user = store.verify_credentials(request.email, request.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _create_tokens(user)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="User registration")
async def register(request: RegisterRequest) -> UserResponse:
    """Register a new user.

    Args:
        request: Registration request with user details.

    Returns:
        UserResponse for the created user.

    Raises:
        HTTPException: If email already exists.
    """
    store = get_user_store()
    user = store.create_user(
        email=request.email,
        password=request.password,
        username=request.username,
        full_name=request.full_name,
    )
    return _user_to_response(user)


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh_token(request: RefreshRequest) -> TokenResponse:
    """Refresh an access token using a refresh token.

    Args:
        request: Refresh request with refresh token.

    Returns:
        TokenResponse with new tokens.

    Raises:
        HTTPException: If refresh token is invalid.
    """
    token_manager = get_token_manager()

    try:
        payload = token_manager.decode_token(request.refresh_token)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub", "")
    store = get_user_store()
    user = store.get_by_id(user_id)

    if user is None or not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return _create_tokens(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="User logout")
async def logout(request: Request) -> None:
    """Logout the current user.

    In a stateless JWT system, this is a no-op on the server side.
    The client should discard the tokens.

    Args:
        request: The incoming request.

    Returns:
        None (204 No Content).
    """
    # In a stateless JWT system, logout is handled client-side
    # For token revocation, implement a token blacklist (e.g., in Redis)
    return None


@router.get("/me", response_model=UserResponse, summary="Get current user")
async def get_current_user_info(request: Request) -> UserResponse:
    """Get information about the currently authenticated user.

    Args:
        request: The incoming request.

    Returns:
        UserResponse for the current user.
    """
    user = get_current_user(request)
    store = get_user_store()
    user_data = store.get_by_id(user.user_id)

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return _user_to_response(user_data)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT, summary="Change password")
async def change_password(request: Request, body: PasswordChangeRequest) -> None:
    """Change the current user's password.

    Args:
        request: The incoming request.
        body: Password change request.

    Returns:
        None (204 No Content).

    Raises:
        HTTPException: If current password is invalid.
    """
    user = get_current_user(request)
    store = get_user_store()
    user_data = store.get_by_id(user.user_id)

    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not store._verify_password(
        body.current_password,
        user_data["password_hash"],
        user_data["password_salt"],
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    new_hash, new_salt = store._hash_password(body.new_password)
    user_data["password_hash"] = new_hash
    user_data["password_salt"] = new_salt

    return None
