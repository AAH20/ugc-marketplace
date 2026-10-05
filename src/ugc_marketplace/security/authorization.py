"""Authorization checks for UGC Marketplace route handlers."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any

from fastapi import HTTPException, Request, status

from ugc_marketplace.security.auth import AuthenticatedUser, UserRole, get_current_user


class Permission(str, Enum):
    """Permissions for fine-grained access control."""

    # Content permissions
    CONTENT_READ = "content:read"
    CONTENT_CREATE = "content:create"
    CONTENT_UPDATE = "content:update"
    CONTENT_DELETE = "content:delete"
    CONTENT_MODERATE = "content:moderate"

    # Creator permissions
    CREATOR_READ = "creator:read"
    CREATOR_CREATE = "creator:create"
    CREATOR_UPDATE = "creator:update"
    CREATOR_DELETE = "creator:delete"

    # Listing permissions
    LISTING_READ = "listing:read"
    LISTING_CREATE = "listing:create"
    LISTING_UPDATE = "listing:update"
    LISTING_DELETE = "listing:delete"

    # Transaction permissions
    TRANSACTION_READ = "transaction:read"
    TRANSACTION_CREATE = "transaction:create"
    TRANSACTION_UPDATE = "transaction:update"
    TRANSACTION_DELETE = "transaction:delete"
    TRANSACTION_REFUND = "transaction:refund"

    # Payment permissions
    PAYMENT_READ = "payment:read"
    PAYMENT_CREATE = "payment:create"
    PAYMENT_UPDATE = "payment:update"
    PAYMENT_DELETE = "payment:delete"

    # Review permissions
    REVIEW_READ = "review:read"
    REVIEW_CREATE = "review:create"
    REVIEW_UPDATE = "review:update"
    REVIEW_DELETE = "review:delete"

    # Category permissions
    CATEGORY_READ = "category:read"
    CATEGORY_CREATE = "category:create"
    CATEGORY_UPDATE = "category:update"
    CATEGORY_DELETE = "category:delete"

    # Tag permissions
    TAG_READ = "tag:read"
    TAG_CREATE = "tag:create"
    TAG_UPDATE = "tag:update"
    TAG_DELETE = "tag:delete"

    # Notification permissions
    NOTIFICATION_READ = "notification:read"
    NOTIFICATION_CREATE = "notification:create"
    NOTIFICATION_UPDATE = "notification:update"
    NOTIFICATION_DELETE = "notification:delete"

    # Analytics permissions
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"

    # Moderation permissions
    MODERATION_READ = "moderation:read"
    MODERATION_ACTION = "moderation:action"
    MODERATION_APPEAL = "moderation:appeal"

    # Fraud detection permissions
    FRAUD_READ = "fraud:read"
    FRAUD_ACTION = "fraud:action"

    # Quality scoring permissions
    QUALITY_READ = "quality:read"
    QUALITY_SCORE = "quality:score"

    # Rights management permissions
    RIGHTS_READ = "rights:read"
    RIGHTS_MANAGE = "rights:manage"

    # Licensing permissions
    LICENSING_READ = "licensing:read"
    LICENSING_MANAGE = "licensing:manage"

    # Curation permissions
    CURATION_READ = "curation:read"
    CURATION_MANAGE = "curation:manage"

    # Monetization permissions
    MONETIZATION_READ = "monetization:read"
    MONETIZATION_MANAGE = "monetization:manage"

    # Admin permissions
    ADMIN_FULL = "admin:full"


# ── Role-Permission Mapping ─────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.ADMIN: {
        Permission.ADMIN_FULL,
        Permission.CONTENT_READ,
        Permission.CONTENT_CREATE,
        Permission.CONTENT_UPDATE,
        Permission.CONTENT_DELETE,
        Permission.CONTENT_MODERATE,
        Permission.CREATOR_READ,
        Permission.CREATOR_CREATE,
        Permission.CREATOR_UPDATE,
        Permission.CREATOR_DELETE,
        Permission.LISTING_READ,
        Permission.LISTING_CREATE,
        Permission.LISTING_UPDATE,
        Permission.LISTING_DELETE,
        Permission.TRANSACTION_READ,
        Permission.TRANSACTION_CREATE,
        Permission.TRANSACTION_UPDATE,
        Permission.TRANSACTION_DELETE,
        Permission.TRANSACTION_REFUND,
        Permission.PAYMENT_READ,
        Permission.PAYMENT_CREATE,
        Permission.PAYMENT_UPDATE,
        Permission.PAYMENT_DELETE,
        Permission.REVIEW_READ,
        Permission.REVIEW_CREATE,
        Permission.REVIEW_UPDATE,
        Permission.REVIEW_DELETE,
        Permission.CATEGORY_READ,
        Permission.CATEGORY_CREATE,
        Permission.CATEGORY_UPDATE,
        Permission.CATEGORY_DELETE,
        Permission.TAG_READ,
        Permission.TAG_CREATE,
        Permission.TAG_UPDATE,
        Permission.TAG_DELETE,
        Permission.NOTIFICATION_READ,
        Permission.NOTIFICATION_CREATE,
        Permission.NOTIFICATION_UPDATE,
        Permission.NOTIFICATION_DELETE,
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_EXPORT,
        Permission.MODERATION_READ,
        Permission.MODERATION_ACTION,
        Permission.MODERATION_APPEAL,
        Permission.FRAUD_READ,
        Permission.FRAUD_ACTION,
        Permission.QUALITY_READ,
        Permission.QUALITY_SCORE,
        Permission.RIGHTS_READ,
        Permission.RIGHTS_MANAGE,
        Permission.LICENSING_READ,
        Permission.LICENSING_MANAGE,
        Permission.CURATION_READ,
        Permission.CURATION_MANAGE,
        Permission.MONETIZATION_READ,
        Permission.MONETIZATION_MANAGE,
    },
    UserRole.MODERATOR: {
        Permission.CONTENT_READ,
        Permission.CONTENT_UPDATE,
        Permission.CONTENT_MODERATE,
        Permission.CREATOR_READ,
        Permission.CREATOR_UPDATE,
        Permission.LISTING_READ,
        Permission.LISTING_UPDATE,
        Permission.TRANSACTION_READ,
        Permission.PAYMENT_READ,
        Permission.REVIEW_READ,
        Permission.REVIEW_UPDATE,
        Permission.REVIEW_DELETE,
        Permission.CATEGORY_READ,
        Permission.TAG_READ,
        Permission.NOTIFICATION_READ,
        Permission.NOTIFICATION_CREATE,
        Permission.ANALYTICS_READ,
        Permission.MODERATION_READ,
        Permission.MODERATION_ACTION,
        Permission.MODERATION_APPEAL,
        Permission.FRAUD_READ,
        Permission.FRAUD_ACTION,
        Permission.QUALITY_READ,
        Permission.QUALITY_SCORE,
        Permission.RIGHTS_READ,
        Permission.LICENSING_READ,
        Permission.CURATION_READ,
        Permission.CURATION_MANAGE,
        Permission.MONETIZATION_READ,
    },
    UserRole.CREATOR: {
        Permission.CONTENT_READ,
        Permission.CONTENT_CREATE,
        Permission.CONTENT_UPDATE,
        Permission.CREATOR_READ,
        Permission.CREATOR_UPDATE,
        Permission.LISTING_READ,
        Permission.LISTING_CREATE,
        Permission.LISTING_UPDATE,
        Permission.TRANSACTION_READ,
        Permission.TRANSACTION_CREATE,
        Permission.PAYMENT_READ,
        Permission.REVIEW_READ,
        Permission.REVIEW_CREATE,
        Permission.REVIEW_UPDATE,
        Permission.CATEGORY_READ,
        Permission.TAG_READ,
        Permission.NOTIFICATION_READ,
        Permission.NOTIFICATION_UPDATE,
        Permission.ANALYTICS_READ,
        Permission.QUALITY_READ,
        Permission.RIGHTS_READ,
        Permission.LICENSING_READ,
        Permission.CURATION_READ,
        Permission.MONETIZATION_READ,
    },
    UserRole.USER: {
        Permission.CONTENT_READ,
        Permission.CREATOR_READ,
        Permission.LISTING_READ,
        Permission.TRANSACTION_READ,
        Permission.TRANSACTION_CREATE,
        Permission.PAYMENT_READ,
        Permission.PAYMENT_CREATE,
        Permission.REVIEW_READ,
        Permission.REVIEW_CREATE,
        Permission.CATEGORY_READ,
        Permission.TAG_READ,
        Permission.NOTIFICATION_READ,
        Permission.QUALITY_READ,
        Permission.RIGHTS_READ,
        Permission.LICENSING_READ,
        Permission.CURATION_READ,
    },
    UserRole.SERVICE: {
        Permission.CONTENT_READ,
        Permission.CONTENT_CREATE,
        Permission.CONTENT_UPDATE,
        Permission.CONTENT_DELETE,
        Permission.CREATOR_READ,
        Permission.CREATOR_CREATE,
        Permission.CREATOR_UPDATE,
        Permission.LISTING_READ,
        Permission.LISTING_CREATE,
        Permission.LISTING_UPDATE,
        Permission.LISTING_DELETE,
        Permission.TRANSACTION_READ,
        Permission.TRANSACTION_CREATE,
        Permission.TRANSACTION_UPDATE,
        Permission.TRANSACTION_DELETE,
        Permission.PAYMENT_READ,
        Permission.PAYMENT_CREATE,
        Permission.PAYMENT_UPDATE,
        Permission.PAYMENT_DELETE,
        Permission.REVIEW_READ,
        Permission.REVIEW_CREATE,
        Permission.REVIEW_UPDATE,
        Permission.REVIEW_DELETE,
        Permission.CATEGORY_READ,
        Permission.CATEGORY_CREATE,
        Permission.CATEGORY_UPDATE,
        Permission.CATEGORY_DELETE,
        Permission.TAG_READ,
        Permission.TAG_CREATE,
        Permission.TAG_UPDATE,
        Permission.TAG_DELETE,
        Permission.NOTIFICATION_READ,
        Permission.NOTIFICATION_CREATE,
        Permission.NOTIFICATION_UPDATE,
        Permission.NOTIFICATION_DELETE,
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_EXPORT,
        Permission.MODERATION_READ,
        Permission.MODERATION_ACTION,
        Permission.FRAUD_READ,
        Permission.FRAUD_ACTION,
        Permission.QUALITY_READ,
        Permission.QUALITY_SCORE,
        Permission.RIGHTS_READ,
        Permission.RIGHTS_MANAGE,
        Permission.LICENSING_READ,
        Permission.LICENSING_MANAGE,
        Permission.CURATION_READ,
        Permission.CURATION_MANAGE,
        Permission.MONETIZATION_READ,
        Permission.MONETIZATION_MANAGE,
    },
}


class AuthorizationChecker:
    """Check user permissions and ownership for authorization."""

    @staticmethod
    def get_user_permissions(user: AuthenticatedUser) -> set[Permission]:
        """Get all permissions for a user based on their roles.

        Args:
            user: The authenticated user.

        Returns:
            Set of permissions the user has.
        """
        permissions: set[Permission] = set()
        for role in user.roles:
            permissions.update(ROLE_PERMISSIONS.get(role, set()))
        return permissions

    @staticmethod
    def has_permission(user: AuthenticatedUser, permission: Permission) -> bool:
        """Check if a user has a specific permission.

        Args:
            user: The authenticated user.
            permission: The permission to check.

        Returns:
            True if the user has the permission.
        """
        user_permissions = AuthorizationChecker.get_user_permissions(user)
        return permission in user_permissions or Permission.ADMIN_FULL in user_permissions

    @staticmethod
    def has_any_permission(user: AuthenticatedUser, permissions: list[Permission]) -> bool:
        """Check if a user has any of the specified permissions.

        Args:
            user: The authenticated user.
            permissions: List of permissions to check.

        Returns:
            True if the user has any of the permissions.
        """
        user_permissions = AuthorizationChecker.get_user_permissions(user)
        if Permission.ADMIN_FULL in user_permissions:
            return True
        return any(p in user_permissions for p in permissions)

    @staticmethod
    def has_all_permissions(user: AuthenticatedUser, permissions: list[Permission]) -> bool:
        """Check if a user has all of the specified permissions.

        Args:
            user: The authenticated user.
            permissions: List of permissions to check.

        Returns:
            True if the user has all of the permissions.
        """
        user_permissions = AuthorizationChecker.get_user_permissions(user)
        if Permission.ADMIN_FULL in user_permissions:
            return True
        return all(p in user_permissions for p in permissions)

    @staticmethod
    def is_owner(user: AuthenticatedUser, resource_owner_id: str) -> bool:
        """Check if a user owns a resource.

        Args:
            user: The authenticated user.
            resource_owner_id: The ID of the resource owner.

        Returns:
            True if the user is the owner.
        """
        return user.user_id == resource_owner_id

    @staticmethod
    def is_owner_or_has_permission(
        user: AuthenticatedUser,
        resource_owner_id: str,
        permission: Permission,
    ) -> bool:
        """Check if a user is the owner or has a specific permission.

        Args:
            user: The authenticated user.
            resource_owner_id: The ID of the resource owner.
            permission: The permission to check.

        Returns:
            True if the user is the owner or has the permission.
        """
        return AuthorizationChecker.is_owner(
            user, resource_owner_id
        ) or AuthorizationChecker.has_permission(user, permission)


# ── Dependency Functions ────────────────────────────────────────────────────


def require_permission(permission: Permission) -> Callable:
    """Create a dependency that requires a specific permission.

    Args:
        permission: The required permission.

    Returns:
        A dependency function that checks the permission.
    """

    def permission_checker(request: Request) -> AuthenticatedUser:
        user = get_current_user(request)
        if not AuthorizationChecker.has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required",
            )
        return user

    return permission_checker


def require_any_permission(permissions: list[Permission]) -> Callable:
    """Create a dependency that requires any of the specified permissions.

    Args:
        permissions: List of permissions, any one of which is sufficient.

    Returns:
        A dependency function that checks the permissions.
    """

    def permission_checker(request: Request) -> AuthenticatedUser:
        user = get_current_user(request)
        if not AuthorizationChecker.has_any_permission(user, permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: insufficient permissions",
            )
        return user

    return permission_checker


def require_ownership(
    resource_owner_id: str,
    permission: Permission | None = None,
) -> Callable:
    """Create a dependency that requires ownership of a resource.

    Args:
        resource_owner_id: The ID of the resource owner.
        permission: Optional permission that can override ownership requirement.

    Returns:
        A dependency function that checks ownership.
    """

    def ownership_checker(request: Request) -> AuthenticatedUser:
        user = get_current_user(request)
        if AuthorizationChecker.is_owner(user, resource_owner_id):
            return user
        if permission and AuthorizationChecker.has_permission(user, permission):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not own this resource",
        )

    return ownership_checker


def require_ownership_or_permission(
    get_owner_id: Callable,
    permission: Permission,
) -> Callable:
    """Create a dependency that requires ownership or a specific permission.

    Args:
        get_owner_id: A callable that extracts the owner ID from the request.
        permission: The permission that can override ownership requirement.

    Returns:
        A dependency function that checks ownership or permission.
    """

    def ownership_checker(request: Request) -> AuthenticatedUser:
        user = get_current_user(request)
        owner_id = get_owner_id(request)
        if AuthorizationChecker.is_owner_or_has_permission(user, owner_id, permission):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not own this resource",
        )

    return ownership_checker
