"""Channel Analyzer Agent — analyzes and optimizes channel performance."""

from __future__ import annotations

from typing import Any

from ugc_marketplace.gtm.agents.base import BaseGTMAgent
from ugc_marketplace.gtm.models import CampaignAnalytics, ChannelPerformance, LaunchChannel


class ChannelAnalyzerAgent(BaseGTMAgent[CampaignAnalytics]):
    """Agent that analyzes channel performance and optimizes allocation.

    Processes campaign analytics data to identify top-performing channels,
    calculate ROI, and recommend budget reallocation.
    """

    async def _execute(self, input_data: CampaignAnalytics) -> dict[str, Any]:
        """Execute channel analysis.

        Args:
            input_data: The campaign analytics to analyze.

        Returns:
            Analysis result with optimization recommendations.
        """
        # Rank channels by ROAS
        ranked = self._rank_channels(input_data.channel_performance)

        # Identify underperformers
        underperformers = self._identify_underperformers(input_data.channel_performance)

        # Calculate optimal budget allocation
        allocation = self._optimal_allocation(input_data)

        # Generate insights
        insights = self._generate_insights(input_data, ranked, underperformers)

        return {
            "campaign_id": str(input_data.campaign_id),
            "ranked_channels": [c.model_dump() for c in ranked],
            "underperformers": [c.model_dump() for c in underperformers],
            "optimal_allocation": allocation,
            "insights": insights,
            "total_roas": input_data.overall_roas,
        }

    def _rank_channels(self, channels: list[ChannelPerformance]) -> list[ChannelPerformance]:
        """Rank channels by ROAS (Return on Ad Spend).

        Args:
            channels: List of channel performance metrics.

        Returns:
            Channels sorted by ROAS descending.
        """
        return sorted(channels, key=lambda c: c.roas, reverse=True)

    def _identify_underperformers(
        self, channels: list[ChannelPerformance]
    ) -> list[ChannelPerformance]:
        """Identify underperforming channels.

        Args:
            channels: List of channel performance metrics.

        Returns:
            Channels with ROAS below 1.0.
        """
        return [c for c in channels if c.roas < 1.0 and c.spend > 0]

    def _optimal_allocation(self, analytics: CampaignAnalytics) -> dict[str, float]:
        """Calculate optimal budget allocation.

        Args:
            analytics: Campaign analytics.

        Returns:
            Channel -> recommended budget percentage.
        """
        if not analytics.channel_performance:
            return {}

        # Weight by ROAS
        total_roas = sum(max(c.roas, 0.1) for c in analytics.channel_performance)
        allocation = {}
        for c in analytics.channel_performance:
            weight = max(c.roas, 0.1) / total_roas
            allocation[c.channel.value] = round(weight, 2)

        return allocation

    def _generate_insights(
        self,
        analytics: CampaignAnalytics,
        ranked: list[ChannelPerformance],
        underperformers: list[ChannelPerformance],
    ) -> list[str]:
        """Generate actionable insights.

        Args:
            analytics: Campaign analytics.
            ranked: Channels ranked by ROAS.
            underperformers: Underperforming channels.

        Returns:
            List of insight strings.
        """
        insights = []

        if ranked:
            top = ranked[0]
            insights.append(
                f"Top channel: {top.channel.value} with ROAS {top.roas:.2f}"
            )

        if underperformers:
            worst = underperformers[-1]
            insights.append(
                f"Consider reducing spend on {worst.channel.value} (ROAS: {worst.roas:.2f})"
            )

        if analytics.overall_roas < 1.0:
            insights.append("Overall ROAS below 1.0 — campaign is unprofitable at current spend")
        elif analytics.overall_roas > 3.0:
            insights.append("Strong ROAS — consider increasing budget to scale")

        if analytics.total_impressions > 0:
            overall_ctr = analytics.total_clicks / analytics.total_impressions
            if overall_ctr < 0.01:
                insights.append("Low CTR — test different creative hooks and thumbnails")

        return insights
