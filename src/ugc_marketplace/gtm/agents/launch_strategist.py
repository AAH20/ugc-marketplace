"""Launch Strategist Agent — designs optimal GTM strategies."""

from __future__ import annotations

from typing import Any

from ugc_marketplace.gtm.agents.base import BaseGTMAgent
from ugc_marketplace.gtm.models import LaunchCampaign, LaunchScore


class LaunchStrategistAgent(BaseGTMAgent[LaunchCampaign]):
    """Agent that designs optimal GTM launch strategies.

    Analyzes campaign parameters and produces a comprehensive launch plan
    with channel selection, timing, content recommendations, and readiness scoring.
    """

    async def _execute(self, input_data: LaunchCampaign) -> dict[str, Any]:
        """Execute launch strategy design.

        Args:
            input_data: The launch campaign to strategize for.

        Returns:
            Strategy result with launch score and recommendations.
        """
        # Calculate launch readiness score
        score = self._calculate_launch_score(input_data)

        # Generate channel-specific strategies
        channel_strategies = {}
        for channel in input_data.channels:
            channel_strategies[channel.value] = self._channel_strategy(channel, input_data)

        # Generate content recommendations
        content_recs = self._content_recommendations(input_data)

        # Generate timing recommendations
        timing_recs = self._timing_recommendations(input_data)

        return {
            "campaign_id": str(input_data.id),
            "launch_score": score.model_dump(),
            "channel_strategies": channel_strategies,
            "content_recommendations": content_recs,
            "timing_recommendations": timing_recs,
            "overall_strategy": self._overall_strategy(input_data, score),
        }

    def _calculate_launch_score(self, campaign: LaunchCampaign) -> LaunchScore:
        """Calculate launch readiness score.

        Args:
            campaign: The campaign to score.

        Returns:
            LaunchScore with detailed scoring.
        """
        # Content quality score
        content_quality = 0.7 if campaign.content_type.value != "text" else 0.5
        if campaign.metadata.get("has_demo_video"):
            content_quality += 0.15
        if campaign.metadata.get("has_screenshots"):
            content_quality += 0.1
        content_quality = min(content_quality, 1.0)

        # Channel fit score
        channel_fit = min(len(campaign.channels) * 0.15, 0.9)
        if len(campaign.channels) >= 3:
            channel_fit += 0.1

        # Timing score
        timing = 0.6
        if campaign.scheduled_at:
            timing += 0.2
        if campaign.metadata.get("optimal_launch_window"):
            timing += 0.2

        # Audience match score
        audience_match = 0.5
        if campaign.target_audience:
            audience_match += 0.3
        if campaign.metadata.get("audience_researched"):
            audience_match += 0.2

        # Overall score
        overall = (content_quality + channel_fit + timing + audience_match) / 4

        # Generate recommendations
        recommendations = []
        if content_quality < 0.7:
            recommendations.append("Add demo video or product screenshots to improve content quality")
        if channel_fit < 0.6:
            recommendations.append("Consider adding more launch channels for broader reach")
        if timing < 0.8:
            recommendations.append("Schedule launch for optimal timing (Tuesday-Thursday, 9-11am EST)")
        if audience_match < 0.7:
            recommendations.append("Define and research your target audience more specifically")

        return LaunchScore(
            overall=round(overall, 2),
            content_quality=round(content_quality, 2),
            channel_fit=round(channel_fit, 2),
            timing=round(timing, 2),
            audience_match=round(audience_match, 2),
            recommendations=recommendations,
        )

    def _channel_strategy(self, channel: Any, campaign: LaunchCampaign) -> dict[str, Any]:
        """Generate strategy for a specific channel.

        Args:
            channel: The launch channel.
            campaign: The campaign.

        Returns:
            Channel-specific strategy.
        """
        strategies = {
            "product_hunt": {
                "positioning": "Maker launch with demo video",
                "content_format": "Gallery with demo video + images",
                "timing": "Launch at 12:01 AM PST",
                "expected_reach": "5K-50K visitors",
            },
            "hacker_news": {
                "positioning": "Technical deep-dive post",
                "content_format": "Show HN with technical details",
                "timing": "Post at 8-10 AM EST",
                "expected_reach": "10K-100K views",
            },
            "reddit": {
                "positioning": "Community-focused launch",
                "content_format": "Text post with images",
                "timing": "Post in r/SideProject at 9 AM EST",
                "expected_reach": "5K-30K views",
            },
            "twitter": {
                "positioning": "Viral thread with visuals",
                "content_format": "Thread with images/video",
                "timing": "Post at 9-11 AM EST",
                "expected_reach": "10K-500K impressions",
            },
            "linkedin": {
                "positioning": "Professional announcement",
                "content_format": "Article or carousel",
                "timing": "Post Tuesday-Thursday 8-10 AM",
                "expected_reach": "5K-50K views",
            },
            "tiktok": {
                "positioning": "Viral short-form video",
                "content_format": "15-60 second video",
                "timing": "Post at 7-9 PM EST",
                "expected_reach": "50K-1M views",
            },
            "email": {
                "positioning": "Personal announcement",
                "content_format": "Plain text with CTA",
                "timing": "Send Tuesday-Thursday 9 AM",
                "expected_reach": "20-40% open rate",
            },
            "discord": {
                "positioning": "Community announcement",
                "content_format": "Embed with description",
                "timing": "Post in relevant channels",
                "expected_reach": "1K-10K views",
            },
            "blog": {
                "positioning": "SEO-optimized launch post",
                "content_format": "Long-form article",
                "timing": "Publish and share across channels",
                "expected_reach": "2K-20K organic/month",
            },
            "youtube": {
                "positioning": "Video launch announcement",
                "content_format": "3-10 minute video",
                "timing": "Publish Tuesday-Thursday 2 PM EST",
                "expected_reach": "10K-100K views",
            },
        }
        return strategies.get(channel.value, {"positioning": "General launch", "content_format": "Standard"})

    def _content_recommendations(self, campaign: LaunchCampaign) -> list[str]:
        """Generate content recommendations.

        Args:
            campaign: The campaign.

        Returns:
            List of content recommendations.
        """
        recs = [
            "Create a 30-second demo video showing core value proposition",
            "Prepare 3-5 high-quality product screenshots",
            "Write a compelling one-liner that fits in a tweet",
            "Create a landing page with clear CTA",
            "Prepare a press kit with logos, screenshots, and boilerplate",
        ]
        if campaign.content_type.value == "video":
            recs.append("Also create a 15-second cut for TikTok/Reels")
        return recs

    def _timing_recommendations(self, campaign: LaunchCampaign) -> list[str]:
        """Generate timing recommendations.

        Args:
            campaign: The campaign.

        Returns:
            List of timing recommendations.
        """
        return [
            "Launch on Tuesday, Wednesday, or Thursday for maximum engagement",
            "Post at 9-11 AM EST for US audience",
            "Avoid launching on Fridays, weekends, or holidays",
            "Coordinate all channels to launch within the same 24-hour window",
            "Prepare a 3-day pre-launch teaser campaign",
        ]

    def _overall_strategy(self, campaign: LaunchCampaign, score: LaunchScore) -> str:
        """Generate overall strategy summary.

        Args:
            campaign: The campaign.
            score: The launch score.

        Returns:
            Strategy summary string.
        """
        if score.overall >= 0.8:
            return "Strong launch readiness. Execute across all channels with confidence."
        if score.overall >= 0.6:
            return "Good launch readiness. Address recommendations before launching."
        return "Needs improvement. Focus on content quality and audience research first."
