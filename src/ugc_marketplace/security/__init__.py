"""Security package for UGC Marketplace."""
from __future__ import annotations

from ugc_marketplace.security.auth import (
    AuthMiddleware,
    get_current_user,
    require_auth,
    require_roles,
)
from ugc_marketplace.security.authorization import (
    AuthorizationChecker,
    require_ownership,
    require_permission,
)
from ugc_marketplace.security.rate_limit import (
    RateLimiter,
    rate_limit,
)

__all__ = [
    "AuthMiddleware",
    "get_current_user",
    "require_auth",
    "require_roles",
    "AuthorizationChecker",
    "require_ownership",
    "require_permission",
    "RateLimiter",
    "rate_limit",
]
