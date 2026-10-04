"""
Reviews API endpoints for UGC Marketplace.

Provides:
  GET  /reviews  — list reviews with pagination and rating filter
  POST /reviews  — create a new review with validation
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from ugc_marketplace.security.auth import get_current_user, require_auth
from ugc_marketplace.security.authorization import Permission, require_permission

router = APIRouter(prefix="/reviews", tags=["reviews"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ReviewCreate(BaseModel):
    """Payload for creating a new review."""

    product_id: int = Field(..., gt=0, description="ID of the product being reviewed")
    user_id: int = Field(..., gt=0, description="ID of the user writing the review")
    rating: int = Field(..., ge=1, le=5, description="Star rating from 1 to 5")
    title: str = Field(..., min_length=1, max_length=120, description="Short review headline")
    body: str = Field(..., min_length=1, max_length=2000, description="Full review text")


class ReviewResponse(BaseModel):
    """Review representation returned by the API."""

    id: int
    product_id: int
    user_id: int
    rating: int
    title: str
    body: str
    helpful_count: int
    verified_purchase: bool
    created_at: str
    updated_at: str


class ReviewListResponse(BaseModel):
    """Paginated list of reviews."""

    data: list[ReviewResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ---------------------------------------------------------------------------
# Mock data store
# ---------------------------------------------------------------------------

MOCK_REVIEWS: list[dict] = [
    {
        "id": 1,
        "product_id": 101,
        "user_id": 501,
        "rating": 5,
        "title": "Exceeded expectations",
        "body": "The quality is outstanding and it arrived faster than expected. Highly recommend!",
        "helpful_count": 12,
        "verified_purchase": True,
        "created_at": "2026-09-15T10:30:00Z",
        "updated_at": "2026-09-15T10:30:00Z",
    },
    {
        "id": 2,
        "product_id": 101,
        "user_id": 502,
        "rating": 4,
        "title": "Good but could be better",
        "body": "Solid product overall. Packaging was a bit damaged but the item itself works great.",
        "helpful_count": 5,
        "verified_purchase": True,
        "created_at": "2026-09-18T14:22:00Z",
        "updated_at": "2026-09-18T14:22:00Z",
    },
    {
        "id": 3,
        "product_id": 102,
        "user_id": 503,
        "rating": 3,
        "title": "Average experience",
        "body": "It does what it says but nothing extraordinary. Price feels slightly high for what you get.",
        "helpful_count": 2,
        "verified_purchase": False,
        "created_at": "2026-09-20T09:15:00Z",
        "updated_at": "2026-09-20T09:15:00Z",
    },
    {
        "id": 4,
        "product_id": 103,
        "user_id": 504,
        "rating": 1,
        "title": "Disappointed",
        "body": "Stopped working after two days. Customer support has been unresponsive.",
        "helpful_count": 8,
        "verified_purchase": True,
        "created_at": "2026-09-22T16:45:00Z",
        "updated_at": "2026-09-22T16:45:00Z",
    },
    {
        "id": 5,
        "product_id": 102,
        "user_id": 505,
        "rating": 5,
        "title": "Perfect gift",
        "body": "Bought this as a birthday gift and the recipient loved it. Great value for money.",
        "helpful_count": 3,
        "verified_purchase": True,
        "created_at": "2026-09-25T11:00:00Z",
        "updated_at": "2026-09-25T11:00:00Z",
    },
    {
        "id": 6,
        "product_id": 104,
        "user_id": 506,
        "rating": 2,
        "title": "Not as described",
        "body": "Color was different from the photos. Material feels cheap.",
        "helpful_count": 15,
        "verified_purchase": True,
        "created_at": "2026-09-28T08:30:00Z",
        "updated_at": "2026-09-28T08:30:00Z",
    },
    {
        "id": 7,
        "product_id": 101,
        "user_id": 507,
        "rating": 4,
        "title": "Would buy again",
        "body": "Second time purchasing. Consistent quality and reliable shipping.",
        "helpful_count": 6,
        "verified_purchase": True,
        "created_at": "2026-10-01T13:10:00Z",
        "updated_at": "2026-10-01T13:10:00Z",
    },
    {
        "id": 8,
        "product_id": 105,
        "user_id": 508,
        "rating": 5,
        "title": "Best purchase this year",
        "body": "Absolutely love it. The attention to detail is remarkable.",
        "helpful_count": 20,
        "verified_purchase": True,
        "created_at": "2026-10-02T17:45:00Z",
        "updated_at": "2026-10-02T17:45:00Z",
    },
]

_next_id = max(r["id"] for r in MOCK_REVIEWS) + 1


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=ReviewListResponse)
async def list_reviews(
    request: Request,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    rating: int | None = Query(None, ge=1, le=5, description="Filter by star rating"),
    user=Depends(require_permission(Permission.REVIEW_READ)),
) -> dict:
    """
    List reviews with optional rating filter and pagination.
    """
    filtered = MOCK_REVIEWS
    if rating is not None:
        filtered = [r for r in filtered if r["rating"] == rating]

    total = len(filtered)
    pages = (total + page_size - 1) // page_size if total else 1

    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]

    return {
        "data": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    request: Request,
    payload: ReviewCreate,
    user=Depends(require_permission(Permission.REVIEW_CREATE)),
) -> dict:
    """
    Create a new review. Validates rating (1-5), non-empty title/body,
    and positive product_id / user_id.
    """
    global _next_id

    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    review = {
        "id": _next_id,
        "product_id": payload.product_id,
        "user_id": payload.user_id,
        "rating": payload.rating,
        "title": payload.title,
        "body": payload.body,
        "helpful_count": 0,
        "verified_purchase": True,
        "created_at": now,
        "updated_at": now,
    }

    MOCK_REVIEWS.append(review)
    _next_id += 1

    return review


class ReviewUpdate(BaseModel):
    """Payload for updating an existing review (all fields optional)."""

    rating: int | None = Field(None, ge=1, le=5, description="Star rating from 1 to 5")
    title: str | None = Field(
        None, min_length=1, max_length=120, description="Short review headline"
    )
    body: str | None = Field(None, min_length=1, max_length=2000, description="Full review text")


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    request: Request,
    review_id: int,
    user=Depends(require_permission(Permission.REVIEW_READ)),
) -> dict:
    """Retrieve a single review by its unique identifier."""
    for review in MOCK_REVIEWS:
        if review["id"] == review_id:
            return review

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Review with id {review_id} not found",
    )


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    request: Request,
    review_id: int,
    payload: ReviewUpdate,
    user=Depends(require_permission(Permission.REVIEW_UPDATE)),
) -> dict:
    """Update an existing review by its unique identifier."""
    for review in MOCK_REVIEWS:
        if review["id"] == review_id:
            update_data = payload.model_dump(exclude_unset=True)
            review.update(update_data)
            review["updated_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            return review

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Review with id {review_id} not found",
    )


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    request: Request,
    review_id: int,
    user=Depends(require_permission(Permission.REVIEW_DELETE)),
) -> None:
    """Delete a review by its unique identifier."""
    for i, review in enumerate(MOCK_REVIEWS):
        if review["id"] == review_id:
            MOCK_REVIEWS.pop(i)
            return None

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Review with id {review_id} not found",
    )
