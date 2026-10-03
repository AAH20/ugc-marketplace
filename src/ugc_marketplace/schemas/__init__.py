"""Pydantic schemas for UGC Marketplace API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ─── Enums ────────────────────────────────────────────────────────────────────


class CreatorTier(str, Enum):
    """Creator tier levels."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class ContentStatus(str, Enum):
    """Content moderation status."""

    DRAFT = "draft"
    PENDING = "pending"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ListingStatus(str, Enum):
    """Listing availability status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SOLD = "sold"
    EXPIRED = "expired"


class TransactionStatus(str, Enum):
    """Transaction lifecycle status."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class ReviewRating(int, Enum):
    """Allowed review rating values."""

    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5


# ─── Creator Schemas ──────────────────────────────────────────────────────────


class CreatorBase(BaseModel):
    """Shared creator fields."""

    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    display_name: str | None = Field(None, max_length=100)
    bio: str | None = Field(None, max_length=500)
    tier: CreatorTier = CreatorTier.BRONZE
    is_verified: bool = False


class CreatorCreate(CreatorBase):
    """Schema for creating a new creator."""

    password: str = Field(..., min_length=8, max_length=128)


class CreatorUpdate(BaseModel):
    """Schema for updating an existing creator."""

    username: str | None = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr | None = None
    display_name: str | None = Field(None, max_length=100)
    bio: str | None = Field(None, max_length=500)
    tier: CreatorTier | None = None
    is_verified: bool | None = None


class CreatorResponse(CreatorBase):
    """Schema for creator API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


# ─── Content Schemas ──────────────────────────────────────────────────────────


class ContentBase(BaseModel):
    """Shared content fields."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=5000)
    content_type: str = Field(..., min_length=1, max_length=50)
    tags: list[str] = Field(default_factory=list)
    status: ContentStatus = ContentStatus.DRAFT
    is_premium: bool = False
    price: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)


class ContentCreate(ContentBase):
    """Schema for creating new content."""

    creator_id: int = Field(..., gt=0)


class ContentUpdate(BaseModel):
    """Schema for updating existing content."""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=5000)
    content_type: str | None = Field(None, min_length=1, max_length=50)
    tags: list[str] | None = None
    status: ContentStatus | None = None
    is_premium: bool | None = None
    price: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)


class ContentResponse(ContentBase):
    """Schema for content API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    creator_id: int
    created_at: datetime
    updated_at: datetime


# ─── Listing Schemas ──────────────────────────────────────────────────────────


class ListingBase(BaseModel):
    """Shared listing fields."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=5000)
    price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    status: ListingStatus = ListingStatus.ACTIVE
    quantity: int = Field(default=1, ge=1)


class ListingCreate(ListingBase):
    """Schema for creating a new listing."""

    creator_id: int = Field(..., gt=0)
    content_id: int | None = Field(None, gt=0)


class ListingUpdate(BaseModel):
    """Schema for updating an existing listing."""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=5000)
    price: Decimal | None = Field(None, gt=0, max_digits=10, decimal_places=2)
    currency: str | None = Field(None, pattern=r"^[A-Z]{3}$")
    status: ListingStatus | None = None
    quantity: int | None = Field(None, ge=1)


class ListingResponse(ListingBase):
    """Schema for listing API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    creator_id: int
    content_id: int | None = None
    created_at: datetime
    updated_at: datetime


# ─── Transaction Schemas ──────────────────────────────────────────────────────


class TransactionBase(BaseModel):
    """Shared transaction fields."""

    amount: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    status: TransactionStatus = TransactionStatus.PENDING


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""

    buyer_id: int = Field(..., gt=0)
    seller_id: int = Field(..., gt=0)
    listing_id: int = Field(..., gt=0)


class TransactionUpdate(BaseModel):
    """Schema for updating an existing transaction."""

    amount: Decimal | None = Field(None, gt=0, max_digits=10, decimal_places=2)
    currency: str | None = Field(None, pattern=r"^[A-Z]{3}$")
    status: TransactionStatus | None = None


class TransactionResponse(TransactionBase):
    """Schema for transaction API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    buyer_id: int
    seller_id: int
    listing_id: int
    created_at: datetime
    updated_at: datetime


# ─── Review Schemas ───────────────────────────────────────────────────────────


class ReviewBase(BaseModel):
    """Shared review fields."""

    rating: ReviewRating
    comment: str | None = Field(None, max_length=2000)


class ReviewCreate(ReviewBase):
    """Schema for creating a new review."""

    reviewer_id: int = Field(..., gt=0)
    creator_id: int = Field(..., gt=0)
    transaction_id: int | None = Field(None, gt=0)


class ReviewUpdate(BaseModel):
    """Schema for updating an existing review."""

    rating: ReviewRating | None = None
    comment: str | None = Field(None, max_length=2000)


class ReviewResponse(ReviewBase):
    """Schema for review API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    reviewer_id: int
    creator_id: int
    transaction_id: int | None = None
    created_at: datetime
    updated_at: datetime
