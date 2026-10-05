"""Tests for GTM Launch Platform models."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from ugc_marketplace.gtm.models import (
    CampaignAnalytics,
    CampaignStatus,
    ChannelPerformance,
    CompetitorAnalysis,
    ContentType,
    LaunchCampaign,
    LaunchCampaignCreate,
    LaunchChannel,
    LaunchScore,
)


class TestLaunchCampaignCreate:
    """Tests for LaunchCampaignCreate model."""

    def test_create_minimal_campaign(self) -> None:
        """Test creating a campaign with minimal required fields."""
        campaign = LaunchCampaignCreate(
            name="Test Launch",
            channels=[LaunchChannel.TWITTER],
        )
        assert campaign.name == "Test Launch"
        assert campaign.channels == [LaunchChannel.TWITTER]
        assert campaign.content_type == ContentType.TEXT
        assert campaign.budget == 0.0

    def test_create_full_campaign(self) -> None:
        """Test creating a campaign with all fields."""
        scheduled = datetime.utcnow() + timedelta(days=7)
        campaign = LaunchCampaignCreate(
            name="Full Launch",
            description="A comprehensive launch",
            channels=[LaunchChannel.TWITTER, LaunchChannel.PRODUCT_HUNT],
            content_type=ContentType.VIDEO,
            target_audience="Developers",
            budget=1000.0,
            scheduled_at=scheduled,
            metadata={"has_demo_video": True},
        )
        assert campaign.name == "Full Launch"
        assert campaign.channels == [LaunchChannel.TWITTER, LaunchChannel.PRODUCT_HUNT]
        assert campaign.content_type == ContentType.VIDEO
        assert campaign.budget == 1000.0
        assert campaign.scheduled_at == scheduled

    def test_empty_name_rejected(self) -> None:
        """Test that empty name is rejected."""
        with pytest.raises(ValueError, match="at least 1 character"):
            LaunchCampaignCreate(name="", channels=[LaunchChannel.TWITTER])

    def test_empty_channels_rejected(self) -> None:
        """Test that empty channels list is rejected."""
        with pytest.raises(ValueError, match="at least 1 item"):
            LaunchCampaignCreate(name="Test", channels=[])


class TestLaunchCampaign:
    """Tests for LaunchCampaign model."""

    def test_campaign_defaults(self) -> None:
        """Test campaign default values."""
        campaign = LaunchCampaign(
            name="Test",
            channels=[LaunchChannel.TWITTER],
            content_type=ContentType.TEXT,
        )
        assert campaign.status == CampaignStatus.DRAFT
        assert campaign.budget == 0.0
        assert campaign.id is not None
        assert campaign.created_at is not None

    def test_campaign_with_all_fields(self) -> None:
        """Test campaign with all fields populated."""
        campaign = LaunchCampaign(
            name="Full",
            description="Description",
            channels=[LaunchChannel.TWITTER, LaunchChannel.PRODUCT_HUNT],
            content_type=ContentType.VIDEO,
            target_audience="Devs",
            budget=500.0,
            status=CampaignStatus.SCHEDULED,
            metadata={"key": "value"},
        )
        assert campaign.name == "Full"
        assert campaign.status == CampaignStatus.SCHEDULED
        assert campaign.metadata == {"key": "value"}


class TestLaunchScore:
    """Tests for LaunchScore model."""

    def test_perfect_score(self) -> None:
        """Test a perfect launch score."""
        score = LaunchScore(
            overall=1.0,
            content_quality=1.0,
            channel_fit=1.0,
            timing=1.0,
            audience_match=1.0,
        )
        assert score.overall == 1.0
        assert score.recommendations == []

    def test_score_with_recommendations(self) -> None:
        """Test score with recommendations."""
        score = LaunchScore(
            overall=0.5,
            content_quality=0.4,
            channel_fit=0.5,
            timing=0.6,
            audience_match=0.5,
            recommendations=["Add demo video"],
        )
        assert len(score.recommendations) == 1
        assert "Add demo video" in score.recommendations

    def test_score_bounds(self) -> None:
        """Test that scores must be between 0 and 1."""
        with pytest.raises(ValueError):
            LaunchScore(
                overall=1.5,
                content_quality=0.5,
                channel_fit=0.5,
                timing=0.5,
                audience_match=0.5,
            )


class TestChannelPerformance:
    """Tests for ChannelPerformance model."""

    def test_channel_performance_defaults(self) -> None:
        """Test default channel performance."""
        perf = ChannelPerformance(channel=LaunchChannel.TWITTER)
        assert perf.impressions == 0
        assert perf.clicks == 0
        assert perf.roas == 0.0

    def test_channel_performance_with_data(self) -> None:
        """Test channel performance with data."""
        perf = ChannelPerformance(
            channel=LaunchChannel.TWITTER,
            impressions=10000,
            clicks=500,
            conversions=50,
            spend=100.0,
            revenue=300.0,
            engagement_rate=0.05,
            ctr=0.05,
            roas=3.0,
        )
        assert perf.roas == 3.0
        assert perf.ctr == 0.05


class TestCampaignAnalytics:
    """Tests for CampaignAnalytics model."""

    def test_analytics_with_channels(self) -> None:
        """Test analytics with channel performance."""
        analytics = CampaignAnalytics(
            campaign_id=uuid.uuid4(),
            total_impressions=50000,
            total_clicks=2500,
            total_conversions=250,
            total_spend=500.0,
            total_revenue=1500.0,
            overall_roas=3.0,
            channel_performance=[
                ChannelPerformance(
                    channel=LaunchChannel.TWITTER,
                    impressions=30000,
                    clicks=1500,
                    conversions=150,
                    spend=300.0,
                    revenue=900.0,
                    roas=3.0,
                ),
                ChannelPerformance(
                    channel=LaunchChannel.PRODUCT_HUNT,
                    impressions=20000,
                    clicks=1000,
                    conversions=100,
                    spend=200.0,
                    revenue=600.0,
                    roas=3.0,
                ),
            ],
        )
        assert len(analytics.channel_performance) == 2
        assert analytics.overall_roas == 3.0


class TestCompetitorAnalysis:
    """Tests for CompetitorAnalysis model."""

    def test_competitor_analysis(self) -> None:
        """Test competitor analysis model."""
        analysis = CompetitorAnalysis(
            competitor_name="Unfair.so",
            channels=[LaunchChannel.TWITTER, LaunchChannel.PRODUCT_HUNT],
            estimated_reach=500000,
            content_strategy="Creator marketing",
            strengths=["Large reach"],
            weaknesses=["High pricing"],
            opportunities=["Untapped channels"],
        )
        assert analysis.competitor_name == "Unfair.so"
        assert len(analysis.channels) == 2
