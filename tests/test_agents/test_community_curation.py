"""Tests for community curation agent functions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ugc_marketplace.agents.community_curation import (
    curate_community_content,
    feature_content,
    get_curated_feed,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db():
    """Provide a mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def mock_content_item():
    """Provide a sample content item."""
    return {
        "id": "content-001",
        "creator_id": "user-123",
        "title": "Amazing Product Review",
        "body": "This product exceeded my expectations in every way.",
        "content_type": "review",
        "status": "pending",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=2),
        "updated_at": datetime.now(timezone.utc),
        "upvotes": 42,
        "downvotes": 3,
        "flags": 0,
        "tags": ["review", "electronics"],
        "media_urls": ["https://example.com/image1.jpg"],
    }


@pytest.fixture
def mock_curated_item():
    """Provide a sample curated/featured content item."""
    return {
        "id": "content-002",
        "creator_id": "user-456",
        "title": "Featured: Best Purchase of 2026",
        "body": "An in-depth look at why this is the best purchase I've made.",
        "content_type": "article",
        "status": "curated",
        "created_at": datetime.now(timezone.utc) - timedelta(days=1),
        "updated_at": datetime.now(timezone.utc),
        "upvotes": 150,
        "downvotes": 5,
        "flags": 0,
        "tags": ["featured", "editorial"],
        "media_urls": ["https://example.com/featured.jpg"],
        "curated_at": datetime.now(timezone.utc),
        "curated_by": "agent-community-curation",
        "curation_score": 0.95,
    }


@pytest.fixture
def mock_featured_item():
    """Provide a sample featured content item."""
    return {
        "id": "content-003",
        "creator_id": "user-789",
        "title": "Community Spotlight: Top Creator",
        "body": "Celebrating our top contributor this month.",
        "content_type": "spotlight",
        "status": "featured",
        "created_at": datetime.now(timezone.utc) - timedelta(days=3),
        "updated_at": datetime.now(timezone.utc),
        "upvotes": 500,
        "downvotes": 10,
        "flags": 0,
        "tags": ["spotlight", "community"],
        "media_urls": ["https://example.com/spotlight.jpg"],
        "featured_at": datetime.now(timezone.utc),
        "featured_by": "agent-community-curation",
        "feature_reason": "Exceptional community contribution",
    }


@pytest.fixture
def mock_llm_response():
    """Provide a mock LLM response for curation decisions."""
    return {
        "should_curate": True,
        "curation_score": 0.92,
        "reasoning": "High-quality original content with strong community engagement",
        "tags": ["high-quality", "original", "engaging"],
    }


# ---------------------------------------------------------------------------
# Tests for curate_community_content
# ---------------------------------------------------------------------------


class TestCurateCommunityContent:
    """Tests for the curate_community_content function."""

    @pytest.mark.asyncio
    async def test_curate_community_content_success(
        self, mock_db, mock_content_item, mock_llm_response
    ):
        """Test successful curation of community content."""
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_content_item)
        )

        with patch(
            "ugc_marketplace.agents.community_curation.llm_client"
        ) as mock_llm:
            mock_llm.generate = AsyncMock(return_value=mock_llm_response)

            result = await curate_community_content(
                db=mock_db,
                content_id="content-001",
            )

        assert result is not None
        assert result["id"] == "content-001"
        assert result["status"] == "curated"
        assert result["curation_score"] == 0.92
        assert "curated_at" in result
        assert result["curated_by"] == "agent-community-curation"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_curate_community_content_not_found(self, mock_db):
        """Test curation when content does not exist."""
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )

        result = await curate_community_content(
            db=mock_db,
            content_id="nonexistent-id",
        )

        assert result is None
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_curate_community_content_already_curated(
        self, mock_db, mock_curated_item
    ):
        """Test curation of already curated content is idempotent."""
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_curated_item)
        )

        result = await curate_community_content(
            db=mock_db,
            content_id="content-002",
        )

        assert result is not None
        assert result["status"] == "curated"
        # Should not re-curate
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_curate_community_content_low_quality(
        self, mock_db, mock_content_item
    ):
        """Test that low-quality content is not curated."""
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_content_item)
        )

        low_quality_response = {
            "should_curate": False,
            "curation_score": 0.15,
            "reasoning": "Low quality content with minimal engagement",
            "tags": ["low-quality"],
        }

        with patch(
            "ugc_marketplace.agents.community_curation.llm_client"
        ) as mock_llm:
            mock_llm.generate = AsyncMock(return_value=low_quality_response)

            result = await curate_community_content(
                db=mock_db,
                content_id="content-001",
            )

        assert result is not None
        assert result["status"] == "pending"
        assert result["curation_score"] == 0.15
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_curate_community_content_flagged_content(
        self, mock_db, mock_content_item
    ):
        """Test that flagged content is rejected during curation."""
        flagged_item = {**mock_content_item, "flags": 5}
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=flagged_item)
        )

        result = await curate_community_content(
            db=mock_db,
            content_id="content-001",
        )

        assert result is not None
        assert result["status"] == "rejected"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_curate_community_content_db_error(self, mock_db):
        """Test handling of database errors during curation."""
        mock_db.execute.side_effect = Exception("Database connection lost")

        with pytest.raises(Exception, match="Database connection lost"):
            await curate_community_content(
                db=mock_db,
                content_id="content-001",
            )

        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_curate_community_content_with_custom_agent_id(
        self, mock_db, mock_content_item, mock_llm_response
    ):
        """Test curation with a custom agent identifier."""
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_content_item)
        )

        with patch(
            "ugc_marketplace.agents.community_curation.llm_client"
        ) as mock_llm:
            mock_llm.generate = AsyncMock(return_value=mock_llm_response)

            result = await curate_community_content(
                db=mock_db,
                content_id="content-001",
                agent_id="custom-agent-42",
            )

        assert result is not None
        assert result["curated_by"] == "custom-agent-42"

    @pytest.mark.asyncio
    async def test_curate_community_content_updates_tags(
        self, mock_db, mock_content_item, mock_llm_response
    ):
        """Test that curation updates content tags."""
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_content_item)
        )

        with patch(
            "ugc_marketplace.agents.community_curation.llm_client"
        ) as mock_llm:
            mock_llm.generate = AsyncMock(return_value=mock_llm_response)

            result = await curate_community_content(
                db=mock_db,
                content_id="content-001",
            )

        assert result is not None
        assert "high-quality" in result["tags"]
        assert "original" in result["tags"]
        assert "engaging" in result["tags"]


# ---------------------------------------------------------------------------
# Tests for feature_content
# ---------------------------------------------------------------------------


class TestFeatureContent:
    """Tests for the feature_content function."""

    @pytest.mark.asyncio
    async def test_feature_content_success(
        self, mock_db, mock_curated_item
    ):
        """Test successful featuring of curated content."""
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_curated_item)
        )

        result = await feature_content(
            db=mock_db,
            content_id="content-002",
            reason="Exceptional quality and engagement",
        )

        assert result is not None
        assert result["id"] == "content-002"
        assert result["status"] == "featured"
        assert result["feature_reason"] == "Exceptional quality and engagement"
        assert "featured_at" in result
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_feature_content_not_found(self, mock_db):
        """Test featuring when content does not exist."""
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )

        result = await feature_content(
            db=mock_db,
            content_id="nonexistent-id",
            reason="Test reason",
        )

        assert result is None
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_feature_content_not_curated(
        self, mock_db, mock_content_item
    ):
        """Test that non-curated content cannot be featured."""
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_content_item)
        )

        result = await feature_content(
            db=mock_db,
            content_id="content-001",
            reason="Attempt to feature uncurated content",
        )

        assert result is None
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_feature_content_already_featured(
        self, mock_db, mock_featured_item
    ):
        """Test that already featured content is handled gracefully."""
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_featured_item)
        )

        result = await feature_content(
            db=mock_db,
            content_id="content-003",
            reason="Re-featuring",
        )

        assert result is not None
        assert result["status"] == "featured"
        # Should not duplicate feature
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_feature_content_with_duration(
        self, mock_db, mock_curated_item
    ):
        """Test featuring content with a specific duration."""
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_curated_item)
        )

        result = await feature_content(
            db=mock_db,
            content_id="content-002",
            reason="Weekly featured content",
            duration_days=7,
        )

        assert result is not None
        assert result["status"] == "featured"
        assert "feature_expires_at" in result
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_feature_content_db_error(self, mock_db):
        """Test handling of database errors during featuring."""
        mock_db.execute.side_effect = Exception("Database timeout")

        with pytest.raises(Exception, match="Database timeout"):
            await feature_content(
                db=mock_db,
                content_id="content-002",
                reason="Test",
            )

        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_feature_content_with_custom_agent_id(
        self, mock_db, mock_curated_item
    ):
        """Test featuring with a custom agent identifier."""
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=mock_curated_item)
        )

        result = await feature_content(
            db=mock_db,
            content_id="content-002",
            reason="Custom agent feature",
            agent_id="custom-featurer-99",
        )

        assert result is not None
        assert result["featured_by"] == "custom-featurer-99"


# ---------------------------------------------------------------------------
# Tests for get_curated_feed
# ---------------------------------------------------------------------------


class TestGetCuratedFeed:
    """Tests for the get_curated_feed function."""

    @pytest.mark.asyncio
    async def test_get_curated_feed_success(
        self, mock_db, mock_curated_item, mock_featured_item
    ):
        """Test successful retrieval of curated feed."""
        curated_items = [mock_curated_item, mock_featured_item]
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(
                return_value=MagicMock(
                    all=MagicMock(return_value=curated_items)
                )
            )
        )

        result = await get_curated_feed(db=mock_db)

        assert result is not None
        assert len(result) == 2
        assert result[0]["id"] == "content-002"
        assert result[1]["id"] == "content-003"
        assert all(item["status"] in ("curated", "featured") for item in result)

    @pytest.mark.asyncio
    async def test_get_curated_feed_empty(self, mock_db):
        """Test retrieval when no curated content exists."""
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(
                return_value=MagicMock(all=MagicMock(return_value=[]))
            )
        )

        result = await get_curated_feed(db=mock_db)

        assert result is not None
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_curated_feed_with_limit(self, mock_db, mock_curated_item):
        """Test retrieval with a result limit."""
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(
                return_value=MagicMock(
                    all=MagicMock(return_value=[mock_curated_item])
                )
            )
        )

        result = await get_curated_feed(db=mock_db, limit=10)

        assert result is not None
        assert len(result) <= 10

    @pytest.mark.asyncio
    async def test_get_curated_feed_with_offset(self, mock_db, mock_curated_item):
        """Test retrieval with pagination offset."""
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(
                return_value=MagicMock(
                    all=MagicMock(return_value=[mock_curated_item])
                )
            )
        )

        result = await get_curated_feed(db=mock_db, offset=20, limit=10)

        assert result is not None
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_curated_feed_sorted_by_date(
        self, mock_db, mock_curated_item, mock_featured_item
    ):
        """Test that feed is sorted by curation date descending."""
        # featured_item is older than curated_item
        items = [mock_featured_item, mock_curated_item]
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(
                return_value=MagicMock(all=MagicMock(return_value=items))
            )
        )

        result = await get_curated_feed(db=mock_db)

        assert result is not None
        # Most recently curated should be first
        assert result[0]["curated_at"] >= result[1]["curated_at"]

    @pytest.mark.asyncio
    async def test_get_curated_feed_db_error(self, mock_db):
        """Test handling of database errors during feed retrieval."""
        mock_db.execute.side_effect = Exception("Query failed")

        with pytest.raises(Exception, match="Query failed"):
            await get_curated_feed(db=mock_db)

    @pytest.mark.asyncio
    async def test_get_curated_feed_with_content_type_filter(
        self, mock_db, mock_curated_item
    ):
        """Test retrieval filtered by content type."""
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(
                return_value=MagicMock(
                    all=MagicMock(return_value=[mock_curated_item])
                )
            )
        )

        result = await get_curated_feed(
            db=mock_db, content_type="article"
        )

        assert result is not None
        assert len(result) == 1
        assert result[0]["content_type"] == "article"

    @pytest.mark.asyncio
    async def test_get_curated_feed_includes_creator_info(
        self, mock_db, mock_curated_item
    ):
        """Test that feed items include creator information."""
        item_with_creator = {
            **mock_curated_item,
            "creator": {
                "id": "user-456",
                "username": "testuser",
                "display_name": "Test User",
            },
        }
        mock_db.execute.return_value = MagicMock(
            scalars=MagicMock(
                return_value=MagicMock(
                    all=MagicMock(return_value=[item_with_creator])
                )
            )
        )

        result = await get_curated_feed(db=mock_db)

        assert result is not None
        assert "creator" in result[0]
        assert result[0]["creator"]["username"] == "testuser"
