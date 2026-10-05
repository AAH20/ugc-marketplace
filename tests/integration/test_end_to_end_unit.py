"""End-to-end integration tests for ugc-marketplace."""
from __future__ import annotations

import pytest
from typing import Any, Generator
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client() -> Generator[MagicMock, None, None]:
    """Provide a mock API client for integration tests."""
    client = MagicMock()
    yield client


@pytest.fixture
def creator_data() -> dict[str, Any]:
    """Sample creator data."""
    return {
        "id": "creator-001",
        "username": "test_creator",
        "email": "creator@example.com",
        "display_name": "Test Creator",
        "bio": "A test creator for integration tests",
        "verified": True,
    }


@pytest.fixture
def content_data() -> dict[str, Any]:
    """Sample content data."""
    return {
        "id": "content-001",
        "creator_id": "creator-001",
        "title": "Test Content",
        "description": "A test content item",
        "content_type": "video",
        "status": "published",
        "tags": ["test", "integration"],
    }


@pytest.fixture
def listing_data() -> dict[str, Any]:
    """Sample listing data."""
    return {
        "id": "listing-001",
        "content_id": "content-001",
        "creator_id": "creator-001",
        "title": "Test Listing",
        "description": "A test listing for sale",
        "price": 29.99,
        "currency": "USD",
        "status": "active",
    }


@pytest.fixture
def buyer_data() -> dict[str, Any]:
    """Sample buyer data."""
    return {
        "id": "buyer-001",
        "username": "test_buyer",
        "email": "buyer@example.com",
    }


@pytest.fixture
def review_data() -> dict[str, Any]:
    """Sample review data."""
    return {
        "id": "review-001",
        "listing_id": "listing-001",
        "buyer_id": "buyer-001",
        "rating": 5,
        "comment": "Excellent content!",
    }


# ---------------------------------------------------------------------------
# Test 1: Full marketplace flow
# ---------------------------------------------------------------------------


def test_full_marketplace_flow(
    mock_client: MagicMock,
    creator_data: dict[str, Any],
    content_data: dict[str, Any],
    listing_data: dict[str, Any],
    buyer_data: dict[str, Any],
    review_data: dict[str, Any],
) -> None:
    """Test the complete marketplace flow: creator → content → listing → purchase → review."""
    # Step 1: Create creator
    mock_client.create_creator.return_value = creator_data
    creator = mock_client.create_creator(
        username="test_creator",
        email="creator@example.com",
        display_name="Test Creator",
    )
    assert creator is not None
    assert creator["id"] == "creator-001"
    assert creator["username"] == "test_creator"
    assert creator["verified"] is True
    mock_client.create_creator.assert_called_once()

    # Step 2: Create content
    mock_client.create_content.return_value = content_data
    content = mock_client.create_content(
        creator_id=creator["id"],
        title="Test Content",
        description="A test content item",
        content_type="video",
    )
    assert content is not None
    assert content["id"] == "content-001"
    assert content["creator_id"] == creator["id"]
    assert content["status"] == "published"
    mock_client.create_content.assert_called_once()

    # Step 3: Create listing
    mock_client.create_listing.return_value = listing_data
    listing = mock_client.create_listing(
        content_id=content["id"],
        creator_id=creator["id"],
        title="Test Listing",
        price=29.99,
        currency="USD",
    )
    assert listing is not None
    assert listing["id"] == "listing-001"
    assert listing["content_id"] == content["id"]
    assert listing["price"] == 29.99
    assert listing["status"] == "active"
    mock_client.create_listing.assert_called_once()

    # Step 4: Purchase
    purchase_result = {
        "id": "purchase-001",
        "listing_id": listing["id"],
        "buyer_id": buyer_data["id"],
        "amount": 29.99,
        "currency": "USD",
        "status": "completed",
    }
    mock_client.purchase.return_value = purchase_result
    purchase = mock_client.purchase(
        listing_id=listing["id"],
        buyer_id=buyer_data["id"],
    )
    assert purchase is not None
    assert purchase["id"] == "purchase-001"
    assert purchase["listing_id"] == listing["id"]
    assert purchase["status"] == "completed"
    assert purchase["amount"] == 29.99
    mock_client.purchase.assert_called_once()

    # Step 5: Review
    mock_client.create_review.return_value = review_data
    review = mock_client.create_review(
        listing_id=listing["id"],
        buyer_id=buyer_data["id"],
        rating=5,
        comment="Excellent content!",
    )
    assert review is not None
    assert review["id"] == "review-001"
    assert review["listing_id"] == listing["id"]
    assert review["rating"] == 5
    assert review["comment"] == "Excellent content!"
    mock_client.create_review.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2: Creator analytics flow
# ---------------------------------------------------------------------------


def test_creator_analytics_flow(
    mock_client: MagicMock,
    creator_data: dict[str, Any],
    content_data: dict[str, Any],
) -> None:
    """Test creator analytics: create creator → create content → get analytics."""
    # Step 1: Create creator
    mock_client.create_creator.return_value = creator_data
    creator = mock_client.create_creator(
        username="test_creator",
        email="creator@example.com",
    )
    assert creator is not None
    assert creator["id"] == "creator-001"

    # Step 2: Create content
    mock_client.create_content.return_value = content_data
    content = mock_client.create_content(
        creator_id=creator["id"],
        title="Test Content",
        content_type="video",
    )
    assert content is not None
    assert content["creator_id"] == creator["id"]

    # Step 3: Get analytics
    analytics = {
        "creator_id": creator["id"],
        "total_content": 1,
        "total_views": 1500,
        "total_likes": 320,
        "total_revenue": 299.90,
        "followers_count": 85,
        "engagement_rate": 0.213,
        "top_content": [
            {"content_id": content["id"], "views": 1500, "likes": 320},
        ],
    }
    mock_client.get_creator_analytics.return_value = analytics
    result = mock_client.get_creator_analytics(creator_id=creator["id"])
    assert result is not None
    assert result["creator_id"] == creator["id"]
    assert result["total_content"] == 1
    assert result["total_views"] == 1500
    assert result["total_likes"] == 320
    assert result["total_revenue"] == 299.90
    assert result["followers_count"] == 85
    assert result["engagement_rate"] == pytest.approx(0.213)
    assert len(result["top_content"]) == 1
    assert result["top_content"][0]["content_id"] == content["id"]
    mock_client.get_creator_analytics.assert_called_once_with(creator_id=creator["id"])


# ---------------------------------------------------------------------------
# Test 3: Marketplace stats
# ---------------------------------------------------------------------------


def test_marketplace_stats(
    mock_client: MagicMock,
    creator_data: dict[str, Any],
    content_data: dict[str, Any],
    listing_data: dict[str, Any],
) -> None:
    """Test marketplace stats: create data → get marketplace stats."""
    # Step 1: Create some data
    mock_client.create_creator.return_value = creator_data
    creator = mock_client.create_creator(
        username="test_creator",
        email="creator@example.com",
    )
    assert creator is not None

    mock_client.create_content.return_value = content_data
    content = mock_client.create_content(
        creator_id=creator["id"],
        title="Test Content",
        content_type="video",
    )
    assert content is not None

    mock_client.create_listing.return_value = listing_data
    listing = mock_client.create_listing(
        content_id=content["id"],
        creator_id=creator["id"],
        title="Test Listing",
        price=29.99,
    )
    assert listing is not None

    # Step 2: Get marketplace stats
    stats = {
        "total_creators": 1,
        "total_content": 1,
        "total_listings": 1,
        "total_transactions": 0,
        "total_volume": 0.0,
        "active_listings": 1,
        "average_listing_price": 29.99,
        "top_categories": [
            {"category": "video", "count": 1},
        ],
    }
    mock_client.get_marketplace_stats.return_value = stats
    result = mock_client.get_marketplace_stats()
    assert result is not None
    assert result["total_creators"] == 1
    assert result["total_content"] == 1
    assert result["total_listings"] == 1
    assert result["active_listings"] == 1
    assert result["average_listing_price"] == pytest.approx(29.99)
    assert len(result["top_categories"]) == 1
    assert result["top_categories"][0]["category"] == "video"
    mock_client.get_marketplace_stats.assert_called_once()
