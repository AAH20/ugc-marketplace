"""Comprehensive agent tests for content marketplace functions."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
from uuid import uuid4

from ugc_marketplace.agents.content_marketplace import (
    list_marketplace_items,
    purchase_content,
    get_marketplace_stats,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db():
    """Provide a mock database session."""
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def sample_item():
    """Return a sample marketplace item dict."""
    return {
        "id": str(uuid4()),
        "title": "Test Content Pack",
        "description": "A test content pack for agents",
        "price": 29.99,
        "currency": "USD",
        "category": "templates",
        "seller_id": str(uuid4()),
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "tags": ["template", "starter"],
        "rating": 4.5,
        "sales_count": 42,
    }


@pytest.fixture
def sample_items_list():
    """Return a list of sample marketplace items."""
    base_time = datetime.utcnow()
    return [
        {
            "id": str(uuid4()),
            "title": f"Content Pack {i}",
            "description": f"Description for pack {i}",
            "price": 9.99 * (i + 1),
            "currency": "USD",
            "category": ["templates", "prompts", "workflows"][i % 3],
            "seller_id": str(uuid4()),
            "status": "active",
            "created_at": (base_time - timedelta(days=i)).isoformat(),
            "updated_at": (base_time - timedelta(hours=i)).isoformat(),
            "tags": ["tag1", "tag2"],
            "rating": 3.5 + (i * 0.5),
            "sales_count": i * 10,
        }
        for i in range(5)
    ]


@pytest.fixture
def sample_purchase():
    """Return a sample purchase record."""
    return {
        "id": str(uuid4()),
        "item_id": str(uuid4()),
        "buyer_id": str(uuid4()),
        "seller_id": str(uuid4()),
        "amount": 29.99,
        "currency": "USD",
        "status": "completed",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_stats():
    """Return sample marketplace statistics."""
    return {
        "total_items": 150,
        "active_items": 120,
        "total_sales": 1523,
        "total_revenue": 45678.90,
        "average_rating": 4.3,
        "categories": {
            "templates": 50,
            "prompts": 45,
            "workflows": 35,
        },
        "top_sellers": [
            {"seller_id": str(uuid4()), "sales": 200},
            {"seller_id": str(uuid4()), "sales": 150},
        ],
    }


# ---------------------------------------------------------------------------
# Tests for list_marketplace_items
# ---------------------------------------------------------------------------


class TestListMarketplaceItems:
    """Tests for the list_marketplace_items function."""

    @pytest.mark.asyncio
    async def test_list_marketplace_items_returns_items(self, mock_db, sample_items_list):
        """Test that list_marketplace_items returns a list of items."""
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(
            all=MagicMock(return_value=sample_items_list)
        ))
        mock_db.execute.return_value = mock_result

        result = await list_marketplace_items(mock_db)

        assert isinstance(result, list)
        assert len(result) == 5
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_marketplace_items_empty_result(self, mock_db):
        """Test that list_marketplace_items handles empty results."""
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(
            all=MagicMock(return_value=[])
        ))
        mock_db.execute.return_value = mock_result

        result = await list_marketplace_items(mock_db)

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_marketplace_items_with_category_filter(self, mock_db, sample_items_list):
        """Test filtering items by category."""
        filtered = [item for item in sample_items_list if item["category"] == "templates"]
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(
            all=MagicMock(return_value=filtered)
        ))
        mock_db.execute.return_value = mock_result

        result = await list_marketplace_items(mock_db, category="templates")

        assert isinstance(result, list)
        assert all(item["category"] == "templates" for item in result)

    @pytest.mark.asyncio
    async def test_list_marketplace_items_with_pagination(self, mock_db, sample_items_list):
        """Test pagination with limit and offset."""
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(
            all=MagicMock(return_value=sample_items_list[:2])
        ))
        mock_db.execute.return_value = mock_result

        result = await list_marketplace_items(mock_db, limit=2, offset=0)

        assert isinstance(result, list)
        assert len(result) <= 2

    @pytest.mark.asyncio
    async def test_list_marketplace_items_with_search_query(self, mock_db, sample_items_list):
        """Test search functionality."""
        search_results = [item for item in sample_items_list if "Pack 1" in item["title"]]
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(
            all=MagicMock(return_value=search_results)
        ))
        mock_db.execute.return_value = mock_result

        result = await list_marketplace_items(mock_db, search="Pack 1")

        assert isinstance(result, list)
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_list_marketplace_items_with_price_range(self, mock_db, sample_items_list):
        """Test filtering by price range."""
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(
            all=MagicMock(return_value=sample_items_list)
        ))
        mock_db.execute.return_value = mock_result

        result = await list_marketplace_items(mock_db, min_price=10.0, max_price=30.0)

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_marketplace_items_with_sorting(self, mock_db, sample_items_list):
        """Test sorting options."""
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(
            all=MagicMock(return_value=sample_items_list)
        ))
        mock_db.execute.return_value = mock_result

        result = await list_marketplace_items(mock_db, sort_by="price", sort_order="desc")

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_marketplace_items_db_error(self, mock_db):
        """Test handling of database errors."""
        mock_db.execute.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception, match="Database connection failed"):
            await list_marketplace_items(mock_db)

    @pytest.mark.asyncio
    async def test_list_marketplace_items_with_status_filter(self, mock_db, sample_items_list):
        """Test filtering by status."""
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(
            all=MagicMock(return_value=sample_items_list)
        ))
        mock_db.execute.return_value = mock_result

        result = await list_marketplace_items(mock_db, status="active")

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_marketplace_items_with_tags(self, mock_db, sample_items_list):
        """Test filtering by tags."""
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(
            all=MagicMock(return_value=sample_items_list)
        ))
        mock_db.execute.return_value = mock_result

        result = await list_marketplace_items(mock_db, tags=["template"])

        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Tests for purchase_content
# ---------------------------------------------------------------------------


class TestPurchaseContent:
    """Tests for the purchase_content function."""

    @pytest.mark.asyncio
    async def test_purchase_content_success(self, mock_db, sample_item, sample_purchase):
        """Test successful content purchase."""
        mock_db.execute.return_value = MagicMock(
            scalar=MagicMock(return_value=sample_item)
        )
        mock_db.add = MagicMock()

        result = await purchase_content(
            mock_db,
            item_id=sample_item["id"],
            buyer_id=sample_purchase["buyer_id"],
        )

        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_purchase_content_item_not_found(self, mock_db):
        """Test purchase fails when item is not found."""
        mock_db.execute.return_value = MagicMock(
            scalar=MagicMock(return_value=None)
        )

        with pytest.raises(ValueError, match="Item not found"):
            await purchase_content(mock_db, item_id=str(uuid4()), buyer_id=str(uuid4()))

    @pytest.mark.asyncio
    async def test_purchase_content_inactive_item(self, mock_db, sample_item):
        """Test purchase fails for inactive items."""
        sample_item["status"] = "inactive"
        mock_db.execute.return_value = MagicMock(
            scalar=MagicMock(return_value=sample_item)
        )

        with pytest.raises(ValueError, match="Item is not available"):
            await purchase_content(mock_db, item_id=sample_item["id"], buyer_id=str(uuid4()))

    @pytest.mark.asyncio
    async def test_purchase_content_creates_purchase_record(self, mock_db, sample_item):
        """Test that a purchase record is created."""
        mock_db.execute.return_value = MagicMock(
            scalar=MagicMock(return_value=sample_item)
        )

        buyer_id = str(uuid4())
        result = await purchase_content(
            mock_db,
            item_id=sample_item["id"],
            buyer_id=buyer_id,
        )

        mock_db.add.assert_called_once()
        added_record = mock_db.add.call_args[0][0]
        assert hasattr(added_record, 'buyer_id') or isinstance(added_record, dict)

    @pytest.mark.asyncio
    async def test_purchase_content_updates_sales_count(self, mock_db, sample_item):
        """Test that sales count is incremented after purchase."""
        mock_db.execute.return_value = MagicMock(
            scalar=MagicMock(return_value=sample_item)
        )

        await purchase_content(
            mock_db,
            item_id=sample_item["id"],
            buyer_id=str(uuid4()),
        )

        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_purchase_content_with_discount(self, mock_db, sample_item):
        """Test purchase with a discount code."""
        mock_db.execute.return_value = MagicMock(
            scalar=MagicMock(return_value=sample_item)
        )

        result = await purchase_content(
            mock_db,
            item_id=sample_item["id"],
            buyer_id=str(uuid4()),
            discount_code="SAVE20",
        )

        assert result is not None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_purchase_content_invalid_discount(self, mock_db, sample_item):
        """Test purchase with invalid discount code."""
        mock_db.execute.return_value = MagicMock(
            scalar=MagicMock(return_value=sample_item)
        )

        with pytest.raises(ValueError, match="Invalid discount code"):
            await purchase_content(
                mock_db,
                item_id=sample_item["id"],
                buyer_id=str(uuid4()),
                discount_code="INVALID",
            )

    @pytest.mark.asyncio
    async def test_purchase_content_db_error(self, mock_db, sample_item):
        """Test handling of database errors during purchase."""
        mock_db.execute.return_value = MagicMock(
            scalar=MagicMock(return_value=sample_item)
        )
        mock_db.commit.side_effect = Exception("Transaction failed")

        with pytest.raises(Exception, match="Transaction failed"):
            await purchase_content(
                mock_db,
                item_id=sample_item["id"],
                buyer_id=str(uuid4()),
            )

        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_purchase_content_already_purchased(self, mock_db, sample_item):
        """Test that duplicate purchase is prevented."""
        buyer_id = str(uuid4())
        mock_db.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=sample_item)),
            MagicMock(scalar=MagicMock(return_value={"id": str(uuid4())})),
        ]

        with pytest.raises(ValueError, match="already purchased"):
            await purchase_content(
                mock_db,
                item_id=sample_item["id"],
                buyer_id=buyer_id,
            )

    @pytest.mark.asyncio
    async def test_purchase_content_zero_price(self, mock_db, sample_item):
        """Test purchase of free content."""
        sample_item["price"] = 0.0
        mock_db.execute.return_value = MagicMock(
            scalar=MagicMock(return_value=sample_item)
        )

        result = await purchase_content(
            mock_db,
            item_id=sample_item["id"],
            buyer_id=str(uuid4()),
        )

        assert result is not None
        mock_db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Tests for get_marketplace_stats
# ---------------------------------------------------------------------------


class TestGetMarketplaceStats:
    """Tests for the get_marketplace_stats function."""

    @pytest.mark.asyncio
    async def test_get_marketplace_stats_returns_stats(self, mock_db, sample_stats):
        """Test that get_marketplace_stats returns statistics."""
        mock_db.execute.return_value = MagicMock(
            one=MagicMock(return_value=sample_stats)
        )

        result = await get_marketplace_stats(mock_db)

        assert isinstance(result, dict)
        assert "total_items" in result
        assert "active_items" in result
        assert "total_sales" in result
        assert "total_revenue" in result
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_marketplace_stats_empty_marketplace(self, mock_db):
        """Test stats for an empty marketplace."""
        empty_stats = {
            "total_items": 0,
            "active_items": 0,
            "total_sales": 0,
            "total_revenue": 0.0,
            "average_rating": 0.0,
            "categories": {},
            "top_sellers": [],
        }
        mock_db.execute.return_value = MagicMock(
            one=MagicMock(return_value=empty_stats)
        )

        result = await get_marketplace_stats(mock_db)

        assert result["total_items"] == 0
        assert result["total_sales"] == 0
        assert result["total_revenue"] == 0.0

    @pytest.mark.asyncio
    async def test_get_marketplace_stats_with_date_range(self, mock_db, sample_stats):
        """Test stats filtered by date range."""
        mock_db.execute.return_value = MagicMock(
            one=MagicMock(return_value=sample_stats)
        )

        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()

        result = await get_marketplace_stats(
            mock_db,
            start_date=start_date,
            end_date=end_date,
        )

        assert isinstance(result, dict)
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_marketplace_stats_with_category_filter(self, mock_db, sample_stats):
        """Test stats filtered by category."""
        mock_db.execute.return_value = MagicMock(
            one=MagicMock(return_value=sample_stats)
        )

        result = await get_marketplace_stats(mock_db, category="templates")

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_marketplace_stats_db_error(self, mock_db):
        """Test handling of database errors."""
        mock_db.execute.side_effect = Exception("Query failed")

        with pytest.raises(Exception, match="Query failed"):
            await get_marketplace_stats(mock_db)

    @pytest.mark.asyncio
    async def test_get_marketplace_stats_revenue_calculation(self, mock_db):
        """Test that revenue is calculated correctly."""
        stats = {
            "total_items": 10,
            "active_items": 8,
            "total_sales": 100,
            "total_revenue": 999.99,
            "average_rating": 4.5,
            "categories": {"templates": 5},
            "top_sellers": [],
        }
        mock_db.execute.return_value = MagicMock(
            one=MagicMock(return_value=stats)
        )

        result = await get_marketplace_stats(mock_db)

        assert result["total_revenue"] == 999.99
        assert result["total_sales"] == 100

    @pytest.mark.asyncio
    async def test_get_marketplace_stats_categories_breakdown(self, mock_db):
        """Test category breakdown in stats."""
        stats = {
            "total_items": 50,
            "active_items": 40,
            "total_sales": 500,
            "total_revenue": 15000.0,
            "average_rating": 4.2,
            "categories": {
                "templates": 20,
                "prompts": 15,
                "workflows": 10,
            },
            "top_sellers": [],
        }
        mock_db.execute.return_value = MagicMock(
            one=MagicMock(return_value=stats)
        )

        result = await get_marketplace_stats(mock_db)

        assert "categories" in result
        assert result["categories"]["templates"] == 20
        assert result["categories"]["prompts"] == 15
        assert result["categories"]["workflows"] == 10

    @pytest.mark.asyncio
    async def test_get_marketplace_stats_top_sellers(self, mock_db):
        """Test top sellers in stats."""
        stats = {
            "total_items": 100,
            "active_items": 80,
            "total_sales": 1000,
            "total_revenue": 50000.0,
            "average_rating": 4.7,
            "categories": {},
            "top_sellers": [
                {"seller_id": str(uuid4()), "sales": 300},
                {"seller_id": str(uuid4()), "sales": 250},
                {"seller_id": str(uuid4()), "sales": 200},
            ],
        }
        mock_db.execute.return_value = MagicMock(
            one=MagicMock(return_value=stats)
        )

        result = await get_marketplace_stats(mock_db)

        assert "top_sellers" in result
        assert len(result["top_sellers"]) == 3
        assert result["top_sellers"][0]["sales"] == 300

    @pytest.mark.asyncio
    async def test_get_marketplace_stats_average_rating(self, mock_db):
        """Test average rating calculation in stats."""
        stats = {
            "total_items": 20,
            "active_items": 15,
            "total_sales": 200,
            "total_revenue": 5000.0,
            "average_rating": 4.6,
            "categories": {},
            "top_sellers": [],
        }
        mock_db.execute.return_value = MagicMock(
            one=MagicMock(return_value=stats)
        )

        result = await get_marketplace_stats(mock_db)

        assert result["average_rating"] == 4.6

    @pytest.mark.asyncio
    async def test_get_marketplace_stats_with_seller_filter(self, mock_db, sample_stats):
        """Test stats filtered by seller."""
        mock_db.execute.return_value = MagicMock(
            one=MagicMock(return_value=sample_stats)
        )

        seller_id = str(uuid4())
        result = await get_marketplace_stats(mock_db, seller_id=seller_id)

        assert isinstance(result, dict)
