"""Comprehensive service tests for the analytics service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ugc_marketplace.services.analytics_service import (
    AnalyticsService,
    get_creator_analytics,
    get_content_analytics,
    get_marketplace_metrics,
    get_revenue_analytics,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db():
    """Provide a mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.scalar = AsyncMock()
    db.scalars = AsyncMock()
    return db


@pytest.fixture
def mock_cache():
    """Provide a mock cache client."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    return cache


@pytest.fixture
def analytics_service(mock_db, mock_cache):
    """Provide an AnalyticsService instance with mocked dependencies."""
    return AnalyticsService(db=mock_db, cache=mock_cache)


@pytest.fixture
def sample_marketplace_metrics():
    """Return sample marketplace metrics data."""
    return {
        "total_users": 1500,
        "total_creators": 320,
        "total_content_items": 5400,
        "total_transactions": 8900,
        "total_revenue": 125000.50,
        "active_users_7d": 850,
        "active_users_30d": 1200,
        "new_users_7d": 45,
        "new_users_30d": 180,
        "conversion_rate": 0.067,
        "avg_order_value": 14.05,
        "period_start": "2025-09-01T00:00:00Z",
        "period_end": "2025-09-30T23:59:59Z",
    }


@pytest.fixture
def sample_creator_analytics():
    """Return sample creator analytics data."""
    return {
        "creator_id": "creator-001",
        "display_name": "Test Creator",
        "total_content": 42,
        "total_views": 125000,
        "total_likes": 8900,
        "total_shares": 1200,
        "total_revenue": 5600.75,
        "follower_count": 3400,
        "engagement_rate": 0.071,
        "top_performing_content": [
            {"content_id": "c-001", "views": 25000, "likes": 1800},
            {"content_id": "c-002", "views": 18000, "likes": 1200},
        ],
        "content_breakdown": {
            "images": 20,
            "videos": 15,
            "text": 7,
        },
        "period_start": "2025-09-01T00:00:00Z",
        "period_end": "2025-09-30T23:59:59Z",
    }


@pytest.fixture
def sample_content_analytics():
    """Return sample content analytics data."""
    return {
        "content_id": "content-001",
        "creator_id": "creator-001",
        "content_type": "video",
        "views": 50000,
        "unique_views": 42000,
        "likes": 3200,
        "shares": 450,
        "comments": 180,
        "avg_watch_time_seconds": 45.5,
        "completion_rate": 0.62,
        "revenue_generated": 890.25,
        "impressions": 75000,
        "click_through_rate": 0.056,
        "period_start": "2025-09-01T00:00:00Z",
        "period_end": "2025-09-30T23:59:59Z",
    }


@pytest.fixture
def sample_revenue_analytics():
    """Return sample revenue analytics data."""
    return {
        "total_revenue": 125000.50,
        "total_transactions": 8900,
        "avg_order_value": 14.05,
        "refund_rate": 0.023,
        "refund_amount": 2875.01,
        "net_revenue": 122125.49,
        "revenue_by_content_type": {
            "images": 35000.00,
            "videos": 65000.50,
            "text": 25000.00,
        },
        "revenue_by_creator_tier": {
            "bronze": 15000.00,
            "silver": 35000.00,
            "gold": 45000.50,
            "platinum": 30000.00,
        },
        "daily_revenue": [
            {"date": "2025-09-01", "revenue": 4200.50},
            {"date": "2025-09-02", "revenue": 3800.00},
            {"date": "2025-09-03", "revenue": 5100.75},
        ],
        "period_start": "2025-09-01T00:00:00Z",
        "period_end": "2025-09-30T23:59:59Z",
    }


@pytest.fixture
def date_range():
    """Return a standard date range for testing."""
    return {
        "start_date": datetime(2025, 9, 1, tzinfo=timezone.utc),
        "end_date": datetime(2025, 9, 30, 23, 59, 59, tzinfo=timezone.utc),
    }


# ---------------------------------------------------------------------------
# Tests: get_marketplace_metrics
# ---------------------------------------------------------------------------


class TestGetMarketplaceMetrics:
    """Tests for the get_marketplace_metrics function."""

    @pytest.mark.asyncio
    async def test_get_marketplace_metrics_returns_expected_data(
        self, mock_db, sample_marketplace_metrics, date_range
    ):
        """Test that get_marketplace_metrics returns the expected metrics data."""
        mock_db.execute.return_value = MagicMock(
            **sample_marketplace_metrics
        )

        result = await get_marketplace_metrics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert result is not None
        assert result["total_users"] == 1500
        assert result["total_creators"] == 320
        assert result["total_content_items"] == 5400
        assert result["total_transactions"] == 8900
        assert result["total_revenue"] == 125000.50
        assert result["active_users_7d"] == 850
        assert result["active_users_30d"] == 1200
        assert result["new_users_7d"] == 45
        assert result["new_users_30d"] == 180
        assert result["conversion_rate"] == pytest.approx(0.067)
        assert result["avg_order_value"] == pytest.approx(14.05)

    @pytest.mark.asyncio
    async def test_get_marketplace_metrics_calls_db_with_correct_params(
        self, mock_db, sample_marketplace_metrics, date_range
    ):
        """Test that get_marketplace_metrics queries the database with correct date range."""
        mock_db.execute.return_value = MagicMock(
            **sample_marketplace_metrics
        )

        await get_marketplace_metrics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_get_marketplace_metrics_with_no_data(self, mock_db):
        """Test that get_marketplace_metrics handles empty result set gracefully."""
        mock_db.execute.return_value = None

        result = await get_marketplace_metrics(
            db=mock_db,
            start_date=datetime(2025, 9, 1, tzinfo=timezone.utc),
            end_date=datetime(2025, 9, 30, tzinfo=timezone.utc),
        )

        assert result is None or result == {}

    @pytest.mark.asyncio
    async def test_get_marketplace_metrics_with_default_dates(self, mock_db, sample_marketplace_metrics):
        """Test that get_marketplace_metrics works with default date parameters."""
        mock_db.execute.return_value = MagicMock(
            **sample_marketplace_metrics
        )

        result = await get_marketplace_metrics(db=mock_db)

        assert result is not None
        assert result["total_users"] == 1500

    @pytest.mark.asyncio
    async def test_get_marketplace_metrics_caching(
        self, mock_db, mock_cache, sample_marketplace_metrics, date_range
    ):
        """Test that get_marketplace_metrics uses cache when available."""
        cached_data = sample_marketplace_metrics
        mock_cache.get.return_value = cached_data

        result = await get_marketplace_metrics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
            cache=mock_cache,
        )

        assert result == cached_data
        mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_marketplace_metrics_cache_miss_queries_db(
        self, mock_db, mock_cache, sample_marketplace_metrics, date_range
    ):
        """Test that get_marketplace_metrics queries DB on cache miss."""
        mock_cache.get.return_value = None
        mock_db.execute.return_value = MagicMock(
            **sample_marketplace_metrics
        )

        result = await get_marketplace_metrics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
            cache=mock_cache,
        )

        assert result is not None
        assert result["total_users"] == 1500
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_marketplace_metrics_stores_in_cache(
        self, mock_db, mock_cache, sample_marketplace_metrics, date_range
    ):
        """Test that get_marketplace_metrics stores result in cache after DB query."""
        mock_cache.get.return_value = None
        mock_db.execute.return_value = MagicMock(
            **sample_marketplace_metrics
        )

        await get_marketplace_metrics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
            cache=mock_cache,
        )

        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_marketplace_metrics_with_service_instance(
        self, analytics_service, sample_marketplace_metrics, date_range
    ):
        """Test get_marketplace_metrics via AnalyticsService instance."""
        analytics_service.db.execute.return_value = MagicMock(
            **sample_marketplace_metrics
        )

        result = await analytics_service.get_marketplace_metrics(
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert result is not None
        assert result["total_users"] == 1500
        assert result["total_revenue"] == 125000.50

    @pytest.mark.asyncio
    async def test_get_marketplace_metrics_db_error_handling(self, mock_db):
        """Test that get_marketplace_metrics handles database errors."""
        mock_db.execute.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception, match="Database connection failed"):
            await get_marketplace_metrics(
                db=mock_db,
                start_date=datetime(2025, 9, 1, tzinfo=timezone.utc),
                end_date=datetime(2025, 9, 30, tzinfo=timezone.utc),
            )

    @pytest.mark.asyncio
    async def test_get_marketplace_metrics_revenue_is_numeric(
        self, mock_db, sample_marketplace_metrics, date_range
    ):
        """Test that revenue fields are numeric types."""
        mock_db.execute.return_value = MagicMock(
            **sample_marketplace_metrics
        )

        result = await get_marketplace_metrics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert isinstance(result["total_revenue"], (int, float))
        assert isinstance(result["avg_order_value"], (int, float))
        assert result["total_revenue"] >= 0
        assert result["avg_order_value"] >= 0

    @pytest.mark.asyncio
    async def test_get_marketplace_metrics_counts_are_non_negative(
        self, mock_db, sample_marketplace_metrics, date_range
    ):
        """Test that all count fields are non-negative."""
        mock_db.execute.return_value = MagicMock(
            **sample_marketplace_metrics
        )

        result = await get_marketplace_metrics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        count_fields = [
            "total_users",
            "total_creators",
            "total_content_items",
            "total_transactions",
            "active_users_7d",
            "active_users_30d",
            "new_users_7d",
            "new_users_30d",
        ]
        for field in count_fields:
            assert result[field] >= 0, f"{field} should be non-negative"

    @pytest.mark.asyncio
    async def test_get_marketplace_metrics_conversion_rate_range(
        self, mock_db, sample_marketplace_metrics, date_range
    ):
        """Test that conversion rate is between 0 and 1."""
        mock_db.execute.return_value = MagicMock(
            **sample_marketplace_metrics
        )

        result = await get_marketplace_metrics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert 0 <= result["conversion_rate"] <= 1


# ---------------------------------------------------------------------------
# Tests: get_creator_analytics
# ---------------------------------------------------------------------------


class TestGetCreatorAnalytics:
    """Tests for the get_creator_analytics function."""

    @pytest.mark.asyncio
    async def test_get_creator_analytics_returns_expected_data(
        self, mock_db, sample_creator_analytics, date_range
    ):
        """Test that get_creator_analytics returns the expected analytics data."""
        mock_db.execute.return_value = MagicMock(
            **sample_creator_analytics
        )

        result = await get_creator_analytics(
            db=mock_db,
            creator_id="creator-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert result is not None
        assert result["creator_id"] == "creator-001"
        assert result["display_name"] == "Test Creator"
        assert result["total_content"] == 42
        assert result["total_views"] == 125000
        assert result["total_likes"] == 8900
        assert result["total_shares"] == 1200
        assert result["total_revenue"] == 5600.75
        assert result["follower_count"] == 3400
        assert result["engagement_rate"] == pytest.approx(0.071)

    @pytest.mark.asyncio
    async def test_get_creator_analytics_includes_top_content(
        self, mock_db, sample_creator_analytics, date_range
    ):
        """Test that get_creator_analytics includes top performing content."""
        mock_db.execute.return_value = MagicMock(
            **sample_creator_analytics
        )

        result = await get_creator_analytics(
            db=mock_db,
            creator_id="creator-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert "top_performing_content" in result
        assert len(result["top_performing_content"]) == 2
        assert result["top_performing_content"][0]["content_id"] == "c-001"
        assert result["top_performing_content"][0]["views"] == 25000

    @pytest.mark.asyncio
    async def test_get_creator_analytics_includes_content_breakdown(
        self, mock_db, sample_creator_analytics, date_range
    ):
        """Test that get_creator_analytics includes content type breakdown."""
        mock_db.execute.return_value = MagicMock(
            **sample_creator_analytics
        )

        result = await get_creator_analytics(
            db=mock_db,
            creator_id="creator-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert "content_breakdown" in result
        assert result["content_breakdown"]["images"] == 20
        assert result["content_breakdown"]["videos"] == 15
        assert result["content_breakdown"]["text"] == 7

    @pytest.mark.asyncio
    async def test_get_creator_analytics_calls_db_with_creator_id(
        self, mock_db, sample_creator_analytics, date_range
    ):
        """Test that get_creator_analytics queries with the correct creator_id."""
        mock_db.execute.return_value = MagicMock(
            **sample_creator_analytics
        )

        await get_creator_analytics(
            db=mock_db,
            creator_id="creator-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_get_creator_analytics_with_no_data(self, mock_db):
        """Test that get_creator_analytics handles non-existent creator gracefully."""
        mock_db.execute.return_value = None

        result = await get_creator_analytics(
            db=mock_db,
            creator_id="non-existent-creator",
            start_date=datetime(2025, 9, 1, tzinfo=timezone.utc),
            end_date=datetime(2025, 9, 30, tzinfo=timezone.utc),
        )

        assert result is None or result == {}

    @pytest.mark.asyncio
    async def test_get_creator_analytics_with_default_dates(
        self, mock_db, sample_creator_analytics
    ):
        """Test that get_creator_analytics works with default date parameters."""
        mock_db.execute.return_value = MagicMock(
            **sample_creator_analytics
        )

        result = await get_creator_analytics(
            db=mock_db,
            creator_id="creator-001",
        )

        assert result is not None
        assert result["creator_id"] == "creator-001"

    @pytest.mark.asyncio
    async def test_get_creator_analytics_caching(
        self, mock_db, mock_cache, sample_creator_analytics, date_range
    ):
        """Test that get_creator_analytics uses cache when available."""
        mock_cache.get.return_value = sample_creator_analytics

        result = await get_creator_analytics(
            db=mock_db,
            creator_id="creator-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
            cache=mock_cache,
        )

        assert result == sample_creator_analytics
        mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_creator_analytics_cache_miss_queries_db(
        self, mock_db, mock_cache, sample_creator_analytics, date_range
    ):
        """Test that get_creator_analytics queries DB on cache miss."""
        mock_cache.get.return_value = None
        mock_db.execute.return_value = MagicMock(
            **sample_creator_analytics
        )

        result = await get_creator_analytics(
            db=mock_db,
            creator_id="creator-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
            cache=mock_cache,
        )

        assert result is not None
        assert result["creator_id"] == "creator-001"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_creator_analytics_stores_in_cache(
        self, mock_db, mock_cache, sample_creator_analytics, date_range
    ):
        """Test that get_creator_analytics stores result in cache after DB query."""
        mock_cache.get.return_value = None
        mock_db.execute.return_value = MagicMock(
            **sample_creator_analytics
        )

        await get_creator_analytics(
            db=mock_db,
            creator_id="creator-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
            cache=mock_cache,
        )

        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_creator_analytics_with_service_instance(
        self, analytics_service, sample_creator_analytics, date_range
    ):
        """Test get_creator_analytics via AnalyticsService instance."""
        analytics_service.db.execute.return_value = MagicMock(
            **sample_creator_analytics
        )

        result = await analytics_service.get_creator_analytics(
            creator_id="creator-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert result is not None
        assert result["total_views"] == 125000
        assert result["total_revenue"] == 5600.75

    @pytest.mark.asyncio
    async def test_get_creator_analytics_db_error_handling(self, mock_db):
        """Test that get_creator_analytics handles database errors."""
        mock_db.execute.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception, match="Database connection failed"):
            await get_creator_analytics(
                db=mock_db,
                creator_id="creator-001",
                start_date=datetime(2025, 9, 1, tzinfo=timezone.utc),
                end_date=datetime(2025, 9, 30, tzinfo=timezone.utc),
            )

    @pytest.mark.asyncio
    async def test_get_creator_analytics_engagement_rate_range(
        self, mock_db, sample_creator_analytics, date_range
    ):
        """Test that engagement rate is between 0 and 1."""
        mock_db.execute.return_value = MagicMock(
            **sample_creator_analytics
        )

        result = await get_creator_analytics(
            db=mock_db,
            creator_id="creator-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert 0 <= result["engagement_rate"] <= 1

    @pytest.mark.asyncio
    async def test_get_creator_analytics_counts_are_non_negative(
        self, mock_db, sample_creator_analytics, date_range
    ):
        """Test that all count fields are non-negative."""
        mock_db.execute.return_value = MagicMock(
            **sample_creator_analytics
        )

        result = await get_creator_analytics(
            db=mock_db,
            creator_id="creator-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        count_fields = [
            "total_content",
            "total_views",
            "total_likes",
            "total_shares",
            "follower_count",
        ]
        for field in count_fields:
            assert result[field] >= 0, f"{field} should be non-negative"

    @pytest.mark.asyncio
    async def test_get_creator_analytics_revenue_is_numeric(
        self, mock_db, sample_creator_analytics, date_range
    ):
        """Test that revenue field is numeric."""
        mock_db.execute.return_value = MagicMock(
            **sample_creator_analytics
        )

        result = await get_creator_analytics(
            db=mock_db,
            creator_id="creator-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert isinstance(result["total_revenue"], (int, float))
        assert result["total_revenue"] >= 0


# ---------------------------------------------------------------------------
# Tests: get_content_analytics
# ---------------------------------------------------------------------------


class TestGetContentAnalytics:
    """Tests for the get_content_analytics function."""

    @pytest.mark.asyncio
    async def test_get_content_analytics_returns_expected_data(
        self, mock_db, sample_content_analytics, date_range
    ):
        """Test that get_content_analytics returns the expected analytics data."""
        mock_db.execute.return_value = MagicMock(
            **sample_content_analytics
        )

        result = await get_content_analytics(
            db=mock_db,
            content_id="content-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert result is not None
        assert result["content_id"] == "content-001"
        assert result["creator_id"] == "creator-001"
        assert result["content_type"] == "video"
        assert result["views"] == 50000
        assert result["unique_views"] == 42000
        assert result["likes"] == 3200
        assert result["shares"] == 450
        assert result["comments"] == 180
        assert result["avg_watch_time_seconds"] == pytest.approx(45.5)
        assert result["completion_rate"] == pytest.approx(0.62)
        assert result["revenue_generated"] == pytest.approx(890.25)
        assert result["impressions"] == 75000
        assert result["click_through_rate"] == pytest.approx(0.056)

    @pytest.mark.asyncio
    async def test_get_content_analytics_calls_db_with_content_id(
        self, mock_db, sample_content_analytics, date_range
    ):
        """Test that get_content_analytics queries with the correct content_id."""
        mock_db.execute.return_value = MagicMock(
            **sample_content_analytics
        )

        await get_content_analytics(
            db=mock_db,
            content_id="content-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_get_content_analytics_with_no_data(self, mock_db):
        """Test that get_content_analytics handles non-existent content gracefully."""
        mock_db.execute.return_value = None

        result = await get_content_analytics(
            db=mock_db,
            content_id="non-existent-content",
            start_date=datetime(2025, 9, 1, tzinfo=timezone.utc),
            end_date=datetime(2025, 9, 30, tzinfo=timezone.utc),
        )

        assert result is None or result == {}

    @pytest.mark.asyncio
    async def test_get_content_analytics_with_default_dates(
        self, mock_db, sample_content_analytics
    ):
        """Test that get_content_analytics works with default date parameters."""
        mock_db.execute.return_value = MagicMock(
            **sample_content_analytics
        )

        result = await get_content_analytics(
            db=mock_db,
            content_id="content-001",
        )

        assert result is not None
        assert result["content_id"] == "content-001"

    @pytest.mark.asyncio
    async def test_get_content_analytics_caching(
        self, mock_db, mock_cache, sample_content_analytics, date_range
    ):
        """Test that get_content_analytics uses cache when available."""
        mock_cache.get.return_value = sample_content_analytics

        result = await get_content_analytics(
            db=mock_db,
            content_id="content-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
            cache=mock_cache,
        )

        assert result == sample_content_analytics
        mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_content_analytics_cache_miss_queries_db(
        self, mock_db, mock_cache, sample_content_analytics, date_range
    ):
        """Test that get_content_analytics queries DB on cache miss."""
        mock_cache.get.return_value = None
        mock_db.execute.return_value = MagicMock(
            **sample_content_analytics
        )

        result = await get_content_analytics(
            db=mock_db,
            content_id="content-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
            cache=mock_cache,
        )

        assert result is not None
        assert result["content_id"] == "content-001"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_content_analytics_stores_in_cache(
        self, mock_db, mock_cache, sample_content_analytics, date_range
    ):
        """Test that get_content_analytics stores result in cache after DB query."""
        mock_cache.get.return_value = None
        mock_db.execute.return_value = MagicMock(
            **sample_content_analytics
        )

        await get_content_analytics(
            db=mock_db,
            content_id="content-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
            cache=mock_cache,
        )

        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_content_analytics_with_service_instance(
        self, analytics_service, sample_content_analytics, date_range
    ):
        """Test get_content_analytics via AnalyticsService instance."""
        analytics_service.db.execute.return_value = MagicMock(
            **sample_content_analytics
        )

        result = await analytics_service.get_content_analytics(
            content_id="content-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert result is not None
        assert result["views"] == 50000
        assert result["revenue_generated"] == pytest.approx(890.25)

    @pytest.mark.asyncio
    async def test_get_content_analytics_db_error_handling(self, mock_db):
        """Test that get_content_analytics handles database errors."""
        mock_db.execute.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception, match="Database connection failed"):
            await get_content_analytics(
                db=mock_db,
                content_id="content-001",
                start_date=datetime(2025, 9, 1, tzinfo=timezone.utc),
                end_date=datetime(2025, 9, 30, tzinfo=timezone.utc),
            )

    @pytest.mark.asyncio
    async def test_get_content_analytics_completion_rate_range(
        self, mock_db, sample_content_analytics, date_range
    ):
        """Test that completion rate is between 0 and 1."""
        mock_db.execute.return_value = MagicMock(
            **sample_content_analytics
        )

        result = await get_content_analytics(
            db=mock_db,
            content_id="content-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert 0 <= result["completion_rate"] <= 1

    @pytest.mark.asyncio
    async def test_get_content_analytics_ctr_range(
        self, mock_db, sample_content_analytics, date_range
    ):
        """Test that click-through rate is between 0 and 1."""
        mock_db.execute.return_value = MagicMock(
            **sample_content_analytics
        )

        result = await get_content_analytics(
            db=mock_db,
            content_id="content-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert 0 <= result["click_through_rate"] <= 1

    @pytest.mark.asyncio
    async def test_get_content_analytics_counts_are_non_negative(
        self, mock_db, sample_content_analytics, date_range
    ):
        """Test that all count fields are non-negative."""
        mock_db.execute.return_value = MagicMock(
            **sample_content_analytics
        )

        result = await get_content_analytics(
            db=mock_db,
            content_id="content-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        count_fields = [
            "views",
            "unique_views",
            "likes",
            "shares",
            "comments",
            "impressions",
        ]
        for field in count_fields:
            assert result[field] >= 0, f"{field} should be non-negative"

    @pytest.mark.asyncio
    async def test_get_content_analytics_unique_views_lte_views(
        self, mock_db, sample_content_analytics, date_range
    ):
        """Test that unique views is less than or equal to total views."""
        mock_db.execute.return_value = MagicMock(
            **sample_content_analytics
        )

        result = await get_content_analytics(
            db=mock_db,
            content_id="content-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert result["unique_views"] <= result["views"]

    @pytest.mark.asyncio
    async def test_get_content_analytics_revenue_is_numeric(
        self, mock_db, sample_content_analytics, date_range
    ):
        """Test that revenue field is numeric."""
        mock_db.execute.return_value = MagicMock(
            **sample_content_analytics
        )

        result = await get_content_analytics(
            db=mock_db,
            content_id="content-001",
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert isinstance(result["revenue_generated"], (int, float))
        assert result["revenue_generated"] >= 0


# ---------------------------------------------------------------------------
# Tests: get_revenue_analytics
# ---------------------------------------------------------------------------


class TestGetRevenueAnalytics:
    """Tests for the get_revenue_analytics function."""

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_returns_expected_data(
        self, mock_db, sample_revenue_analytics, date_range
    ):
        """Test that get_revenue_analytics returns the expected analytics data."""
        mock_db.execute.return_value = MagicMock(
            **sample_revenue_analytics
        )

        result = await get_revenue_analytics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert result is not None
        assert result["total_revenue"] == 125000.50
        assert result["total_transactions"] == 8900
        assert result["avg_order_value"] == pytest.approx(14.05)
        assert result["refund_rate"] == pytest.approx(0.023)
        assert result["refund_amount"] == pytest.approx(2875.01)
        assert result["net_revenue"] == pytest.approx(122125.49)

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_includes_content_type_breakdown(
        self, mock_db, sample_revenue_analytics, date_range
    ):
        """Test that get_revenue_analytics includes revenue by content type."""
        mock_db.execute.return_value = MagicMock(
            **sample_revenue_analytics
        )

        result = await get_revenue_analytics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert "revenue_by_content_type" in result
        assert result["revenue_by_content_type"]["images"] == 35000.00
        assert result["revenue_by_content_type"]["videos"] == 65000.50
        assert result["revenue_by_content_type"]["text"] == 25000.00

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_includes_creator_tier_breakdown(
        self, mock_db, sample_revenue_analytics, date_range
    ):
        """Test that get_revenue_analytics includes revenue by creator tier."""
        mock_db.execute.return_value = MagicMock(
            **sample_revenue_analytics
        )

        result = await get_revenue_analytics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert "revenue_by_creator_tier" in result
        assert result["revenue_by_creator_tier"]["bronze"] == 15000.00
        assert result["revenue_by_creator_tier"]["silver"] == 35000.00
        assert result["revenue_by_creator_tier"]["gold"] == 45000.50
        assert result["revenue_by_creator_tier"]["platinum"] == 30000.00

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_includes_daily_revenue(
        self, mock_db, sample_revenue_analytics, date_range
    ):
        """Test that get_revenue_analytics includes daily revenue breakdown."""
        mock_db.execute.return_value = MagicMock(
            **sample_revenue_analytics
        )

        result = await get_revenue_analytics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert "daily_revenue" in result
        assert len(result["daily_revenue"]) == 3
        assert result["daily_revenue"][0]["date"] == "2025-09-01"
        assert result["daily_revenue"][0]["revenue"] == 4200.50

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_calls_db_with_correct_params(
        self, mock_db, sample_revenue_analytics, date_range
    ):
        """Test that get_revenue_analytics queries the database with correct date range."""
        mock_db.execute.return_value = MagicMock(
            **sample_revenue_analytics
        )

        await get_revenue_analytics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_with_no_data(self, mock_db):
        """Test that get_revenue_analytics handles empty result set gracefully."""
        mock_db.execute.return_value = None

        result = await get_revenue_analytics(
            db=mock_db,
            start_date=datetime(2025, 9, 1, tzinfo=timezone.utc),
            end_date=datetime(2025, 9, 30, tzinfo=timezone.utc),
        )

        assert result is None or result == {}

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_with_default_dates(
        self, mock_db, sample_revenue_analytics
    ):
        """Test that get_revenue_analytics works with default date parameters."""
        mock_db.execute.return_value = MagicMock(
            **sample_revenue_analytics
        )

        result = await get_revenue_analytics(db=mock_db)

        assert result is not None
        assert result["total_revenue"] == 125000.50

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_caching(
        self, mock_db, mock_cache, sample_revenue_analytics, date_range
    ):
        """Test that get_revenue_analytics uses cache when available."""
        mock_cache.get.return_value = sample_revenue_analytics

        result = await get_revenue_analytics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
            cache=mock_cache,
        )

        assert result == sample_revenue_analytics
        mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_cache_miss_queries_db(
        self, mock_db, mock_cache, sample_revenue_analytics, date_range
    ):
        """Test that get_revenue_analytics queries DB on cache miss."""
        mock_cache.get.return_value = None
        mock_db.execute.return_value = MagicMock(
            **sample_revenue_analytics
        )

        result = await get_revenue_analytics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
            cache=mock_cache,
        )

        assert result is not None
        assert result["total_revenue"] == 125000.50
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_stores_in_cache(
        self, mock_db, mock_cache, sample_revenue_analytics, date_range
    ):
        """Test that get_revenue_analytics stores result in cache after DB query."""
        mock_cache.get.return_value = None
        mock_db.execute.return_value = MagicMock(
            **sample_revenue_analytics
        )

        await get_revenue_analytics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
            cache=mock_cache,
        )

        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_with_service_instance(
        self, analytics_service, sample_revenue_analytics, date_range
    ):
        """Test get_revenue_analytics via AnalyticsService instance."""
        analytics_service.db.execute.return_value = MagicMock(
            **sample_revenue_analytics
        )

        result = await analytics_service.get_revenue_analytics(
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert result is not None
        assert result["total_revenue"] == 125000.50
        assert result["net_revenue"] == pytest.approx(122125.49)

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_db_error_handling(self, mock_db):
        """Test that get_revenue_analytics handles database errors."""
        mock_db.execute.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception, match="Database connection failed"):
            await get_revenue_analytics(
                db=mock_db,
                start_date=datetime(2025, 9, 1, tzinfo=timezone.utc),
                end_date=datetime(2025, 9, 30, tzinfo=timezone.utc),
            )

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_refund_rate_range(
        self, mock_db, sample_revenue_analytics, date_range
    ):
        """Test that refund rate is between 0 and 1."""
        mock_db.execute.return_value = MagicMock(
            **sample_revenue_analytics
        )

        result = await get_revenue_analytics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert 0 <= result["refund_rate"] <= 1

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_net_revenue_calculation(
        self, mock_db, sample_revenue_analytics, date_range
    ):
        """Test that net revenue equals total revenue minus refund amount."""
        mock_db.execute.return_value = MagicMock(
            **sample_revenue_analytics
        )

        result = await get_revenue_analytics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        expected_net = result["total_revenue"] - result["refund_amount"]
        assert result["net_revenue"] == pytest.approx(expected_net)

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_revenue_is_numeric(
        self, mock_db, sample_revenue_analytics, date_range
    ):
        """Test that revenue fields are numeric types."""
        mock_db.execute.return_value = MagicMock(
            **sample_revenue_analytics
        )

        result = await get_revenue_analytics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert isinstance(result["total_revenue"], (int, float))
        assert isinstance(result["net_revenue"], (int, float))
        assert isinstance(result["refund_amount"], (int, float))
        assert result["total_revenue"] >= 0
        assert result["net_revenue"] >= 0
        assert result["refund_amount"] >= 0

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_counts_are_non_negative(
        self, mock_db, sample_revenue_analytics, date_range
    ):
        """Test that transaction count is non-negative."""
        mock_db.execute.return_value = MagicMock(
            **sample_revenue_analytics
        )

        result = await get_revenue_analytics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert result["total_transactions"] >= 0

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_avg_order_value_positive(
        self, mock_db, sample_revenue_analytics, date_range
    ):
        """Test that average order value is positive."""
        mock_db.execute.return_value = MagicMock(
            **sample_revenue_analytics
        )

        result = await get_revenue_analytics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        assert result["avg_order_value"] > 0

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_content_type_revenue_sums_correctly(
        self, mock_db, sample_revenue_analytics, date_range
    ):
        """Test that content type revenue breakdown sums approximately to total."""
        mock_db.execute.return_value = MagicMock(
            **sample_revenue_analytics
        )

        result = await get_revenue_analytics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        content_type_sum = sum(result["revenue_by_content_type"].values())
        assert content_type_sum == pytest.approx(result["total_revenue"], rel=1e-2)

    @pytest.mark.asyncio
    async def test_get_revenue_analytics_creator_tier_revenue_sums_correctly(
        self, mock_db, sample_revenue_analytics, date_range
    ):
        """Test that creator tier revenue breakdown sums approximately to total."""
        mock_db.execute.return_value = MagicMock(
            **sample_revenue_analytics
        )

        result = await get_revenue_analytics(
            db=mock_db,
            start_date=date_range["start_date"],
            end_date=date_range["end_date"],
        )

        tier_sum = sum(result["revenue_by_creator_tier"].values())
        assert tier_sum == pytest.approx(result["total_revenue"], rel=1e-2)
