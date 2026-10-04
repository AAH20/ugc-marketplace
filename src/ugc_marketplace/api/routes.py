"""API route registration for UGC Marketplace."""

from fastapi import APIRouter

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

api_router = APIRouter()

api_router.include_router(creators, prefix="/creators", tags=["creators"])
api_router.include_router(content, prefix="/content", tags=["content"])
api_router.include_router(listings, prefix="/listings", tags=["listings"])
api_router.include_router(transactions, prefix="/transactions", tags=["transactions"])
api_router.include_router(notifications, prefix="/notifications", tags=["notifications"])
api_router.include_router(analytics, prefix="/analytics", tags=["analytics"])
api_router.include_router(payments, prefix="/payments", tags=["payments"])
api_router.include_router(reviews, prefix="/reviews", tags=["reviews"])
api_router.include_router(categories, prefix="/categories", tags=["categories"])
api_router.include_router(tags, prefix="/tags", tags=["tags"])
