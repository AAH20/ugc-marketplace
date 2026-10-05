"""API routers for ugc-marketplace."""

from ugc_marketplace.api.analytics import router as analytics
from ugc_marketplace.api.categories import router as categories
from ugc_marketplace.api.content import router as content
from ugc_marketplace.api.creators import router as creators
from ugc_marketplace.api.listings import router as listings
from ugc_marketplace.api.notifications import router as notifications
from ugc_marketplace.api.payments import router as payments
from ugc_marketplace.api.reviews import router as reviews
from ugc_marketplace.api.tags import router as tags
from ugc_marketplace.api.transactions import router as transactions

__all__ = [
    "analytics",
    "categories",
    "content",
    "creators",
    "listings",
    "notifications",
    "payments",
    "reviews",
    "tags",
    "transactions",
]
