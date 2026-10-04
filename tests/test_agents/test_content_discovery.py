"""Comprehensive agent tests for content discovery functions.

Tests cover recommend_content, search_content, and get_trending_content
from the ugc_marketplace content discovery module.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Any

from ugc_marketplace.agents.content_discovery import (
    recommend_content,
    search_content,
    get_trending_content,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db_session():
    """Provide a mock database session."""
    session = MagicMock()
    session.execute = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def mock_redis_client():
    """Provide a mock Redis client."""
    client = MagicMock()
    client.get = MagicMock(return_value=None)
    client.set = MagicMock(return_value=True)
    client.delete = MagicMock(return_value=True)
    client.exists = MagicMock(return_value=False)
    return client


@pytest.fixture
def mock_llm_client():
    """Provide a mock LLM client."""
    client = MagicMock()
    client.generate = MagicMock(return_value="Generated response")
    client.embed = MagicMock(return_value=[0.1, 0.2, 0.3, 0.4])
    return client


@pytest.fixture
def sample_content_items():
    """Provide sample content items for testing."""
    return [
        {
            "id": "content-001",
            "title": "Amazing Product Review",
            "body": "This product exceeded all my expectations...",
            "author_id": "user-001",
            "category": "reviews",
            "tags": ["product", "review", "tech"],
            "likes": 150,
            "views": 2500,
            "shares": 45,
            "created_at": datetime.now() - timedelta(days=1),
            "updated_at": datetime.now() - timedelta(hours=2),
            "status": "published",
            "score": 0.95,
        },
        {
            "id": "content-002",
            "title": "How to Use This Gadget",
            "body": "In this tutorial, I will show you how...",
            "author_id": "user-002",
            "category": "tutorials",
            "tags": ["tutorial", "gadget", "how-to"],
            "likes": 89,
            "views": 1800,
            "shares": 22,
            "created_at": datetime.now() - timedelta(days=3),
            "updated_at": datetime.now() - timedelta(days=1),
            "status": "published",
            "score": 0.87,
        },
        {
            "id": "content-003",
            "title": "Top 10 Tips for Beginners",
            "body": "Here are my top 10 tips for getting started...",
            "author_id": "user-003",
            "category": "guides",
            "tags": ["tips", "beginners", "guide"],
            "likes": 230,
            "views": 5000,
            "shares": 78,
            "created_at": datetime.now() - timedelta(hours=6),
            "updated_at": datetime.now() - timedelta(hours=1),
            "status": "published",
            "score": 0.92,
        },
    ]


@pytest.fixture
def sample_user_profile():
    """Provide a sample user profile for recommendation testing."""
    return {
        "user_id": "user-001",
        "interests": ["tech", "gadgets", "reviews"],
        "preferred_categories": ["reviews", "tutorials"],
        "view_history": ["content-001", "content-002"],
        "like_history": ["content-001"],
        "share_history": [],
        "search_history": ["product review", "gadget tutorial"],
    }


@pytest.fixture
def sample_trending_data():
    """Provide sample trending data."""
    return [
        {
            "content_id": "content-003",
            "title": "Top 10 Tips for Beginners",
            "trending_score": 95.5,
            "rank": 1,
            "category": "guides",
            "velocity": 12.3,
        },
        {
            "content_id": "content-001",
            "title": "Amazing Product Review",
            "trending_score": 88.2,
            "rank": 2,
            "category": "reviews",
            "velocity": 8.7,
        },
        {
            "content_id": "content-002",
            "title": "How to Use This Gadget",
            "trending_score": 76.1,
            "rank": 3,
            "category": "tutorials",
            "velocity": 5.4,
        },
    ]


@pytest.fixture
def mock_content_repository():
    """Provide a mock content repository."""
    repo = MagicMock()
    repo.get_by_id = MagicMock()
    repo.get_by_category = MagicMock()
    repo.get_trending = MagicMock()
    repo.search = MagicMock()
    repo.get_recommendations = MagicMock()
    repo.get_user_interactions = MagicMock()
    return repo


# ---------------------------------------------------------------------------
# Test recommend_content
# ---------------------------------------------------------------------------


class TestRecommendContent:
    """Tests for the recommend_content function."""

    @pytest.mark.asyncio
    async def test_recommend_content_returns_recommendations(
        self, mock_db_session, mock_redis_client, sample_user_profile, sample_content_items
    ):
        """Test that recommend_content returns content recommendations for a user."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_recommendations.return_value = sample_content_items
            mock_repo.get_user_interactions.return_value = {
                "likes": ["content-001"],
                "views": ["content-001", "content-002"],
            }

            result = await recommend_content(
                user_id="user-001",
                user_profile=sample_user_profile,
                limit=10,
            )

            assert result is not None
            assert isinstance(result, list)
            assert len(result) > 0
            mock_repo.get_recommendations.assert_called_once()

    @pytest.mark.asyncio
    async def test_recommend_content_respects_limit(
        self, mock_db_session, mock_redis_client, sample_user_profile, sample_content_items
    ):
        """Test that recommend_content respects the limit parameter."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_recommendations.return_value = sample_content_items[:2]

            result = await recommend_content(
                user_id="user-001",
                user_profile=sample_user_profile,
                limit=2,
            )

            assert len(result) <= 2

    @pytest.mark.asyncio
    async def test_recommend_content_uses_cache(
        self, mock_db_session, mock_redis_client, sample_user_profile, sample_content_items
    ):
        """Test that recommend_content uses Redis cache when available."""
        mock_redis_client.get.return_value = '[{"id": "content-001", "title": "Cached"}]'

        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value

            result = await recommend_content(
                user_id="user-001",
                user_profile=sample_user_profile,
                limit=10,
            )

            mock_redis_client.get.assert_called()
            assert result is not None

    @pytest.mark.asyncio
    async def test_recommend_content_cache_miss_queries_db(
        self, mock_db_session, mock_redis_client, sample_user_profile, sample_content_items
    ):
        """Test that recommend_content queries the database on cache miss."""
        mock_redis_client.get.return_value = None

        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_recommendations.return_value = sample_content_items

            result = await recommend_content(
                user_id="user-001",
                user_profile=sample_user_profile,
                limit=10,
            )

            mock_repo.get_recommendations.assert_called_once()
            assert len(result) == len(sample_content_items)

    @pytest.mark.asyncio
    async def test_recommend_content_stores_in_cache(
        self, mock_db_session, mock_redis_client, sample_user_profile, sample_content_items
    ):
        """Test that recommend_content stores results in cache."""
        mock_redis_client.get.return_value = None

        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_recommendations.return_value = sample_content_items

            await recommend_content(
                user_id="user-001",
                user_profile=sample_user_profile,
                limit=10,
            )

            mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_recommend_content_empty_user_profile(
        self, mock_db_session, mock_redis_client, sample_content_items
    ):
        """Test recommend_content with an empty user profile."""
        empty_profile = {
            "user_id": "user-999",
            "interests": [],
            "preferred_categories": [],
            "view_history": [],
            "like_history": [],
            "share_history": [],
            "search_history": [],
        }

        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_recommendations.return_value = sample_content_items[:1]

            result = await recommend_content(
                user_id="user-999",
                user_profile=empty_profile,
                limit=10,
            )

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_recommend_content_with_category_filter(
        self, mock_db_session, mock_redis_client, sample_user_profile, sample_content_items
    ):
        """Test recommend_content with category filter."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_recommendations.return_value = [
                item for item in sample_content_items if item["category"] == "reviews"
            ]

            result = await recommend_content(
                user_id="user-001",
                user_profile=sample_user_profile,
                limit=10,
                category="reviews",
            )

            assert all(item["category"] == "reviews" for item in result)

    @pytest.mark.asyncio
    async def test_recommend_content_handles_db_error(
        self, mock_db_session, mock_redis_client, sample_user_profile
    ):
        """Test recommend_content handles database errors gracefully."""
        mock_redis_client.get.return_value = None

        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_recommendations.side_effect = Exception("Database connection failed")

            with pytest.raises(Exception, match="Database connection failed"):
                await recommend_content(
                    user_id="user-001",
                    user_profile=sample_user_profile,
                    limit=10,
                )

    @pytest.mark.asyncio
    async def test_recommend_content_returns_empty_list_when_no_recommendations(
        self, mock_db_session, mock_redis_client, sample_user_profile
    ):
        """Test recommend_content returns empty list when no recommendations found."""
        mock_redis_client.get.return_value = None

        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_recommendations.return_value = []

            result = await recommend_content(
                user_id="user-001",
                user_profile=sample_user_profile,
                limit=10,
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_recommend_content_includes_score(
        self, mock_db_session, mock_redis_client, sample_user_profile, sample_content_items
    ):
        """Test that recommended content includes relevance scores."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_recommendations.return_value = sample_content_items

            result = await recommend_content(
                user_id="user-001",
                user_profile=sample_user_profile,
                limit=10,
            )

            for item in result:
                assert "score" in item
                assert isinstance(item["score"], (int, float))

    @pytest.mark.asyncio
    async def test_recommend_content_deduplicates_content(
        self, mock_db_session, mock_redis_client, sample_user_profile, sample_content_items
    ):
        """Test that recommend_content does not return duplicate content."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            # Return items with duplicates
            duplicated_items = sample_content_items + [sample_content_items[0]]
            mock_repo.get_recommendations.return_value = duplicated_items

            result = await recommend_content(
                user_id="user-001",
                user_profile=sample_user_profile,
                limit=20,
            )

            ids = [item["id"] for item in result]
            assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_recommend_content_orders_by_relevance(
        self, mock_db_session, mock_redis_client, sample_user_profile, sample_content_items
    ):
        """Test that recommended content is ordered by relevance score."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_recommendations.return_value = sample_content_items

            result = await recommend_content(
                user_id="user-001",
                user_profile=sample_user_profile,
                limit=10,
            )

            scores = [item["score"] for item in result]
            assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Test search_content
# ---------------------------------------------------------------------------


class TestSearchContent:
    """Tests for the search_content function."""

    @pytest.mark.asyncio
    async def test_search_content_returns_results(
        self, mock_db_session, mock_redis_client, sample_content_items
    ):
        """Test that search_content returns search results."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search.return_value = sample_content_items

            result = await search_content(
                query="product review",
                limit=10,
            )

            assert result is not None
            assert isinstance(result, list)
            assert len(result) > 0
            mock_repo.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_content_with_query_string(
        self, mock_db_session, mock_redis_client, sample_content_items
    ):
        """Test search_content with a specific query string."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search.return_value = sample_content_items[:1]

            result = await search_content(
                query="Amazing Product Review",
                limit=10,
            )

            assert len(result) > 0
            mock_repo.search.assert_called_with(
                query="Amazing Product Review",
                limit=10,
                offset=0,
            )

    @pytest.mark.asyncio
    async def test_search_content_respects_limit_and_offset(
        self, mock_db_session, mock_redis_client, sample_content_items
    ):
        """Test that search_content respects limit and offset parameters."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search.return_value = sample_content_items[:2]

            result = await search_content(
                query="test",
                limit=2,
                offset=5,
            )

            assert len(result) <= 2
            mock_repo.search.assert_called_with(
                query="test",
                limit=2,
                offset=5,
            )

    @pytest.mark.asyncio
    async def test_search_content_empty_query(
        self, mock_db_session, mock_redis_client
    ):
        """Test search_content with an empty query string."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search.return_value = []

            result = await search_content(
                query="",
                limit=10,
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_search_content_no_results(
        self, mock_db_session, mock_redis_client
    ):
        """Test search_content when no results are found."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search.return_value = []

            result = await search_content(
                query="nonexistent content query",
                limit=10,
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_search_content_with_category_filter(
        self, mock_db_session, mock_redis_client, sample_content_items
    ):
        """Test search_content with category filter."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search.return_value = [
                item for item in sample_content_items if item["category"] == "reviews"
            ]

            result = await search_content(
                query="product",
                category="reviews",
                limit=10,
            )

            assert all(item["category"] == "reviews" for item in result)

    @pytest.mark.asyncio
    async def test_search_content_with_tags_filter(
        self, mock_db_session, mock_redis_client, sample_content_items
    ):
        """Test search_content with tags filter."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search.return_value = sample_content_items

            result = await search_content(
                query="product",
                tags=["tech"],
                limit=10,
            )

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_search_content_uses_cache(
        self, mock_db_session, mock_redis_client, sample_content_items
    ):
        """Test that search_content uses Redis cache."""
        mock_redis_client.get.return_value = '[{"id": "content-001", "title": "Cached Search"}]'

        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value

            result = await search_content(
                query="product review",
                limit=10,
            )

            mock_redis_client.get.assert_called()
            assert result is not None

    @pytest.mark.asyncio
    async def test_search_content_cache_miss_queries_db(
        self, mock_db_session, mock_redis_client, sample_content_items
    ):
        """Test that search_content queries the database on cache miss."""
        mock_redis_client.get.return_value = None

        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search.return_value = sample_content_items

            result = await search_content(
                query="product review",
                limit=10,
            )

            mock_repo.search.assert_called_once()
            assert len(result) == len(sample_content_items)

    @pytest.mark.asyncio
    async def test_search_content_stores_in_cache(
        self, mock_db_session, mock_redis_client, sample_content_items
    ):
        """Test that search_content stores results in cache."""
        mock_redis_client.get.return_value = None

        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search.return_value = sample_content_items

            await search_content(
                query="product review",
                limit=10,
            )

            mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_content_handles_db_error(
        self, mock_db_session, mock_redis_client
    ):
        """Test search_content handles database errors gracefully."""
        mock_redis_client.get.return_value = None

        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search.side_effect = Exception("Search index unavailable")

            with pytest.raises(Exception, match="Search index unavailable"):
                await search_content(
                    query="test query",
                    limit=10,
                )

    @pytest.mark.asyncio
    async def test_search_content_includes_relevance_score(
        self, mock_db_session, mock_redis_client, sample_content_items
    ):
        """Test that search results include relevance scores."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search.return_value = sample_content_items

            result = await search_content(
                query="product review",
                limit=10,
            )

            for item in result:
                assert "score" in item
                assert isinstance(item["score"], (int, float))

    @pytest.mark.asyncio
    async def test_search_content_orders_by_relevance(
        self, mock_db_session, mock_redis_client, sample_content_items
    ):
        """Test that search results are ordered by relevance."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search.return_value = sample_content_items

            result = await search_content(
                query="product review",
                limit=10,
            )

            scores = [item["score"] for item in result]
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_search_content_with_date_range(
        self, mock_db_session, mock_redis_client, sample_content_items
    ):
        """Test search_content with date range filter."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search.return_value = sample_content_items

            result = await search_content(
                query="product",
                date_from=datetime.now() - timedelta(days=7),
                date_to=datetime.now(),
                limit=10,
            )

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_search_content_with_author_filter(
        self, mock_db_session, mock_redis_client, sample_content_items
    ):
        """Test search_content with author filter."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search.return_value = [
                item for item in sample_content_items if item["author_id"] == "user-001"
            ]

            result = await search_content(
                query="product",
                author_id="user-001",
                limit=10,
            )

            assert all(item["author_id"] == "user-001" for item in result)


# ---------------------------------------------------------------------------
# Test get_trending_content
# ---------------------------------------------------------------------------


class TestGetTrendingContent:
    """Tests for the get_trending_content function."""

    @pytest.mark.asyncio
    async def test_get_trending_content_returns_trending(
        self, mock_db_session, mock_redis_client, sample_trending_data
    ):
        """Test that get_trending_content returns trending content."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_trending.return_value = sample_trending_data

            result = await get_trending_content(
                limit=10,
            )

            assert result is not None
            assert isinstance(result, list)
            assert len(result) > 0
            mock_repo.get_trending.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_trending_content_respects_limit(
        self, mock_db_session, mock_redis_client, sample_trending_data
    ):
        """Test that get_trending_content respects the limit parameter."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_trending.return_value = sample_trending_data[:2]

            result = await get_trending_content(
                limit=2,
            )

            assert len(result) <= 2

    @pytest.mark.asyncio
    async def test_get_trending_content_with_category(
        self, mock_db_session, mock_redis_client, sample_trending_data
    ):
        """Test get_trending_content with category filter."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_trending.return_value = [
                item for item in sample_trending_data if item["category"] == "reviews"
            ]

            result = await get_trending_content(
                category="reviews",
                limit=10,
            )

            assert all(item["category"] == "reviews" for item in result)

    @pytest.mark.asyncio
    async def test_get_trending_content_uses_cache(
        self, mock_db_session, mock_redis_client, sample_trending_data
    ):
        """Test that get_trending_content uses Redis cache."""
        mock_redis_client.get.return_value = '[{"content_id": "content-003", "trending_score": 95.5}]'

        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value

            result = await get_trending_content(
                limit=10,
            )

            mock_redis_client.get.assert_called()
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_trending_content_cache_miss_queries_db(
        self, mock_db_session, mock_redis_client, sample_trending_data
    ):
        """Test that get_trending_content queries the database on cache miss."""
        mock_redis_client.get.return_value = None

        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_trending.return_value = sample_trending_data

            result = await get_trending_content(
                limit=10,
            )

            mock_repo.get_trending.assert_called_once()
            assert len(result) == len(sample_trending_data)

    @pytest.mark.asyncio
    async def test_get_trending_content_stores_in_cache(
        self, mock_db_session, mock_redis_client, sample_trending_data
    ):
        """Test that get_trending_content stores results in cache."""
        mock_redis_client.get.return_value = None

        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_trending.return_value = sample_trending_data

            await get_trending_content(
                limit=10,
            )

            mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_trending_content_empty_result(
        self, mock_db_session, mock_redis_client
    ):
        """Test get_trending_content when no trending content exists."""
        mock_redis_client.get.return_value = None

        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_trending.return_value = []

            result = await get_trending_content(
                limit=10,
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_get_trending_content_includes_trending_score(
        self, mock_db_session, mock_redis_client, sample_trending_data
    ):
        """Test that trending content includes trending scores."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_trending.return_value = sample_trending_data

            result = await get_trending_content(
                limit=10,
            )

            for item in result:
                assert "trending_score" in item
                assert isinstance(item["trending_score"], (int, float))

    @pytest.mark.asyncio
    async def test_get_trending_content_includes_rank(
        self, mock_db_session, mock_redis_client, sample_trending_data
    ):
        """Test that trending content includes rank."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_trending.return_value = sample_trending_data

            result = await get_trending_content(
                limit=10,
            )

            for item in result:
                assert "rank" in item
                assert isinstance(item["rank"], int)

    @pytest.mark.asyncio
    async def test_get_trending_content_orders_by_trending_score(
        self, mock_db_session, mock_redis_client, sample_trending_data
    ):
        """Test that trending content is ordered by trending score descending."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_trending.return_value = sample_trending_data

            result = await get_trending_content(
                limit=10,
            )

            scores = [item["trending_score"] for item in result]
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_get_trending_content_handles_db_error(
        self, mock_db_session, mock_redis_client
    ):
        """Test get_trending_content handles database errors gracefully."""
        mock_redis_client.get.return_value = None

        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_trending.side_effect = Exception("Database connection failed")

            with pytest.raises(Exception, match="Database connection failed"):
                await get_trending_content(
                    limit=10,
                )

    @pytest.mark.asyncio
    async def test_get_trending_content_with_time_window(
        self, mock_db_session, mock_redis_client, sample_trending_data
    ):
        """Test get_trending_content with time window parameter."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_trending.return_value = sample_trending_data

            result = await get_trending_content(
                limit=10,
                time_window_hours=24,
            )

            assert isinstance(result, list)
            mock_repo.get_trending.assert_called_with(
                limit=10,
                category=None,
                time_window_hours=24,
            )

    @pytest.mark.asyncio
    async def test_get_trending_content_includes_velocity(
        self, mock_db_session, mock_redis_client, sample_trending_data
    ):
        """Test that trending content includes velocity metric."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_trending.return_value = sample_trending_data

            result = await get_trending_content(
                limit=10,
            )

            for item in result:
                assert "velocity" in item
                assert isinstance(item["velocity"], (int, float))

    @pytest.mark.asyncio
    async def test_get_trending_content_includes_content_id(
        self, mock_db_session, mock_redis_client, sample_trending_data
    ):
        """Test that trending content includes content_id."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_trending.return_value = sample_trending_data

            result = await get_trending_content(
                limit=10,
            )

            for item in result:
                assert "content_id" in item
                assert item["content_id"] is not None

    @pytest.mark.asyncio
    async def test_get_trending_content_includes_title(
        self, mock_db_session, mock_redis_client, sample_trending_data
    ):
        """Test that trending content includes title."""
        with patch(
            "src.ugc_marketplace.agents.content_discovery.get_db_session",
            return_value=mock_db_session,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.get_redis_client",
            return_value=mock_redis_client,
        ), patch(
            "src.ugc_marketplace.agents.content_discovery.ContentRepository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_trending.return_value = sample_trending_data

            result = await get_trending_content(
                limit=10,
            )

            for item in result:
                assert "title" in item
                assert isinstance(item["title"], str)
                assert len(item["title"]) > 0