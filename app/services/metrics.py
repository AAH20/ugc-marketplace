"""Metrics computation service."""
from __future__ import annotations


class MetricsService:
    """Compute campaign performance metrics."""

    def compute_ctr(self, clicks: int, impressions: int) -> float:
        """Click-through rate."""
        if impressions == 0:
            return 0.0
        return clicks / impressions

    def compute_roas(self, revenue: float, spend: float) -> float:
        """Return on ad spend."""
        if spend == 0:
            return 0.0
        return revenue / spend

    def compute_cpc(self, spend: float, clicks: int) -> float:
        """Cost per click."""
        if clicks == 0:
            return 0.0
        return spend / clicks

    def compute_cpm(self, spend: float, impressions: int) -> float:
        """Cost per mille (1000 impressions)."""
        if impressions == 0:
            return 0.0
        return (spend / impressions) * 1000

    def compute_conversion_rate(self, conversions: int, clicks: int) -> float:
        """Conversion rate."""
        if clicks == 0:
            return 0.0
        return conversions / clicks

    def aggregate(self, metrics: list[dict]) -> dict:
        """Aggregate a list of metric dicts into summary statistics."""
        total_impressions = sum(m["impressions"] for m in metrics)
        total_clicks = sum(m["clicks"] for m in metrics)
        total_conversions = sum(m["conversions"] for m in metrics)
        total_spend = sum(m["spend"] for m in metrics)
        total_revenue = sum(m["revenue"] for m in metrics)

        return {
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "total_spend": round(total_spend, 2),
            "total_revenue": round(total_revenue, 2),
            "ctr": round(self.compute_ctr(total_clicks, total_impressions), 6),
            "roas": round(self.compute_roas(total_revenue, total_spend), 4),
            "cpc": round(self.compute_cpc(total_spend, total_clicks), 4),
            "cpm": round(self.compute_cpm(total_spend, total_impressions), 4),
            "conversion_rate": round(self.compute_conversion_rate(total_conversions, total_clicks), 6),
        }
