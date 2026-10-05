"""GTM Launch Platform data models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LaunchChannel(str, Enum):
    """Supported launch channels."""

    PRODUCT_HUNT = "product_hunt"
    HACKER_NEWS = "hacker_news"
    REDDIT = "reddit"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"
    EMAIL = "email"
    DISCORD = "discord"
    BLOG = "blog"
    YOUTUBE = "youtube"


class CampaignStatus(str, Enum):
    """Campaign lifecycle status."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ContentType(str, Enum):
    """Content types for GTM campaigns."""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL = "carousel"
    STORY = "story"


class LaunchCampaignCreate(BaseModel):
    """Request model for creating a launch campaign."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")
    channels: list[LaunchChannel] = Field(..., min_length=1)
    content_type: ContentType = ContentType.TEXT
    target_audience: str = Field(default="")
    budget: float = Field(default=0.0, ge=0)
    scheduled_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LaunchCampaign(BaseModel):
    """Launch campaign model."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    description: str = ""
    channels: list[LaunchChannel]
    content_type: ContentType
    target_audience: str = ""
    budget: float = 0.0
    status: CampaignStatus = CampaignStatus.DRAFT
    scheduled_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChannelPerformance(BaseModel):
    """Performance metrics for a single channel."""

    channel: LaunchChannel
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    revenue: float = 0.0
    engagement_rate: float = 0.0
    ctr: float = 0.0
    roas: float = 0.0


class CampaignAnalytics(BaseModel):
    """Aggregated campaign analytics."""

    campaign_id: uuid.UUID
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    total_spend: float = 0.0
    total_revenue: float = 0.0
    overall_roas: float = 0.0
    channel_performance: list[ChannelPerformance] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)


class LaunchScore(BaseModel):
    """Launch readiness score."""

    overall: float = Field(..., ge=0.0, le=1.0)
    content_quality: float = Field(..., ge=0.0, le=1.0)
    channel_fit: float = Field(..., ge=0.0, le=1.0)
    timing: float = Field(..., ge=0.0, le=1.0)
    audience_match: float = Field(..., ge=0.0, le=1.0)
    recommendations: list[str] = Field(default_factory=list)


class CompetitorAnalysis(BaseModel):
    """Competitor analysis result."""

    competitor_name: str
    channels: list[LaunchChannel] = Field(default_factory=list)
    estimated_reach: int = 0
    content_strategy: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
