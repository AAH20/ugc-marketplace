"""Pydantic schemas for GTM campaigns."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    channels: list[str] = Field(default_factory=list)
    content_type: str = Field(..., min_length=1, max_length=100)
    target_audience: str = Field(..., min_length=1, max_length=255)
    budget: float = Field(default=0.0, ge=0)
    status: str = Field(default="draft")
    scheduled_at: datetime | None = None
    extra_metadata: dict | None = None


class CampaignUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    channels: list[str] | None = None
    content_type: str | None = Field(None, min_length=1, max_length=100)
    target_audience: str | None = Field(None, min_length=1, max_length=255)
    budget: float | None = Field(None, ge=0)
    status: str | None = None
    scheduled_at: datetime | None = None
    extra_metadata: dict | None = None


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    description: str | None
    channels: list[str]
    content_type: str
    target_audience: str
    budget: float
    status: str
    scheduled_at: datetime | None
    extra_metadata: dict | None = None
    created_at: datetime
    updated_at: datetime
