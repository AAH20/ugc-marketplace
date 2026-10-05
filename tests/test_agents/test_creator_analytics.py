"""
Comprehensive agent tests for creator analytics functions.

Tests cover:
- get_creator_metrics: Core metrics retrieval for creators
- get_creator_growth: Growth trend analysis for creators
- get_creator_engagement: Engagement metrics for creators
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Any

# Import the functions under test
try:
    from ugc_marketplace.agents.creator_analytics import (
        get_creator_metrics,
        get_creator_growth,
        get_creator_engagement,
    )
except ImportError:
    try:
        from ugc_marketplace.agents.analytics import (
            get_creator_metrics,
            get_creator_growth,
            get_creator_engagement,
        )
    except ImportError:
        from ugc_marketplace.agents import (
            get_creator_metrics,
            get_creator_growth,
            get_creator_engagement,
        )


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_creator_id():
    """Return a sample creator ID."""
    return "creator_12345"


@pytest.fixture
def sample_creator_ids():
    """Return a list of sample creator IDs."""
    return ["creator_001", "creator_002", "creator_003"]


@pytest.fixture
def sample_metrics_data():
    """Return sample metrics data for a creator."""
    return {
        "creator_id": "creator_12345",
        "total_posts": 150,
        "total_views": 50000,
        "total_likes": 12000,
        "total_comments": 3500,
        "total_shares": 800,
        "follower_count": 25000,
        "following_count": 500,
        "engagement_rate": 0.072,
        "avg_views_per_post": 333.33,
        "avg_likes_per_post": 80.0,
        "avg_comments_per_post": 23.33,
        "profile_views": 15000,
        "bio_link_clicks": 450,
        "last_updated": "2024-01-15T10:30:00Z",
    }


@pytest.fixture
def sample_growth_data():
    """Return sample growth data for a creator."""
    return {
        "creator_id": "creator_12345",
        "period": "30d",
        "follower_growth": 1500,
        "follower_growth_rate": 0.064,
        "views_growth": 25000,
        "views_growth_rate": 1.0,
        "likes_growth": 5000,
        "likes_growth_rate": 0.667,
        "posts_growth": 25,
        "posts_growth_rate": 0.2,
        "daily_follower_change": [10, 15, 20, 25, 30, 35, 40],
        "daily_views_change": [100, 200, 300, 400, 500, 600, 700],
        "peak_growth_day": "2024-01-10",
        "peak_growth_value": 40,
    }


@pytest.fixture
def sample_engagement_data():
    """Return sample engagement data for a creator."""
    return {
        "creator_id": "creator_12345",
        "period": "30d",
        "total_engagements": 16300,
        "engagement_rate": 0.072,
        "avg_engagement_per_post": 108.67,
        "likes_count": 12000,
        "comments_count": 3500,
        "shares_count": 800,
        "saves_count": 1200,
        "profile_visits": 15000,
        "bio_link_clicks": 450,
        "engagement_by_post": [
            {"post_id": "post_001", "likes": 100, "comments": 30, "shares": 10},
            {"post_id": "post_002", "likes": 150, "comments": 45, "shares": 15},
            {"post_id": "post_003", "likes": 80, "comments": 20, "shares": 5},
        ],
        "engagement_trend": "increasing",
        "best_performing_post_id": "post_002",
        "worst_performing_post_id": "post_003",
    }


@pytest.fixture
def sample_date_range():
    """Return a sample date range."""
    return {
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
    }


@pytest.fixture
def mock_db():
    """Return a mock database connection."""
    mock = MagicMock()
    mock.fetch_one = AsyncMock()
    mock.fetch_all = AsyncMock()
    mock.execute = AsyncMock()
    return mock


@pytest.fixture
def mock_redis():
    """Return a mock Redis client."""
    mock = MagicMock()
    mock.get = AsyncMock()
    mock.set = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest.fixture
def empty_metrics_data():
    """Return empty metrics data."""
    return {
        "creator_id": "creator_12345",
        "total_posts": 0,
        "total_views": 0,
        "total_likes": 0,
        "total_comments": 0,
        "total_shares": 0,
        "follower_count": 0,
        "following_count": 0,
        "engagement_rate": 0.0,
        "avg_views_per_post": 0.0,
        "avg_likes_per_post": 0.0,
        "avg_comments_per_post": 0.0,
        "profile_views": 0,
        "bio_link_clicks": 0,
        "last_updated": None,
    }


@pytest.fixture
def empty_growth_data():
    """Return empty growth data."""
    return {
        "creator_id": "creator_12345",
        "period": "30d",
        "follower_growth": 0,
        "follower_growth_rate": 0.0,
        "views_growth": 0,
        "views_growth_rate": 0.0,
        "likes_growth": 0,
        "likes_growth_rate": 0.0,
        "posts_growth": 0,
        "posts_growth_rate": 0.0,
        "daily_follower_change": [],
        "daily_views_change": [],
        "peak_growth_day": None,
        "peak_growth_value": 0,
    }


@pytest.fixture
def empty_engagement_data():
    """Return empty engagement data."""
    return {
        "creator_id": "creator_12345",
        "period": "30d",
        "total_engagements": 0,
        "engagement_rate": 0.0,
        "avg_engagement_per_post": 0.0,
        "likes_count": 0,
        "comments_count": 0,
        "shares_count": 0,
        "saves_count": 0,
        "profile_visits": 0,
        "bio_link_clicks": 0,
        "engagement_by_post": [],
        "engagement_trend": "stable",
        "best_performing_post_id": None,
        "worst_performing_post_id": None,
    }


# ============================================================================
# Test get_creator_metrics
# ============================================================================


class TestGetCreatorMetrics:
    """Test suite for get_creator_metrics function."""

    @pytest.mark.asyncio
    async def test_get_creator_metrics_success(
        self, sample_creator_id, sample_metrics_data, mock_db
    ):
        """Test successful retrieval of creator metrics."""
        mock_db.fetch_one.return_value = sample_metrics_data

        result = await get_creator_metrics(sample_creator_id, db=mock_db)

        assert result is not None
        assert result["creator_id"] == sample_creator_id
        assert result["total_posts"] == 150
        assert result["total_views"] == 50000
        assert result["total_likes"] == 12000
        assert result["total_comments"] == 3500
        assert result["total_shares"] == 800
        assert result["follower_count"] == 25000
        assert result["engagement_rate"] == pytest.approx(0.072)
        assert result["avg_views_per_post"] == pytest.approx(333.33, rel=1e-2)
        assert result["avg_likes_per_post"] == pytest.approx(80.0)
        assert result["avg_comments_per_post"] == pytest.approx(23.33, rel=1e-2)
        assert result["profile_views"] == 15000
        assert result["bio_link_clicks"] == 450
        assert result["last_updated"] == "2024-01-15T10:30:00Z"

    @pytest.mark.asyncio
    async def test_get_creator_metrics_with_empty_data(
        self, sample_creator_id, empty_metrics_data, mock_db
    ):
        """Test retrieval of creator metrics with empty/zero data."""
        mock_db.fetch_one.return_value = empty_metrics_data

        result = await get_creator_metrics(sample_creator_id, db=mock_db)

        assert result is not None
        assert result["creator_id"] == sample_creator_id
        assert result["total_posts"] == 0
        assert result["total_views"] == 0
        assert result["total_likes"] == 0
        assert result["total_comments"] == 0
        assert result["total_shares"] == 0
        assert result["follower_count"] == 0
        assert result["engagement_rate"] == 0.0
        assert result["avg_views_per_post"] == 0.0
        assert result["avg_likes_per_post"] == 0.0
        assert result["avg_comments_per_post"] == 0.0
        assert result["profile_views"] == 0
        assert result["bio_link_clicks"] == 0
        assert result["last_updated"] is None

    @pytest.mark.asyncio
    async def test_get_creator_metrics_not_found(self, sample_creator_id, mock_db):
        """Test retrieval of creator metrics when creator is not found."""
        mock_db.fetch_one.return_value = None

        result = await get_creator_metrics(sample_creator_id, db=mock_db)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_creator_metrics_with_cache(
        self, sample_creator_id, sample_metrics_data, mock_db, mock_redis
    ):
        """Test retrieval of creator metrics with caching."""
        mock_redis.get.return_value = None
        mock_db.fetch_one.return_value = sample_metrics_data

        result = await get_creator_metrics(
            sample_creator_id, db=mock_db, cache=mock_redis
        )

        assert result is not None
        assert result["creator_id"] == sample_creator_id
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_creator_metrics_cache_hit(
        self, sample_creator_id, sample_metrics_data, mock_db, mock_redis
    ):
        """Test retrieval of creator metrics from cache."""
        import json

        mock_redis.get.return_value = json.dumps(sample_metrics_data)

        result = await get_creator_metrics(
            sample_creator_id, db=mock_db, cache=mock_redis
        )

        assert result is not None
        assert result["creator_id"] == sample_creator_id
        assert result["total_posts"] == 150
        mock_db.fetch_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_creator_metrics_database_error(self, sample_creator_id, mock_db):
        """Test handling of database errors."""
        mock_db.fetch_one.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception, match="Database connection failed"):
            await get_creator_metrics(sample_creator_id, db=mock_db)

    @pytest.mark.asyncio
    async def test_get_creator_metrics_invalid_creator_id(self, mock_db):
        """Test handling of invalid creator ID."""
        with pytest.raises((ValueError, TypeError)):
            await get_creator_metrics("", db=mock_db)

    @pytest.mark.asyncio
    async def test_get_creator_metrics_none_creator_id(self, mock_db):
        """Test handling of None creator ID."""
        with pytest.raises((ValueError, TypeError)):
            await get_creator_metrics(None, db=mock_db)

    @pytest.mark.asyncio
    async def test_get_creator_metrics_with_date_range(
        self, sample_creator_id, sample_metrics_data, sample_date_range, mock_db
    ):
        """Test retrieval of creator metrics with date range filter."""
        mock_db.fetch_one.return_value = sample_metrics_data

        result = await get_creator_metrics(
            sample_creator_id, db=mock_db, **sample_date_range
        )

        assert result is not None
        assert result["creator_id"] == sample_creator_id

    @pytest.mark.asyncio
    async def test_get_creator_metrics_engagement_rate_calculation(
        self, sample_creator_id, mock_db
    ):
        """Test that engagement rate is calculated correctly."""
        metrics = {
            "creator_id": sample_creator_id,
            "total_posts": 100,
            "total_views": 10000,
            "total_likes": 2000,
            "total_comments": 500,
            "total_shares": 200,
            "follower_count": 10000,
            "following_count": 100,
            "engagement_rate": 0.27,
            "avg_views_per_post": 100.0,
            "avg_likes_per_post": 20.0,
            "avg_comments_per_post": 5.0,
            "profile_views": 5000,
            "bio_link_clicks": 100,
            "last_updated": "2024-01-15T10:30:00Z",
        }
        mock_db.fetch_one.return_value = metrics

        result = await get_creator_metrics(sample_creator_id, db=mock_db)

        assert result["engagement_rate"] == pytest.approx(0.27)

    @pytest.mark.asyncio
    async def test_get_creator_metrics_large_numbers(
        self, sample_creator_id, mock_db
    ):
        """Test handling of large metric values."""
        large_metrics = {
            "creator_id": sample_creator_id,
            "total_posts": 10000,
            "total_views": 100000000,
            "total_likes": 5000000,
            "total_comments": 1000000,
            "total_shares": 500000,
            "follower_count": 10000000,
            "following_count": 1000,
            "engagement_rate": 0.15,
            "avg_views_per_post": 10000.0,
            "avg_likes_per_post": 500.0,
            "avg_comments_per_post": 100.0,
            "profile_views": 5000000,
            "bio_link_clicks": 50000,
            "last_updated": "2024-01-15T10:30:00Z",
        }
        mock_db.fetch_one.return_value = large_metrics

        result = await get_creator_metrics(sample_creator_id, db=mock_db)

        assert result["total_views"] == 100000000
        assert result["follower_count"] == 10000000
        assert result["total_likes"] == 5000000

    @pytest.mark.asyncio
    async def test_get_creator_metrics_partial_data(self, sample_creator_id, mock_db):
        """Test handling of partial metrics data."""
        partial_metrics = {
            "creator_id": sample_creator_id,
            "total_posts": 50,
            "total_views": 10000,
            "total_likes": 2000,
            # Missing some fields
        }
        mock_db.fetch_one.return_value = partial_metrics

        result = await get_creator_metrics(sample_creator_id, db=mock_db)

        assert result is not None
        assert result["creator_id"] == sample_creator_id
        assert result["total_posts"] == 50
        assert result["total_views"] == 10000
        assert result["total_likes"] == 2000


# ============================================================================
# Test get_creator_growth
# ============================================================================


class TestGetCreatorGrowth:
    """Test suite for get_creator_growth function."""

    @pytest.mark.asyncio
    async def test_get_creator_growth_success(
        self, sample_creator_id, sample_growth_data, mock_db
    ):
        """Test successful retrieval of creator growth data."""
        mock_db.fetch_one.return_value = sample_growth_data

        result = await get_creator_growth(sample_creator_id, db=mock_db)

        assert result is not None
        assert result["creator_id"] == sample_creator_id
        assert result["period"] == "30d"
        assert result["follower_growth"] == 1500
        assert result["follower_growth_rate"] == pytest.approx(0.064)
        assert result["views_growth"] == 25000
        assert result["views_growth_rate"] == pytest.approx(1.0)
        assert result["likes_growth"] == 5000
        assert result["likes_growth_rate"] == pytest.approx(0.667)
        assert result["posts_growth"] == 25
        assert result["posts_growth_rate"] == pytest.approx(0.2)
        assert len(result["daily_follower_change"]) == 7
        assert len(result["daily_views_change"]) == 7
        assert result["peak_growth_day"] == "2024-01-10"
        assert result["peak_growth_value"] == 40

    @pytest.mark.asyncio
    async def test_get_creator_growth_with_empty_data(
        self, sample_creator_id, empty_growth_data, mock_db
    ):
        """Test retrieval of creator growth with empty/zero data."""
        mock_db.fetch_one.return_value = empty_growth_data

        result = await get_creator_growth(sample_creator_id, db=mock_db)

        assert result is not None
        assert result["creator_id"] == sample_creator_id
        assert result["follower_growth"] == 0
        assert result["follower_growth_rate"] == 0.0
        assert result["views_growth"] == 0
        assert result["views_growth_rate"] == 0.0
        assert result["likes_growth"] == 0
        assert result["likes_growth_rate"] == 0.0
        assert result["posts_growth"] == 0
        assert result["posts_growth_rate"] == 0.0
        assert result["daily_follower_change"] == []
        assert result["daily_views_change"] == []
        assert result["peak_growth_day"] is None
        assert result["peak_growth_value"] == 0

    @pytest.mark.asyncio
    async def test_get_creator_growth_not_found(self, sample_creator_id, mock_db):
        """Test retrieval of creator growth when creator is not found."""
        mock_db.fetch_one.return_value = None

        result = await get_creator_growth(sample_creator_id, db=mock_db)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_creator_growth_with_cache(
        self, sample_creator_id, sample_growth_data, mock_db, mock_redis
    ):
        """Test retrieval of creator growth with caching."""
        mock_redis.get.return_value = None
        mock_db.fetch_one.return_value = sample_growth_data

        result = await get_creator_growth(
            sample_creator_id, db=mock_db, cache=mock_redis
        )

        assert result is not None
        assert result["creator_id"] == sample_creator_id
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_creator_growth_cache_hit(
        self, sample_creator_id, sample_growth_data, mock_db, mock_redis
    ):
        """Test retrieval of creator growth from cache."""
        import json

        mock_redis.get.return_value = json.dumps(sample_growth_data)

        result = await get_creator_growth(
            sample_creator_id, db=mock_db, cache=mock_redis
        )

        assert result is not None
        assert result["creator_id"] == sample_creator_id
        assert result["follower_growth"] == 1500
        mock_db.fetch_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_creator_growth_database_error(self, sample_creator_id, mock_db):
        """Test handling of database errors."""
        mock_db.fetch_one.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception, match="Database connection failed"):
            await get_creator_growth(sample_creator_id, db=mock_db)

    @pytest.mark.asyncio
    async def test_get_creator_growth_invalid_creator_id(self, mock_db):
        """Test handling of invalid creator ID."""
        with pytest.raises((ValueError, TypeError)):
            await get_creator_growth("", db=mock_db)

    @pytest.mark.asyncio
    async def test_get_creator_growth_none_creator_id(self, mock_db):
        """Test handling of None creator ID."""
        with pytest.raises((ValueError, TypeError)):
            await get_creator_growth(None, db=mock_db)

    @pytest.mark.asyncio
    async def test_get_creator_growth_with_period(
        self, sample_creator_id, sample_growth_data, mock_db
    ):
        """Test retrieval of creator growth with different period."""
        mock_db.fetch_one.return_value = sample_growth_data

        result = await get_creator_growth(
            sample_creator_id, period="7d", db=mock_db
        )

        assert result is not None
        assert result["creator_id"] == sample_creator_id

    @pytest.mark.asyncio
    async def test_get_creator_growth_negative_growth(
        self, sample_creator_id, mock_db
    ):
        """Test handling of negative growth values."""
        negative_growth = {
            "creator_id": sample_creator_id,
            "period": "30d",
            "follower_growth": -500,
            "follower_growth_rate": -0.02,
            "views_growth": -10000,
            "views_growth_rate": -0.25,
            "likes_growth": -2000,
            "likes_growth_rate": -0.15,
            "posts_growth": -5,
            "posts_growth_rate": -0.05,
            "daily_follower_change": [-10, -15, -20, -25, -30, -35, -40],
            "daily_views_change": [-100, -200, -300, -400, -500, -600, -700],
            "peak_growth_day": "2024-01-01",
            "peak_growth_value": -10,
        }
        mock_db.fetch_one.return_value = negative_growth

        result = await get_creator_growth(sample_creator_id, db=mock_db)

        assert result is not None
        assert result["follower_growth"] == -500
        assert result["follower_growth_rate"] == pytest.approx(-0.02)
        assert result["views_growth"] == -10000
        assert result["likes_growth"] == -2000

    @pytest.mark.asyncio
    async def test_get_creator_growth_with_date_range(
        self, sample_creator_id, sample_growth_data, sample_date_range, mock_db
    ):
        """Test retrieval of creator growth with date range filter."""
        mock_db.fetch_one.return_value = sample_growth_data

        result = await get_creator_growth(
            sample_creator_id, db=mock_db, **sample_date_range
        )

        assert result is not None
        assert result["creator_id"] == sample_creator_id

    @pytest.mark.asyncio
    async def test_get_creator_growth_large_numbers(
        self, sample_creator_id, mock_db
    ):
        """Test handling of large growth values."""
        large_growth = {
            "creator_id": sample_creator_id,
            "period": "30d",
            "follower_growth": 1000000,
            "follower_growth_rate": 5.0,
            "views_growth": 50000000,
            "views_growth_rate": 10.0,
            "likes_growth": 10000000,
            "likes_growth_rate": 8.0,
            "posts_growth": 5000,
            "posts_growth_rate": 2.0,
            "daily_follower_change": [1000] * 30,
            "daily_views_change": [10000] * 30,
            "peak_growth_day": "2024-01-15",
            "peak_growth_value": 5000,
        }
        mock_db.fetch_one.return_value = large_growth

        result = await get_creator_growth(sample_creator_id, db=mock_db)

        assert result["follower_growth"] == 1000000
        assert result["views_growth"] == 50000000
        assert result["likes_growth"] == 10000000

    @pytest.mark.asyncio
    async def test_get_creator_growth_partial_data(self, sample_creator_id, mock_db):
        """Test handling of partial growth data."""
        partial_growth = {
            "creator_id": sample_creator_id,
            "period": "30d",
            "follower_growth": 100,
            "follower_growth_rate": 0.01,
            # Missing some fields
        }
        mock_db.fetch_one.return_value = partial_growth

        result = await get_creator_growth(sample_creator_id, db=mock_db)

        assert result is not None
        assert result["creator_id"] == sample_creator_id
        assert result["follower_growth"] == 100
        assert result["follower_growth_rate"] == pytest.approx(0.01)


# ============================================================================
# Test get_creator_engagement
# ============================================================================


class TestGetCreatorEngagement:
    """Test suite for get_creator_engagement function."""

    @pytest.mark.asyncio
    async def test_get_creator_engagement_success(
        self, sample_creator_id, sample_engagement_data, mock_db
    ):
        """Test successful retrieval of creator engagement data."""
        mock_db.fetch_one.return_value = sample_engagement_data

        result = await get_creator_engagement(sample_creator_id, db=mock_db)

        assert result is not None
        assert result["creator_id"] == sample_creator_id
        assert result["period"] == "30d"
        assert result["total_engagements"] == 16300
        assert result["engagement_rate"] == pytest.approx(0.072)
        assert result["avg_engagement_per_post"] == pytest.approx(108.67, rel=1e-2)
        assert result["likes_count"] == 12000
        assert result["comments_count"] == 3500
        assert result["shares_count"] == 800
        assert result["saves_count"] == 1200
        assert result["profile_visits"] == 15000
        assert result["bio_link_clicks"] == 450
        assert len(result["engagement_by_post"]) == 3
        assert result["engagement_trend"] == "increasing"
        assert result["best_performing_post_id"] == "post_002"
        assert result["worst_performing_post_id"] == "post_003"

    @pytest.mark.asyncio
    async def test_get_creator_engagement_with_empty_data(
        self, sample_creator_id, empty_engagement_data, mock_db
    ):
        """Test retrieval of creator engagement with empty/zero data."""
        mock_db.fetch_one.return_value = empty_engagement_data

        result = await get_creator_engagement(sample_creator_id, db=mock_db)

        assert result is not None
        assert result["creator_id"] == sample_creator_id
        assert result["total_engagements"] == 0
        assert result["engagement_rate"] == 0.0
        assert result["avg_engagement_per_post"] == 0.0
        assert result["likes_count"] == 0
        assert result["comments_count"] == 0
        assert result["shares_count"] == 0
        assert result["saves_count"] == 0
        assert result["profile_visits"] == 0
        assert result["bio_link_clicks"] == 0
        assert result["engagement_by_post"] == []
        assert result["engagement_trend"] == "stable"
        assert result["best_performing_post_id"] is None
        assert result["worst_performing_post_id"] is None

    @pytest.mark.asyncio
    async def test_get_creator_engagement_not_found(self, sample_creator_id, mock_db):
        """Test retrieval of creator engagement when creator is not found."""
        mock_db.fetch_one.return_value = None

        result = await get_creator_engagement(sample_creator_id, db=mock_db)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_creator_engagement_with_cache(
        self, sample_creator_id, sample_engagement_data, mock_db, mock_redis
    ):
        """Test retrieval of creator engagement with caching."""
        mock_redis.get.return_value = None
        mock_db.fetch_one.return_value = sample_engagement_data

        result = await get_creator_engagement(
            sample_creator_id, db=mock_db, cache=mock_redis
        )

        assert result is not None
        assert result["creator_id"] == sample_creator_id
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_creator_engagement_cache_hit(
        self, sample_creator_id, sample_engagement_data, mock_db, mock_redis
    ):
        """Test retrieval of creator engagement from cache."""
        import json

        mock_redis.get.return_value = json.dumps(sample_engagement_data)

        result = await get_creator_engagement(
            sample_creator_id, db=mock_db, cache=mock_redis
        )

        assert result is not None
        assert result["creator_id"] == sample_creator_id
        assert result["total_engagements"] == 16300
        mock_db.fetch_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_creator_engagement_database_error(
        self, sample_creator_id, mock_db
    ):
        """Test handling of database errors."""
        mock_db.fetch_one.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception, match="Database connection failed"):
            await get_creator_engagement(sample_creator_id, db=mock_db)

    @pytest.mark.asyncio
    async def test_get_creator_engagement_invalid_creator_id(self, mock_db):
        """Test handling of invalid creator ID."""
        with pytest.raises((ValueError, TypeError)):
            await get_creator_engagement("", db=mock_db)

    @pytest.mark.asyncio
    async def test_get_creator_engagement_none_creator_id(self, mock_db):
        """Test handling of None creator ID."""
        with pytest.raises((ValueError, TypeError)):
            await get_creator_engagement(None, db=mock_db)

    @pytest.mark.asyncio
    async def test_get_creator_engagement_with_period(
        self, sample_creator_id, sample_engagement_data, mock_db
    ):
        """Test retrieval of creator engagement with different period."""
        mock_db.fetch_one.return_value = sample_engagement_data

        result = await get_creator_engagement(
            sample_creator_id, period="7d", db=mock_db
        )

        assert result is not None
        assert result["creator_id"] == sample_creator_id

    @pytest.mark.asyncio
    async def test_get_creator_engagement_trends(
        self, sample_creator_id, mock_db
    ):
        """Test different engagement trends."""
        trends = ["increasing", "decreasing", "stable"]

        for trend in trends:
            engagement_data = {
                "creator_id": sample_creator_id,
                "period": "30d",
                "total_engagements": 10000,
                "engagement_rate": 0.05,
                "avg_engagement_per_post": 100.0,
                "likes_count": 7000,
                "comments_count": 2000,
                "shares_count": 500,
                "saves_count": 500,
                "profile_visits": 5000,
                "bio_link_clicks": 200,
                "engagement_by_post": [],
                "engagement_trend": trend,
                "best_performing_post_id": "post_001",
                "worst_performing_post_id": "post_002",
            }
            mock_db.fetch_one.return_value = engagement_data

            result = await get_creator_engagement(sample_creator_id, db=mock_db)

            assert result is not None
            assert result["engagement_trend"] == trend

    @pytest.mark.asyncio
    async def test_get_creator_engagement_with_date_range(
        self, sample_creator_id, sample_engagement_data, sample_date_range, mock_db
    ):
        """Test retrieval of creator engagement with date range filter."""
        mock_db.fetch_one.return_value = sample_engagement_data

        result = await get_creator_engagement(
            sample_creator_id, db=mock_db, **sample_date_range
        )

        assert result is not None
        assert result["creator_id"] == sample_creator_id

    @pytest.mark.asyncio
    async def test_get_creator_engagement_large_numbers(
        self, sample_creator_id, mock_db
    ):
        """Test handling of large engagement values."""
        large_engagement = {
            "creator_id": sample_creator_id,
            "period": "30d",
            "total_engagements": 10000000,
            "engagement_rate": 0.25,
            "avg_engagement_per_post": 10000.0,
            "likes_count": 7000000,
            "comments_count": 2000000,
            "shares_count": 500000,
            "saves_count": 500000,
            "profile_visits": 5000000,
            "bio_link_clicks": 50000,
            "engagement_by_post": [
                {"post_id": f"post_{i:03d}", "likes": 1000, "comments": 300, "shares": 100}
                for i in range(100)
            ],
            "engagement_trend": "increasing",
            "best_performing_post_id": "post_001",
            "worst_performing_post_id": "post_100",
        }
        mock_db.fetch_one.return_value = large_engagement

        result = await get_creator_engagement(sample_creator_id, db=mock_db)

        assert result["total_engagements"] == 10000000
        assert result["likes_count"] == 7000000
        assert result["comments_count"] == 2000000
        assert len(result["engagement_by_post"]) == 100

    @pytest.mark.asyncio
    async def test_get_creator_engagement_partial_data(
        self, sample_creator_id, mock_db
    ):
        """Test handling of partial engagement data."""
        partial_engagement = {
            "creator_id": sample_creator_id,
            "period": "30d",
            "total_engagements": 5000,
            "engagement_rate": 0.03,
            # Missing some fields
        }
        mock_db.fetch_one.return_value = partial_engagement

        result = await get_creator_engagement(sample_creator_id, db=mock_db)

        assert result is not None
        assert result["creator_id"] == sample_creator_id
        assert result["total_engagements"] == 5000
        assert result["engagement_rate"] == pytest.approx(0.03)

    @pytest.mark.asyncio
    async def test_get_creator_engagement_by_post_details(
        self, sample_creator_id, sample_engagement_data, mock_db
    ):
        """Test engagement by post details are correctly returned."""
        mock_db.fetch_one.return_value = sample_engagement_data

        result = await get_creator_engagement(sample_creator_id, db=mock_db)

        assert result is not None
        engagement_by_post = result["engagement_by_post"]
        assert len(engagement_by_post) == 3

        # Check first post
        assert engagement_by_post[0]["post_id"] == "post_001"
        assert engagement_by_post[0]["likes"] == 100
        assert engagement_by_post[0]["comments"] == 30
        assert engagement_by_post[0]["shares"] == 10

        # Check second post
        assert engagement_by_post[1]["post_id"] == "post_002"
        assert engagement_by_post[1]["likes"] == 150
        assert engagement_by_post[1]["comments"] == 45
        assert engagement_by_post[1]["shares"] == 15

        # Check third post
        assert engagement_by_post[2]["post_id"] == "post_003"
        assert engagement_by_post[2]["likes"] == 80
        assert engagement_by_post[2]["comments"] == 20
        assert engagement_by_post[2]["shares"] == 5


# ============================================================================
# Integration-style tests
# ============================================================================


class TestCreatorAnalyticsIntegration:
    """Integration-style tests for creator analytics functions."""

    @pytest.mark.asyncio
    async def test_all_functions_with_same_creator(
        self,
        sample_creator_id,
        sample_metrics_data,
        sample_growth_data,
        sample_engagement_data,
        mock_db,
    ):
        """Test all three functions work with the same creator ID."""
        mock_db.fetch_one.side_effect = [
            sample_metrics_data,
            sample_growth_data,
            sample_engagement_data,
        ]

        metrics = await get_creator_metrics(sample_creator_id, db=mock_db)
        growth = await get_creator_growth(sample_creator_id, db=mock_db)
        engagement = await get_creator_engagement(sample_creator_id, db=mock_db)

        assert metrics["creator_id"] == sample_creator_id
        assert growth["creator_id"] == sample_creator_id
        assert engagement["creator_id"] == sample_creator_id

    @pytest.mark.asyncio
    async def test_all_functions_with_empty_data(
        self,
        sample_creator_id,
        empty_metrics_data,
        empty_growth_data,
        empty_engagement_data,
        mock_db,
    ):
        """Test all three functions handle empty data correctly."""
        mock_db.fetch_one.side_effect = [
            empty_metrics_data,
            empty_growth_data,
            empty_engagement_data,
        ]

        metrics = await get_creator_metrics(sample_creator_id, db=mock_db)
        growth = await get_creator_growth(sample_creator_id, db=mock_db)
        engagement = await get_creator_engagement(sample_creator_id, db=mock_db)

        assert metrics["total_posts"] == 0
        assert growth["follower_growth"] == 0
        assert engagement["total_engagements"] == 0

    @pytest.mark.asyncio
    async def test_all_functions_not_found(self, sample_creator_id, mock_db):
        """Test all three functions return None when creator not found."""
        mock_db.fetch_one.return_value = None

        metrics = await get_creator_metrics(sample_creator_id, db=mock_db)
        growth = await get_creator_growth(sample_creator_id, db=mock_db)
        engagement = await get_creator_engagement(sample_creator_id, db=mock_db)

        assert metrics is None
        assert growth is None
        assert engagement is None

    @pytest.mark.asyncio
    async def test_all_functions_database_error(self, sample_creator_id, mock_db):
        """Test all three functions handle database errors."""
        mock_db.fetch_one.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await get_creator_metrics(sample_creator_id, db=mock_db)

        with pytest.raises(Exception, match="Database error"):
            await get_creator_growth(sample_creator_id, db=mock_db)

        with pytest.raises(Exception, match="Database error"):
            await get_creator_engagement(sample_creator_id, db=mock_db)