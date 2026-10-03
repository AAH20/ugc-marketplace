"""Analytics service for the UGC Marketplace.

Provides aggregated metrics for marketplace performance, creator activity,
content engagement, and revenue tracking.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

VALID_TIME_RANGES = {"7d", "30d", "90d", "12m", "all"}


def _parse_time_range(time_range: str) -> tuple[datetime, datetime]:
    """Convert a time-range string into a (start, end) datetime tuple.

    Args:
        time_range: One of ``"7d"``, ``"30d"``, ``"90d"``, ``"12m"``, or ``"all"``.

    Returns:
        A tuple of (start_datetime, end_datetime) in UTC.

    Raises:
        ValueError: If *time_range* is not a recognised value.
    """
    end = datetime.now(timezone.utc)
    delta_map = {
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "12m": timedelta(days=365),
    }
    if time_range == "all":
        start = datetime(1970, 1, 1, tzinfo=timezone.utc)
    elif time_range in delta_map:
        start = end - delta_map[time_range]
    else:
        raise ValueError(
            f"Invalid time_range '{time_range}'. "
            f"Must be one of: {', '.join(sorted(VALID_TIME_RANGES))}"
        )
    return start, end


def get_marketplace_metrics(time_range: str) -> dict[str, Any]:
    """Get high-level marketplace metrics for the given time range.

    Args:
        time_range: Period to aggregate over — ``"7d"``, ``"30d"``,
            ``"90d"``, ``"12m"``, or ``"all"``.

    Returns:
        A dictionary containing marketplace-level KPIs such as total users,
        active users, total content items, total transactions, and GMV.

    Raises:
        ValueError: If *time_range* is invalid.
        RuntimeError: If the metrics cannot be retrieved.
    """
    try:
        start, end = _parse_time_range(time_range)
        logger.info("Fetching marketplace metrics from %s to %s", start, end)

        metrics: dict[str, Any] = {
            "time_range": time_range,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "total_users": 0,
            "active_users": 0,
            "total_creators": 0,
            "total_content_items": 0,
            "total_transactions": 0,
            "gross_merchandise_value": 0.0,
            "average_order_value": 0.0,
            "conversion_rate": 0.0,
        }
        return metrics
    except ValueError:
        raise
    except Exception as exc:
        logger.error("Failed to get marketplace metrics: %s", exc)
        raise RuntimeError(f"Failed to get marketplace metrics: {exc}") from exc


def get_creator_analytics(time_range: str) -> dict[str, Any]:
    """Get creator-focused analytics for the given time range.

    Args:
        time_range: Period to aggregate over — ``"7d"``, ``"30d"``,
            ``"90d"``, ``"12m"``, or ``"all"``.

    Returns:
        A dictionary containing creator KPIs such as new creators, active
        creators, top creators by revenue, and creator retention rate.

    Raises:
        ValueError: If *time_range* is invalid.
        RuntimeError: If the analytics cannot be retrieved.
    """
    try:
        start, end = _parse_time_range(time_range)
        logger.info("Fetching creator analytics from %s to %s", start, end)

        analytics: dict[str, Any] = {
            "time_range": time_range,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "new_creators": 0,
            "active_creators": 0,
            "total_creators": 0,
            "creator_retention_rate": 0.0,
            "average_revenue_per_creator": 0.0,
            "top_creators": [],
        }
        return analytics
    except ValueError:
        raise
    except Exception as exc:
        logger.error("Failed to get creator analytics: %s", exc)
        raise RuntimeError(f"Failed to get creator analytics: {exc}") from exc


def get_content_analytics(time_range: str) -> dict[str, Any]:
    """Get content-focused analytics for the given time range.

    Args:
        time_range: Period to aggregate over — ``"7d"``, ``"30d"``,
            ``"90d"``, ``"12m"``, or ``"all"``.

    Returns:
        A dictionary containing content KPIs such as new content items,
        published items, total views, likes, shares, and engagement rate.

    Raises:
        ValueError: If *time_range* is invalid.
        RuntimeError: If the analytics cannot be retrieved.
    """
    try:
        start, end = _parse_time_range(time_range)
        logger.info("Fetching content analytics from %s to %s", start, end)

        analytics: dict[str, Any] = {
            "time_range": time_range,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "new_content_items": 0,
            "published_content_items": 0,
            "total_content_items": 0,
            "total_views": 0,
            "total_likes": 0,
            "total_shares": 0,
            "engagement_rate": 0.0,
            "top_performing_content": [],
        }
        return analytics
    except ValueError:
        raise
    except Exception as exc:
        logger.error("Failed to get content analytics: %s", exc)
        raise RuntimeError(f"Failed to get content analytics: {exc}") from exc


def get_revenue_analytics(time_range: str) -> dict[str, Any]:
    """Get revenue-focused analytics for the given time range.

    Args:
        time_range: Period to aggregate over — ``"7d"``, ``"30d"``,
            ``"90d"``, ``"12m"``, or ``"all"``.

    Returns:
        A dictionary containing revenue KPIs such as total revenue, platform
        fee revenue, creator payouts, refunds, and revenue by category.

    Raises:
        ValueError: If *time_range* is invalid.
        RuntimeError: If the analytics cannot be retrieved.
    """
    try:
        start, end = _parse_time_range(time_range)
        logger.info("Fetching revenue analytics from %s to %s", start, end)

        analytics: dict[str, Any] = {
            "time_range": time_range,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "total_revenue": 0.0,
            "platform_fee_revenue": 0.0,
            "creator_payouts": 0.0,
            "refunds": 0.0,
            "net_revenue": 0.0,
            "revenue_by_category": {},
            "monthly_recurring_revenue": 0.0,
        }
        return analytics
    except ValueError:
        raise
    except Exception as exc:
        logger.error("Failed to get revenue analytics: %s", exc)
        raise RuntimeError(f"Failed to get revenue analytics: {exc}") from exc
