"""Tests for ListingService."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from ugc_marketplace.services.listing_service import ListingService


@pytest.fixture
def mock_db():
    """Provide a mock database session."""
    return MagicMock()


@pytest.fixture
def listing_service(mock_db):
    """Provide a ListingService instance with mocked DB."""
    return ListingService(db=mock_db)


@pytest.fixture
def sample_listing_data():
    """Provide sample listing data."""
    return {
        "id": "listing-001",
        "creator_id": "creator-001",
        "content_id": "content-001",
        "title": "Test Listing",
        "description": "A test listing",
        "price": 29.99,
        "currency": "USD",
        "status": "active",
        "category": "digital_art",
        "tags": ["art", "digital"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


class TestListingService:
    """Test suite for ListingService."""

    def test_create_listing(self, listing_service, mock_db, sample_listing_data):
        """Test creating a new listing."""
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        listing = listing_service.create_listing(sample_listing_data)

        assert listing is not None
        assert listing["title"] == "Test Listing"
        assert listing["price"] == 29.99
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_get_listing_by_id(self, listing_service, mock_db, sample_listing_data):
        """Test retrieving a listing by ID."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_listing_data

        listing = listing_service.get_listing_by_id("listing-001")

        assert listing is not None
        assert listing["id"] == "listing-001"
        assert listing["title"] == "Test Listing"

    def test_get_listing_by_id_not_found(self, listing_service, mock_db):
        """Test retrieving a non-existent listing returns None."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        listing = listing_service.get_listing_by_id("nonexistent")

        assert listing is None

    def test_list_listings(self, listing_service, mock_db, sample_listing_data):
        """Test listing all listings with pagination."""
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = [
            sample_listing_data
        ]

        listings = listing_service.list_listings(skip=0, limit=10)

        assert isinstance(listings, list)
        assert len(listings) == 1

    def test_list_listings_empty(self, listing_service, mock_db):
        """Test listing when no listings exist."""
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []

        listings = listing_service.list_listings(skip=0, limit=10)

        assert listings == []

    def test_list_listings_by_creator(self, listing_service, mock_db, sample_listing_data):
        """Test listing by creator ID."""
        mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = [
            sample_listing_data
        ]

        listings = listing_service.list_listings_by_creator("creator-001", skip=0, limit=10)

        assert isinstance(listings, list)
        assert len(listings) == 1

    def test_list_listings_by_category(self, listing_service, mock_db, sample_listing_data):
        """Test listing filtered by category."""
        mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = [
            sample_listing_data
        ]

        listings = listing_service.list_listings_by_category("digital_art", skip=0, limit=10)

        assert isinstance(listings, list)
        assert len(listings) == 1

    def test_update_listing(self, listing_service, mock_db, sample_listing_data):
        """Test updating a listing."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_listing_data
        mock_db.commit.return_value = None

        updates = {"title": "Updated Listing", "price": 39.99}
        updated = listing_service.update_listing("listing-001", updates)

        assert updated is not None
        mock_db.commit.assert_called_once()

    def test_update_listing_not_found(self, listing_service, mock_db):
        """Test updating a non-existent listing returns None."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = listing_service.update_listing("nonexistent", {"title": "new"})

        assert result is None

    def test_delete_listing(self, listing_service, mock_db, sample_listing_data):
        """Test deleting a listing."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_listing_data
        mock_db.delete.return_value = None
        mock_db.commit.return_value = None

        result = listing_service.delete_listing("listing-001")

        assert result is True
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_delete_listing_not_found(self, listing_service, mock_db):
        """Test deleting a non-existent listing returns False."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = listing_service.delete_listing("nonexistent")

        assert result is False

    def test_activate_listing(self, listing_service, mock_db, sample_listing_data):
        """Test activating a listing."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_listing_data
        mock_db.commit.return_value = None

        result = listing_service.activate_listing("listing-001")

        assert result is True
        mock_db.commit.assert_called_once()

    def test_deactivate_listing(self, listing_service, mock_db, sample_listing_data):
        """Test deactivating a listing."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_listing_data
        mock_db.commit.return_value = None

        result = listing_service.deactivate_listing("listing-001")

        assert result is True
        mock_db.commit.assert_called_once()

    def test_search_listings(self, listing_service, mock_db, sample_listing_data):
        """Test searching listings by title or tags."""
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_listing_data]

        results = listing_service.search_listings("test")

        assert isinstance(results, list)
        assert len(results) == 1

    def test_filter_listings_by_price_range(self, listing_service, mock_db, sample_listing_data):
        """Test filtering listings by price range."""
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_listing_data]

        results = listing_service.filter_listings_by_price_range(min_price=10.0, max_price=50.0)

        assert isinstance(results, list)
        assert len(results) == 1
