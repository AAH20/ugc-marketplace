"""Tests for GTM Launch Platform agents."""

from __future__ import annotations

import uuid

import pytest

from ugc_marketplace.gtm.agents.channel_analyzer import ChannelAnalyzerAgent
from ugc_marketplace.gtm.agents.competitor_researcher import CompetitorResearcherAgent
from ugc_marketplace.gtm.agents.launch_strategist import LaunchStrategistAgent
from ugc_marketplace.gtm.models import (
    CampaignAnalytics,
    ChannelPerformance,
    CompetitorAnalysis,
    ContentType,
    LaunchCampaign,
    LaunchChannel,
)


class TestLaunchStrategistAgent:
    """Tests for LaunchStrategistAgent."""

    @pytest.mark.asyncio
    async def test_execute_returns_success(self) -> None:
        """Test that agent execution returns success."""
        agent = LaunchStrategistAgent()
        campaign = LaunchCampaign(
            name="Test Launch",
            channels=[LaunchChannel.TWITTER, LaunchChannel.PRODUCT_HUNT],
            content_type=ContentType.VIDEO,
            target_audience="Developers",
            metadata={"has_demo_video": True, "has_screenshots": True},
        )
        result = await agent.execute(campaign)
        assert result.success is True
        assert result.data is not None
        assert "launch_score" in result.data
        assert "channel_strategies" in result.data
        assert "content_recommendations" in result.data

    @pytest.mark.asyncio
    async def test_launch_score_calculation(self) -> None:
        """Test that launch score is calculated correctly."""
        agent = LaunchStrategistAgent()
        campaign = LaunchCampaign(
            name="Test",
            channels=[LaunchChannel.TWITTER],
            content_type=ContentType.TEXT,
        )
        result = await agent.execute(campaign)
        assert result.success is True
        score = result.data["launch_score"]
        assert 0 <= score["overall"] <= 1
        assert 0 <= score["content_quality"] <= 1
        assert 0 <= score["channel_fit"] <= 1

    @pytest.mark.asyncio
    async def test_channel_strategies_generated(self) -> None:
        """Test that channel strategies are generated for each channel."""
        agent = LaunchStrategistAgent()
        campaign = LaunchCampaign(
            name="Test",
            channels=[LaunchChannel.TWITTER, LaunchChannel.PRODUCT_HUNT, LaunchChannel.REDDIT],
            content_type=ContentType.TEXT,
        )
        result = await agent.execute(campaign)
        assert result.success is True
        strategies = result.data["channel_strategies"]
        assert len(strategies) == 3
        assert "twitter" in strategies
        assert "product_hunt" in strategies
        assert "reddit" in strategies

    @pytest.mark.asyncio
    async def test_recommendations_generated(self) -> None:
        """Test that recommendations are generated for low scores."""
        agent = LaunchStrategistAgent()
        campaign = LaunchCampaign(
            name="Test",
            channels=[LaunchChannel.TWITTER],
            content_type=ContentType.TEXT,
        )
        result = await agent.execute(campaign)
        assert result.success is True
        score = result.data["launch_score"]
        # Low quality campaign should have recommendations
        assert len(score["recommendations"]) > 0


class TestChannelAnalyzerAgent:
    """Tests for ChannelAnalyzerAgent."""

    @pytest.mark.asyncio
    async def test_execute_returns_success(self) -> None:
        """Test that agent execution returns success."""
        agent = ChannelAnalyzerAgent()
        analytics = CampaignAnalytics(
            campaign_id=uuid.uuid4(),
            channel_performance=[
                ChannelPerformance(
                    channel=LaunchChannel.TWITTER,
                    impressions=10000,
                    clicks=500,
                    conversions=50,
                    spend=100.0,
                    revenue=300.0,
                    roas=3.0,
                ),
                ChannelPerformance(
                    channel=LaunchChannel.PRODUCT_HUNT,
                    impressions=5000,
                    clicks=200,
                    conversions=20,
                    spend=200.0,
                    revenue=100.0,
                    roas=0.5,
                ),
            ],
        )
        result = await agent.execute(analytics)
        assert result.success is True
        assert result.data is not None
        assert "ranked_channels" in result.data
        assert "underperformers" in result.data
        assert "optimal_allocation" in result.data

    @pytest.mark.asyncio
    async def test_rank_channels_by_roas(self) -> None:
        """Test that channels are ranked by ROAS."""
        agent = ChannelAnalyzerAgent()
        analytics = CampaignAnalytics(
            campaign_id=uuid.uuid4(),
            channel_performance=[
                ChannelPerformance(
                    channel=LaunchChannel.TWITTER,
                    spend=100.0,
                    revenue=300.0,
                    roas=3.0,
                ),
                ChannelPerformance(
                    channel=LaunchChannel.PRODUCT_HUNT,
                    spend=100.0,
                    revenue=50.0,
                    roas=0.5,
                ),
            ],
        )
        result = await agent.execute(analytics)
        assert result.success is True
        ranked = result.data["ranked_channels"]
        assert ranked[0]["channel"] == "twitter"
        assert ranked[1]["channel"] == "product_hunt"

    @pytest.mark.asyncio
    async def test_identify_underperformers(self) -> None:
        """Test that underperforming channels are identified."""
        agent = ChannelAnalyzerAgent()
        analytics = CampaignAnalytics(
            campaign_id=uuid.uuid4(),
            channel_performance=[
                ChannelPerformance(
                    channel=LaunchChannel.TWITTER,
                    spend=100.0,
                    revenue=300.0,
                    roas=3.0,
                ),
                ChannelPerformance(
                    channel=LaunchChannel.PRODUCT_HUNT,
                    spend=200.0,
                    revenue=100.0,
                    roas=0.5,
                ),
            ],
        )
        result = await agent.execute(analytics)
        assert result.success is True
        underperformers = result.data["underperformers"]
        assert len(underperformers) == 1
        assert underperformers[0]["channel"] == "product_hunt"


class TestCompetitorResearcherAgent:
    """Tests for CompetitorResearcherAgent."""

    @pytest.mark.asyncio
    async def test_execute_returns_success(self) -> None:
        """Test that agent execution returns success."""
        agent = CompetitorResearcherAgent()
        competitor = CompetitorAnalysis(
            competitor_name="Unfair.so",
            channels=[LaunchChannel.TWITTER, LaunchChannel.PRODUCT_HUNT],
            estimated_reach=500000,
            content_strategy="Creator marketing",
        )
        result = await agent.execute(competitor)
        assert result.success is True
        assert result.data is not None
        assert "strengths" in result.data
        assert "weaknesses" in result.data
        assert "opportunities" in result.data
        assert "counter_strategy" in result.data

    @pytest.mark.asyncio
    async def test_analyze_strengths(self) -> None:
        """Test that strengths are identified."""
        agent = CompetitorResearcherAgent()
        competitor = CompetitorAnalysis(
            competitor_name="Big Competitor",
            channels=[LaunchChannel.TWITTER, LaunchChannel.PRODUCT_HUNT, LaunchChannel.REDDIT],
            estimated_reach=500000,
            content_strategy="Multi-channel creator marketing",
        )
        result = await agent.execute(competitor)
        assert result.success is True
        assert len(result.data["strengths"]) > 0

    @pytest.mark.asyncio
    async def test_identify_opportunities(self) -> None:
        """Test that opportunities are identified."""
        agent = CompetitorResearcherAgent()
        competitor = CompetitorAnalysis(
            competitor_name="Small Competitor",
            channels=[LaunchChannel.TWITTER],
            estimated_reach=5000,
        )
        result = await agent.execute(competitor)
        assert result.success is True
        assert len(result.data["opportunities"]) > 0
