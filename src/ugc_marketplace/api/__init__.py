"""API route registration for ugc-marketplace."""

from fastapi import APIRouter

from ugc_marketplace.api.routes import (
    analytics,
    categories,
    content,
    creators,
    listings,
    notifications,
    payments,
    reviews,
    tags,
    transactions,
)

api_router = APIRouter()

api_router.include_router(creators, prefix="/creators", tags=["creators"])
api_router.include_router(content, prefix="/content", tags=["content"])
api_router.include_router(listings, prefix="/listings", tags=["listings"])
api_router.include_router(transactions, prefix="/transactions", tags=["transactions"])
api_router.include_router(notifications, prefix="/notifications", tags=["notifications"])
api_router.include_router(payments, prefix="/payments", tags=["payments"])
api_router.include_router(reviews, prefix="/reviews", tags=["reviews"])
api_router.include_router(categories, prefix="/categories", tags=["categories"])
api_router.include_router(tags, prefix="/tags", tags=["tags"])
api_router.include_router(analytics, prefix="/analytics", tags=["analytics"])
