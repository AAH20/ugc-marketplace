"""Competitor Researcher Agent — analyzes competitor GTM strategies."""

from __future__ import annotations

from typing import Any

from ugc_marketplace.gtm.agents.base import BaseGTMAgent
from ugc_marketplace.gtm.models import CompetitorAnalysis, LaunchChannel


class CompetitorResearcherAgent(BaseGTMAgent[CompetitorAnalysis]):
    """Agent that researches competitor GTM strategies.

    Analyzes competitor launch patterns, channel usage, content strategies,
    and identifies opportunities for differentiation.
    """

    async def _execute(self, input_data: CompetitorAnalysis) -> dict[str, Any]:
        """Execute competitor research.

        Args:
            input_data: The competitor to research.

        Returns:
            Research result with strategic recommendations.
        """
        # Analyze competitor strengths and weaknesses
        strengths = self._analyze_strengths(input_data)
        weaknesses = self._analyze_weaknesses(input_data)
        opportunities = self._identify_opportunities(input_data)

        # Generate counter-strategy
        counter_strategy = self._counter_strategy(input_data, weaknesses, opportunities)

        return {
            "competitor_name": input_data.competitor_name,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "opportunities": opportunities,
            "counter_strategy": counter_strategy,
            "estimated_market_share": self._estimate_market_share(input_data),
        }

    def _analyze_strengths(self, competitor: CompetitorAnalysis) -> list[str]:
        """Analyze competitor strengths.

        Args:
            competitor: The competitor analysis.

        Returns:
            List of identified strengths.
        """
        strengths = []
        if competitor.estimated_reach > 100000:
            strengths.append("Large audience reach")
        if len(competitor.channels) >= 5:
            strengths.append("Multi-channel presence")
        if competitor.content_strategy:
            strengths.append(f"Strong content strategy: {competitor.content_strategy}")
        return strengths

    def _analyze_weaknesses(self, competitor: CompetitorAnalysis) -> list[str]:
        """Analyze competitor weaknesses.

        Args:
            competitor: The competitor analysis.

        Returns:
            List of identified weaknesses.
        """
        weaknesses = []
        if competitor.estimated_reach < 10000:
            weaknesses.append("Limited audience reach")
        if len(competitor.channels) < 3:
            weaknesses.append("Narrow channel presence")
        if not competitor.content_strategy:
            weaknesses.append("Weak or undefined content strategy")
        return weaknesses

    def _identify_opportunities(self, competitor: CompetitorAnalysis) -> list[str]:
        """Identify market opportunities.

        Args:
            competitor: The competitor analysis.

        Returns:
            List of identified opportunities.
        """
        opportunities = []
        all_channels = {c.value for c in LaunchChannel}
        competitor_channels = {c.value for c in competitor.channels}
        missing = all_channels - competitor_channels
        if missing:
            opportunities.append(f"Untapped channels: {', '.join(missing)}")
        if competitor.estimated_reach < 50000:
            opportunities.append("Room to outspend on paid channels")
        return opportunities

    def _counter_strategy(
        self,
        competitor: CompetitorAnalysis,
        weaknesses: list[str],
        opportunities: list[str],
    ) -> str:
        """Generate counter-strategy.

        Args:
            competitor: The competitor analysis.
            weaknesses: Identified weaknesses.
            opportunities: Identified opportunities.

        Returns:
            Counter-strategy description.
        """
        if weaknesses and opportunities:
            return (
                f"Exploit {competitor.competitor_name}'s weaknesses in "
                f"{', '.join(weaknesses[:2])} by focusing on "
                f"{', '.join(opportunities[:2])}."
            )
        return f"Monitor {competitor.competitor_name} and adapt strategy based on their moves."

    def _estimate_market_share(self, competitor: CompetitorAnalysis) -> float:
        """Estimate competitor market share.

        Args:
            competitor: The competitor analysis.

        Returns:
            Estimated market share percentage.
        """
        # Simplified estimation based on reach
        if competitor.estimated_reach > 1000000:
            return 0.3
        if competitor.estimated_reach > 100000:
            return 0.15
        if competitor.estimated_reach > 10000:
            return 0.05
        return 0.01
