"""Performance optimization recommendation engine."""

from __future__ import annotations

from typing import Any

from app.models.recommendation import RecommendationCategory


class RecommendationEngine:
    """Generate optimization recommendations based on campaign performance."""

    def generate(
        self,
        campaign_id: int,
        current_roas: float,
        target_roas: float,
        current_ctr: float,
        target_ctr: float,
        spend_trend: str,
    ) -> list[dict]:
        """Generate recommendations based on performance gaps."""
        recs: list[dict[str, Any]] = []

        # ROAS below target → budget reallocation
        if current_roas < target_roas:
            gap = target_roas - current_roas
            impact = min(gap / target_roas, 0.5) if target_roas > 0 else 0.1
            recs.append(
                {
                    "campaign_id": campaign_id,
                    "category": RecommendationCategory.BUDGET_REALLOCATION,
                    "priority": 1,
                    "title": "Reallocate budget from underperforming ad sets",
                    "description": (
                        f"Current ROAS ({current_roas:.2f}) is below target ({target_roas:.2f}). "
                        "Shift budget to higher-performing ad sets or pause underperformers."
                    ),
                    "expected_impact": round(impact, 4),
                }
            )

        # CTR below target → CTR optimization
        if current_ctr < target_ctr:
            gap = target_ctr - current_ctr
            impact = min(gap / target_ctr, 0.4) if target_ctr > 0 else 0.1
            recs.append(
                {
                    "campaign_id": campaign_id,
                    "category": RecommendationCategory.CTR_OPTIMIZATION,
                    "priority": 2,
                    "title": "Refresh ad creative and copy",
                    "description": (
                        f"CTR ({current_ctr:.4f}) is below target ({target_ctr:.4f}). "
                        "Test new headlines, images, and CTAs to improve engagement."
                    ),
                    "expected_impact": round(impact, 4),
                }
            )

        # Spend spike → spend adjustment
        if spend_trend == "spike":
            recs.append(
                {
                    "campaign_id": campaign_id,
                    "category": RecommendationCategory.SPEND_ADJUSTMENT,
                    "priority": 1,
                    "title": "Reduce daily budget cap",
                    "description": (
                        "Spend has spiked above normal levels. "
                        "Lower the daily budget cap or enable pacing to smooth delivery."
                    ),
                    "expected_impact": 0.2,
                }
            )

        # Sort by priority
        recs.sort(key=lambda r: r["priority"])
        return recs
