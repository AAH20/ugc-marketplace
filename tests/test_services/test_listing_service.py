"""
Comprehensive service tests for the Listing Service.

Tests cover:
- ListingService class methods (create_listing, get_listing, search_listings)
- Module-level convenience functions (get_listing, list_listings, create_listing, update_listing, delete_listing)
- Validation, error handling, and edge cases
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from ugc_marketplace.services import listing_service as listing_module
from ugc_marketplace.services.listing_service import (
    ListingService,
    Listing,
    ListingStatus,
    ListingCategory,
    Money,
    ListingValidationError,
    ListingNotFoundError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the default service singleton before each test."""
    listing_module._default_service = None
    yield
    listing_module._default_service = None


@pytest.fixture
def mock_repository():
    """Create a mock ListingRepository."""
    repo = MagicMock()
    repo.save = MagicMock()
    repo.get_by_id = MagicMock()
    repo.search = MagicMock()
    repo.count = MagicMock()
    return repo


@pytest.fixture
def listing_service(mock_repository):
    """Create a ListingService instance with a mock repository."""
    return ListingService(repository=mock_repository)


@pytest.fixture
def sample_listing():
    """Create a sample Listing dataclass instance."""
    return Listing(
        id=str(uuid4()),
        seller_id="seller-001",
        title="Test Listing",
        description="A test listing description that is long enough",
        category=ListingCategory.DIGITAL_ART,
        price=Money(amount_cents=2999, currency="USD"),
        status=ListingStatus.DRAFT,
        tags=["art", "digital"],
        media_urls=["https://example.com/image1.png"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        metadata={"key": "value"},
    )


@pytest.fixture
def sample_create_data():
    """Sample data for creating a listing."""
    return {
        "seller_id": "seller-001",
        "title": "New Test Listing",
        "description": "A new test listing description that is long enough",
        "category": "digital_art",
        "price": {"amount_cents": 4999, "currency": "USD"},
        "tags": ["new", "test"],
    }


@pytest.fixture
def sample_search_result():
    """Sample search result from the repository."""
    listing = Listing(
        id=str(uuid4()),
        seller_id="seller-001",
        title="Search Result",
        description="A search result listing",
        category=ListingCategory.PHOTOGRAPHY,
        price=Money(amount_cents=1999, currency="EUR"),
        status=ListingStatus.ACTIVE,
        tags=["photo"],
    )
    return [listing]


# ===========================================================================
# Unit Tests: ListingService.create_listing
# ===========================================================================


class TestListingServiceCreateListing:
    """Tests for ListingService.create_listing method."""

    def test_create_listing_success(self, listing_service, mock_repository, sample_create_data, sample_listing):
        """Test successfully creating a listing."""
        mock_repository.save.return_value = sample_listing

        result = listing_service.create_listing(sample_create_data)

        assert result is not None
        assert result.id == sample_listing.id
        assert result.title == sample_listing.title
        assert result.seller_id == sample_listing.seller_id
        assert result.category == sample_listing.category
        assert result.price.amount_cents == sample_listing.price.amount_cents
        mock_repository.save.assert_called_once()

    def test_create_listing_returns_saved_listing(self, listing_service, mock_repository, sample_create_data):
        """Test that create_listing returns the repository's saved listing."""
        saved_listing = Listing(
            id="saved-id",
            seller_id=sample_create_data["seller_id"],
            title=sample_create_data["title"],
            description=sample_create_data["description"],
            category=ListingCategory.DIGITAL_ART,
            price=Money(amount_cents=4999, currency="USD"),
        )
        mock_repository.save.return_value = saved_listing

        result = listing_service.create_listing(sample_create_data)

        assert result.id == "saved-id"
        assert result.title == sample_create_data["title"]

    def test_create_listing_missing_seller_id(self, listing_service, sample_create_data):
        """Test that missing seller_id raises ListingValidationError."""
        del sample_create_data["seller_id"]

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "seller_id"

    def test_create_listing_missing_title(self, listing_service, sample_create_data):
        """Test that missing title raises ListingValidationError."""
        del sample_create_data["title"]

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "title"

    def test_create_listing_missing_description(self, listing_service, sample_create_data):
        """Test that missing description raises ListingValidationError."""
        del sample_create_data["description"]

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "description"

    def test_create_listing_missing_category(self, listing_service, sample_create_data):
        """Test that missing category raises ListingValidationError."""
        del sample_create_data["category"]

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "category"

    def test_create_listing_missing_price(self, listing_service, sample_create_data):
        """Test that missing price raises ListingValidationError."""
        del sample_create_data["price"]

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "price"

    def test_create_listing_invalid_category(self, listing_service, sample_create_data):
        """Test that an invalid category raises ListingValidationError."""
        sample_create_data["category"] = "invalid_category"

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "category"

    def test_create_listing_invalid_price_type(self, listing_service, sample_create_data):
        """Test that a non-dict price raises ListingValidationError."""
        sample_create_data["price"] = "not_a_dict"

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "price"

    def test_create_listing_negative_price(self, listing_service, sample_create_data):
        """Test that a negative price amount raises ListingValidationError."""
        sample_create_data["price"] = {"amount_cents": -100, "currency": "USD"}

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert "amount_cents" in exc_info.value.field

    def test_create_listing_invalid_currency(self, listing_service, sample_create_data):
        """Test that an invalid currency code raises ListingValidationError."""
        sample_create_data["price"] = {"amount_cents": 100, "currency": "INVALID"}

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert "currency" in exc_info.value.field

    def test_create_listing_title_too_short(self, listing_service, sample_create_data):
        """Test that a title shorter than 3 characters raises ListingValidationError."""
        sample_create_data["title"] = "ab"

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "title"

    def test_create_listing_title_too_long(self, listing_service, sample_create_data):
        """Test that a title longer than 120 characters raises ListingValidationError."""
        sample_create_data["title"] = "a" * 121

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "title"

    def test_create_listing_description_too_short(self, listing_service, sample_create_data):
        """Test that a description shorter than 10 characters raises ListingValidationError."""
        sample_create_data["description"] = "short"

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "description"

    def test_create_listing_description_too_long(self, listing_service, sample_create_data):
        """Test that a description longer than 5000 characters raises ListingValidationError."""
        sample_create_data["description"] = "a" * 5001

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "description"

    def test_create_listing_too_many_tags(self, listing_service, sample_create_data):
        """Test that more than 10 tags raises ListingValidationError."""
        sample_create_data["tags"] = [f"tag{i}" for i in range(11)]

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "tags"

    def test_create_listing_empty_tag(self, listing_service, sample_create_data):
        """Test that an empty tag string raises ListingValidationError."""
        sample_create_data["tags"] = ["valid", "  "]

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "tags"

    def test_create_listing_tags_not_a_list(self, listing_service, sample_create_data):
        """Test that non-list tags raises ListingValidationError."""
        sample_create_data["tags"] = "not_a_list"

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "tags"

    def test_create_listing_too_many_media_urls(self, listing_service, sample_create_data):
        """Test that more than 20 media URLs raises ListingValidationError."""
        sample_create_data["media_urls"] = [f"https://example.com/{i}.png" for i in range(21)]

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "media_urls"

    def test_create_listing_invalid_status(self, listing_service, sample_create_data):
        """Test that an invalid status raises ListingValidationError."""
        sample_create_data["status"] = "invalid_status"

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "status"

    def test_create_listing_invalid_metadata_type(self, listing_service, sample_create_data):
        """Test that non-dict metadata raises ListingValidationError."""
        sample_create_data["metadata"] = "not_a_dict"

        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing(sample_create_data)

        assert exc_info.value.field == "metadata"

    def test_create_listing_non_dict_data(self, listing_service):
        """Test that non-dict data raises ListingValidationError."""
        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.create_listing("not_a_dict")

        assert exc_info.value.field == "data"

    def test_create_listing_strips_whitespace(self, listing_service, mock_repository, sample_create_data):
        """Test that title and description are stripped of whitespace."""
        sample_create_data["title"] = "  Padded Title  "
        sample_create_data["description"] = "  Padded description that is long enough  "

        listing_service.create_listing(sample_create_data)

        saved_call = mock_repository.save.call_args[0][0]
        assert saved_call.title == "Padded Title"
        assert saved_call.description == "Padded description that is long enough"

    def test_create_listing_strips_empty_tags(self, listing_service, mock_repository, sample_create_data):
        """Test that empty/whitespace tags are filtered out."""
        sample_create_data["tags"] = ["valid", "  ", "also_valid", ""]

        listing_service.create_listing(sample_create_data)

        saved_call = mock_repository.save.call_args[0][0]
        assert saved_call.tags == ["valid", "also_valid"]

    def test_create_listing_generates_uuid(self, listing_service, mock_repository, sample_create_data):
        """Test that a UUID is generated for the listing ID."""
        listing_service.create_listing(sample_create_data)

        saved_call = mock_repository.save.call_args[0][0]
        assert saved_call.id is not None
        assert len(saved_call.id) == 36  # UUID string length

    def test_create_listing_sets_default_status(self, listing_service, mock_repository, sample_create_data):
        """Test that the default status is DRAFT when not specified."""
        listing_service.create_listing(sample_create_data)

        saved_call = mock_repository.save.call_args[0][0]
        assert saved_call.status == ListingStatus.DRAFT

    def test_create_listing_sets_timestamps(self, listing_service, mock_repository, sample_create_data):
        """Test that created_at and updated_at are set."""
        listing_service.create_listing(sample_create_data)

        saved_call = mock_repository.save.call_args[0][0]
        assert saved_call.created_at is not None
        assert saved_call.updated_at is not None

    def test_create_listing_with_all_categories(self, listing_service, mock_repository, sample_create_data):
        """Test creating listings with each valid category."""
        categories = [
            "digital_art",
            "photography",
            "video",
            "audio",
            "writing",
            "template",
            "other",
        ]
        for cat in categories:
            data = {**sample_create_data, "category": cat}
            result = listing_service.create_listing(data)
            assert result is not None

    def test_create_listing_with_all_statuses(self, listing_service, mock_repository, sample_create_data):
        """Test creating listings with each valid status."""
        statuses = ["draft", "active", "paused", "sold", "archived"]
        for status in statuses:
            data = {**sample_create_data, "status": status}
            result = listing_service.create_listing(data)
            assert result is not None

    def test_create_listing_with_money_object(self, listing_service, mock_repository, sample_create_data):
        """Test creating a listing with a Money object as price."""
        sample_create_data["price"] = Money(amount_cents=5000, currency="EUR")

        result = listing_service.create_listing(sample_create_data)

        assert result is not None
        assert result.price.amount_cents == 5000
        assert result.price.currency == "EUR"


# ===========================================================================
# Unit Tests: ListingService.get_listing
# ===========================================================================


class TestListingServiceGetListing:
    """Tests for ListingService.get_listing method."""

    def test_get_listing_success(self, listing_service, mock_repository, sample_listing):
        """Test successfully retrieving a listing by ID."""
        mock_repository.get_by_id.return_value = sample_listing

        result = listing_service.get_listing(sample_listing.id)

        assert result is not None
        assert result.id == sample_listing.id
        assert result.title == sample_listing.title
        assert result.seller_id == sample_listing.seller_id
        assert result.category == sample_listing.category
        assert result.price.amount_cents == sample_listing.price.amount_cents
        assert result.status == sample_listing.status
        mock_repository.get_by_id.assert_called_once_with(sample_listing.id)

    def test_get_listing_not_found(self, listing_service, mock_repository):
        """Test that a non-existent listing raises ListingNotFoundError."""
        mock_repository.get_by_id.return_value = None

        with pytest.raises(ListingNotFoundError) as exc_info:
            listing_service.get_listing("nonexistent-id")

        assert exc_info.value.listing_id == "nonexistent-id"

    def test_get_listing_empty_id(self, listing_service):
        """Test that an empty listing ID raises ListingValidationError."""
        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.get_listing("")

        assert exc_info.value.field == "listing_id"

    def test_get_listing_whitespace_id(self, listing_service):
        """Test that a whitespace-only listing ID raises ListingValidationError."""
        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.get_listing("   ")

        assert exc_info.value.field == "listing_id"

    def test_get_listing_none_id(self, listing_service):
        """Test that a None listing ID raises ListingValidationError."""
        with pytest.raises(ListingValidationError):
            listing_service.get_listing(None)

    def test_get_listing_returns_correct_type(self, listing_service, mock_repository, sample_listing):
        """Test that get_listing returns a Listing dataclass."""
        mock_repository.get_by_id.return_value = sample_listing

        result = listing_service.get_listing(sample_listing.id)

        assert isinstance(result, Listing)


# ===========================================================================
# Unit Tests: ListingService.search_listings
# ===========================================================================


class TestListingServiceSearchListings:
    """Tests for ListingService.search_listings method."""

    def test_search_listings_success(self, listing_service, mock_repository, sample_search_result):
        """Test successfully searching listings."""
        mock_repository.search.return_value = sample_search_result
        mock_repository.count.return_value = 1

        result = listing_service.search_listings(query="test", filters={}, limit=10, offset=0)

        assert result is not None
        assert "results" in result
        assert "total" in result
        assert "limit" in result
        assert "offset" in result
        assert len(result["results"]) == 1
        assert result["total"] == 1
        assert result["limit"] == 10
        assert result["offset"] == 0

    def test_search_listings_with_filters(self, listing_service, mock_repository, sample_search_result):
        """Test searching with filter parameters."""
        mock_repository.search.return_value = sample_search_result
        mock_repository.count.return_value = 1

        filters = {
            "category": "digital_art",
            "status": "active",
            "min_price_cents": 1000,
            "max_price_cents": 5000,
            "seller_id": "seller-001",
            "tags": ["art"],
        }
        result = listing_service.search_listings(query="art", filters=filters, limit=20, offset=0)

        assert result is not None
        mock_repository.search.assert_called_once_with("art", filters, 20, 0)
        mock_repository.count.assert_called_once_with("art", filters)

    def test_search_listings_empty_query(self, listing_service, mock_repository):
        """Test searching with an empty query string."""
        mock_repository.search.return_value = []
        mock_repository.count.return_value = 0

        result = listing_service.search_listings(query="", filters={}, limit=10, offset=0)

        assert result["results"] == []
        assert result["total"] == 0

    def test_search_listings_none_query(self, listing_service, mock_repository):
        """Test searching with None as query."""
        mock_repository.search.return_value = []
        mock_repository.count.return_value = 0

        result = listing_service.search_listings(query=None, filters={}, limit=10, offset=0)

        assert result["results"] == []

    def test_search_listings_strips_query(self, listing_service, mock_repository):
        """Test that the query string is stripped of whitespace."""
        mock_repository.search.return_value = []
        mock_repository.count.return_value = 0

        listing_service.search_listings(query="  test query  ", filters={}, limit=10, offset=0)

        mock_repository.search.assert_called_once_with("test query", {}, 10, 0)

    def test_search_listings_default_pagination(self, listing_service, mock_repository):
        """Test that default pagination values are used."""
        mock_repository.search.return_value = []
        mock_repository.count.return_value = 0

        result = listing_service.search_listings(query="", filters={})

        assert result["limit"] == 20  # _DEFAULT_PAGE_SIZE
        assert result["offset"] == 0

    def test_search_listings_limit_too_small(self, listing_service):
        """Test that limit < 1 raises ListingValidationError."""
        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.search_listings(query="", filters={}, limit=0, offset=0)

        assert exc_info.value.field == "limit"

    def test_search_listings_limit_negative(self, listing_service):
        """Test that negative limit raises ListingValidationError."""
        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.search_listings(query="", filters={}, limit=-5, offset=0)

        assert exc_info.value.field == "limit"

    def test_search_listings_limit_too_large(self, listing_service, mock_repository):
        """Test that limit > 100 is clamped to 100."""
        mock_repository.search.return_value = []
        mock_repository.count.return_value = 0

        result = listing_service.search_listings(query="", filters={}, limit=200, offset=0)

        assert result["limit"] == 100

    def test_search_listings_offset_negative(self, listing_service):
        """Test that negative offset raises ListingValidationError."""
        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.search_listings(query="", filters={}, limit=10, offset=-1)

        assert exc_info.value.field == "offset"

    def test_search_listings_unknown_filter_keys(self, listing_service):
        """Test that unknown filter keys raise ListingValidationError."""
        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.search_listings(
                query="",
                filters={"unknown_key": "value"},
                limit=10,
                offset=0,
            )

        assert exc_info.value.field == "filters"

    def test_search_listings_multiple_unknown_filter_keys(self, listing_service):
        """Test that multiple unknown filter keys are reported."""
        with pytest.raises(ListingValidationError) as exc_info:
            listing_service.search_listings(
                query="",
                filters={"bad_key1": "v1", "bad_key2": "v2"},
                limit=10,
                offset=0,
            )

        assert "bad_key1" in exc_info.value.message
        assert "bad_key2" in exc_info.value.message

    def test_search_listings_all_valid_filter_keys(self, listing_service, mock_repository):
        """Test that all valid filter keys are accepted."""
        mock_repository.search.return_value = []
        mock_repository.count.return_value = 0

        filters = {
            "category": "digital_art",
            "status": "active",
            "min_price_cents": 100,
            "max_price_cents": 10000,
            "seller_id": "seller-001",
            "tags": ["art", "digital"],
        }
        result = listing_service.search_listings(query="", filters=filters, limit=10, offset=0)

        assert result is not None

    def test_search_listings_pagination_offset(self, listing_service, mock_repository):
        """Test that pagination offset is passed correctly."""
        mock_repository.search.return_value = []
        mock_repository.count.return_value = 0

        result = listing_service.search_listings(query="", filters={}, limit=5, offset=15)

        assert result["offset"] == 15
        assert result["limit"] == 5
        mock_repository.search.assert_called_once_with("", {}, 5, 15)

    def test_search_listings_returns_correct_structure(self, listing_service, mock_repository, sample_search_result):
        """Test that the search result has the correct structure."""
        mock_repository.search.return_value = sample_search_result
        mock_repository.count.return_value = 1

        result = listing_service.search_listings(query="test", filters={}, limit=10, offset=0)

        assert isinstance(result, dict)
        assert isinstance(result["results"], list)
        assert isinstance(result["total"], int)
        assert isinstance(result["limit"], int)
        assert isinstance(result["offset"], int)

    def test_search_listings_with_none_filters(self, listing_service, mock_repository):
        """Test that None filters defaults to empty dict."""
        mock_repository.search.return_value = []
        mock_repository.count.return_value = 0

        result = listing_service.search_listings(query="", filters=None, limit=10, offset=0)

        assert result is not None
        mock_repository.search.assert_called_once_with("", {}, 10, 0)


# ===========================================================================
# Integration Tests: Module-level create_listing
# ===========================================================================


class TestModuleCreateListing:
    """Tests for the module-level create_listing function."""

    def test_create_listing_success(self, sample_create_data):
        """Test successfully creating a listing via module function."""
        result = listing_module.create_listing(sample_create_data)

        assert result is not None
        assert "id" in result
        assert result["title"] == sample_create_data["title"]
        assert result["seller_id"] == sample_create_data["seller_id"]
        assert result["category"] == sample_create_data["category"]
        assert result["price"]["amount_cents"] == sample_create_data["price"]["amount_cents"]
        assert result["price"]["currency"] == sample_create_data["price"]["currency"]
        assert result["status"] == "draft"
        assert "created_at" in result
        assert "updated_at" in result

    def test_create_listing_returns_dict(self, sample_create_data):
        """Test that create_listing returns a dictionary."""
        result = listing_module.create_listing(sample_create_data)

        assert isinstance(result, dict)

    def test_create_listing_with_all_fields(self):
        """Test creating a listing with all optional fields."""
        data = {
            "seller_id": "seller-002",
            "title": "Full Listing",
            "description": "A listing with all fields",
            "category": "photography",
            "price": {"amount_cents": 9999, "currency": "EUR"},
            "tags": ["photo", "nature"],
            "media_urls": ["https://example.com/photo1.jpg"],
            "status": "active",
            "metadata": {"resolution": "4K"},
        }

        result = listing_module.create_listing(data)

        assert result is not None
        assert result["title"] == "Full Listing"
        assert result["category"] == "photography"
        assert result["price"]["currency"] == "EUR"
        assert result["tags"] == ["photo", "nature"]
        assert result["media_urls"] == ["https://example.com/photo1.jpg"]
        assert result["status"] == "active"
        assert result["metadata"] == {"resolution": "4K"}

    def test_create_listing_validation_error(self):
        """Test that invalid data raises ListingValidationError."""
        with pytest.raises(ListingValidationError):
            listing_module.create_listing({"seller_id": "seller-001"})

    def test_create_listing_persists_to_repository(self, sample_create_data):
        """Test that created listing can be retrieved."""
        created = listing_module.create_listing(sample_create_data)

        fetched = listing_module.get_listing(created["id"])

        assert fetched is not None
        assert fetched["id"] == created["id"]
        assert fetched["title"] == created["title"]


# ===========================================================================
# Integration Tests: Module-level get_listing
# ===========================================================================


class TestModuleGetListing:
    """Tests for the module-level get_listing function."""

    def test_get_listing_success(self, sample_create_data):
        """Test successfully retrieving a listing via module function."""
        created = listing_module.create_listing(sample_create_data)

        result = listing_module.get_listing(created["id"])

        assert result is not None
        assert result["id"] == created["id"]
        assert result["title"] == created["title"]
        assert result["seller_id"] == created["seller_id"]
        assert result["category"] == created["category"]
        assert result["price"]["amount_cents"] == created["price"]["amount_cents"]
        assert result["status"] == created["status"]

    def test_get_listing_not_found(self):
        """Test that a non-existent listing raises ListingNotFoundError."""
        with pytest.raises(ListingNotFoundError):
            listing_module.get_listing("nonexistent-id")

    def test_get_listing_invalid_id(self):
        """Test that an empty ID raises ListingValidationError."""
        with pytest.raises(ListingValidationError):
            listing_module.get_listing("")

    def test_get_listing_returns_dict(self, sample_create_data):
        """Test that get_listing returns a dictionary."""
        created = listing_module.create_listing(sample_create_data)

        result = listing_module.get_listing(created["id"])

        assert isinstance(result, dict)

    def test_get_listing_contains_all_fields(self, sample_create_data):
        """Test that get_listing returns all expected fields."""
        created = listing_module.create_listing(sample_create_data)

        result = listing_module.get_listing(created["id"])

        expected_fields = [
            "id", "seller_id", "title", "description", "category",
            "price", "status", "tags", "media_urls", "created_at",
            "updated_at", "metadata",
        ]
        for field in expected_fields:
            assert field in result, f"Missing field: {field}"


# ===========================================================================
# Integration Tests: Module-level list_listings
# ===========================================================================


class TestModuleListListings:
    """Tests for the module-level list_listings function."""

    def test_list_listings_empty(self):
        """Test listing when no listings exist."""
        result = listing_module.list_listings(filters={}, page=1, page_size=10)

        assert result == []

    def test_list_listings_with_data(self, sample_create_data):
        """Test listing returns created listings."""
        listing_module.create_listing(sample_create_data)

        result = listing_module.list_listings(filters={}, page=1, page_size=10)

        assert isinstance(result, list)
        assert len(result) >= 1

    def test_list_listings_with_filters(self, sample_create_data):
        """Test listing with filter parameters."""
        listing_module.create_listing(sample_create_data)

        result = listing_module.list_listings(
            filters={"category": "digital_art"}, page=1, page_size=10
        )

        assert isinstance(result, list)
        assert len(result) >= 1

    def test_list_listings_pagination(self, sample_create_data):
        """Test listing with pagination."""
        # Create multiple listings
        for i in range(5):
            data = {**sample_create_data, "title": f"Listing {i}"}
            listing_module.create_listing(data)

        result = listing_module.list_listings(filters={}, page=1, page_size=2)

        assert isinstance(result, list)
        assert len(result) <= 2

    def test_list_listings_page_2(self, sample_create_data):
        """Test listing page 2."""
        # Create multiple listings
        for i in range(5):
            data = {**sample_create_data, "title": f"Listing {i}"}
            listing_module.create_listing(data)

        result = listing_module.list_listings(filters={}, page=2, page_size=2)

        assert isinstance(result, list)

    def test_list_listings_returns_dicts(self, sample_create_data):
        """Test that list_listings returns a list of dicts."""
        listing_module.create_listing(sample_create_data)

        result = listing_module.list_listings(filters={}, page=1, page_size=10)

        assert isinstance(result, list)
        if result:
            assert isinstance(result[0], dict)

    def test_list_listings_filter_by_status(self, sample_create_data):
        """Test filtering listings by status."""
        listing_module.create_listing(sample_create_data)

        result = listing_module.list_listings(
            filters={"status": "draft"}, page=1, page_size=10
        )

        assert isinstance(result, list)
        for listing in result:
            assert listing["status"] == "draft"

    def test_list_listings_filter_by_seller(self, sample_create_data):
        """Test filtering listings by seller ID."""
        listing_module.create_listing(sample_create_data)

        result = listing_module.list_listings(
            filters={"seller_id": sample_create_data["seller_id"]},
            page=1,
            page_size=10,
        )

        assert isinstance(result, list)
        assert len(result) >= 1

    def test_list_listings_filter_by_category(self, sample_create_data):
        """Test filtering listings by category."""
        listing_module.create_listing(sample_create_data)

        result = listing_module.list_listings(
            filters={"category": "digital_art"}, page=1, page_size=10
        )

        assert isinstance(result, list)
        assert len(result) >= 1

    def test_list_listings_filter_by_price_range(self, sample_create_data):
        """Test filtering listings by price range."""
        listing_module.create_listing(sample_create_data)

        result = listing_module.list_listings(
            filters={"min_price_cents": 1000, "max_price_cents": 5000},
            page=1,
            page_size=10,
        )

        assert isinstance(result, list)

    def test_list_listings_filter_by_tags(self, sample_create_data):
        """Test filtering listings by tags."""
        listing_module.create_listing(sample_create_data)

        result = listing_module.list_listings(
            filters={"tags": ["new", "test"]}, page=1, page_size=10
        )

        assert isinstance(result, list)

    def test_list_listings_invalid_page(self):
        """Test that invalid page raises ListingValidationError."""
        with pytest.raises(ListingValidationError):
            listing_module.list_listings(filters={}, page=0, page_size=10)

    def test_list_listings_invalid_page_size(self):
        """Test that invalid page_size raises ListingValidationError."""
        with pytest.raises(ListingValidationError):
            listing_module.list_listings(filters={}, page=1, page_size=0)

    def test_list_listings_unknown_filter(self):
        """Test that unknown filter keys raise ListingValidationError."""
        with pytest.raises(ListingValidationError):
            listing_module.list_listings(
                filters={"unknown": "value"}, page=1, page_size=10
            )


# ===========================================================================
# Integration Tests: Module-level update_listing
# ===========================================================================


class TestModuleUpdateListing:
    """Tests for the module-level update_listing function."""

    def test_update_listing_success(self, sample_create_data):
        """Test successfully updating a listing."""
        created = listing_module.create_listing(sample_create_data)

        result = listing_module.update_listing(
            created["id"], {"title": "Updated Title", "price": {"amount_cents": 5999, "currency": "USD"}}
        )

        assert result is not None
        assert result["id"] == created["id"]
        assert result["title"] == "Updated Title"
        assert result["price"]["amount_cents"] == 5999

    def test_update_listing_not_found(self):
        """Test that updating a non-existent listing raises ListingNotFoundError."""
        with pytest.raises(ListingNotFoundError):
            listing_module.update_listing("nonexistent-id", {"title": "New Title"})

    def test_update_listing_partial_update(self, sample_create_data):
        """Test updating only some fields."""
        created = listing_module.create_listing(sample_create_data)
        original_title = created["title"]

        result = listing_module.update_listing(
            created["id"], {"price": {"amount_cents": 0, "currency": "USD"}}
        )

        assert result is not None
        assert result["title"] == original_title
        assert result["price"]["amount_cents"] == 0

    def test_update_listing_status(self, sample_create_data):
        """Test updating a listing's status."""
        created = listing_module.create_listing(sample_create_data)

        result = listing_module.update_listing(created["id"], {"status": "active"})

        assert result is not None
        assert result["status"] == "active"

    def test_update_listing_tags(self, sample_create_data):
        """Test updating a listing's tags."""
        created = listing_module.create_listing(sample_create_data)

        result = listing_module.update_listing(
            created["id"], {"tags": ["updated", "tags"]}
        )

        assert result is not None
        assert result["tags"] == ["updated", "tags"]

    def test_update_listing_preserves_id(self, sample_create_data):
        """Test that updating preserves the original ID."""
        created = listing_module.create_listing(sample_create_data)
        original_id = created["id"]

        result = listing_module.update_listing(created["id"], {"title": "New Title"})

        assert result["id"] == original_id

    def test_update_listing_returns_dict(self, sample_create_data):
        """Test that update_listing returns a dictionary."""
        created = listing_module.create_listing(sample_create_data)

        result = listing_module.update_listing(created["id"], {"title": "Updated"})

        assert isinstance(result, dict)

    def test_update_listing_invalid_data(self, sample_create_data):
        """Test that invalid update data raises ListingValidationError."""
        created = listing_module.create_listing(sample_create_data)

        with pytest.raises(ListingValidationError):
            listing_module.update_listing(
                created["id"], {"category": "invalid_category"}
            )


# ===========================================================================
# Integration Tests: Module-level delete_listing
# ===========================================================================


class TestModuleDeleteListing:
    """Tests for the module-level delete_listing function."""

    def test_delete_listing_success(self, sample_create_data):
        """Test successfully deleting a listing."""
        created = listing_module.create_listing(sample_create_data)

        result = listing_module.delete_listing(created["id"])

        assert result is True

    def test_delete_listing_not_found(self):
        """Test that deleting a non-existent listing returns False."""
        result = listing_module.delete_listing("nonexistent-id")

        assert result is False

    def test_delete_listing_removes_from_repository(self, sample_create_data):
        """Test that deleted listing can no longer be retrieved."""
        created = listing_module.create_listing(sample_create_data)
        listing_module.delete_listing(created["id"])

        with pytest.raises(ListingNotFoundError):
            listing_module.get_listing(created["id"])

    def test_delete_listing_returns_bool(self, sample_create_data):
        """Test that delete_listing returns a boolean."""
        created = listing_module.create_listing(sample_create_data)

        result = listing_module.delete_listing(created["id"])

        assert isinstance(result, bool)

    def test_delete_listing_invalid_id(self):
        """Test that deleting with an empty ID returns False."""
        result = listing_module.delete_listing("")

        assert result is False

    def test_delete_listing_twice(self, sample_create_data):
        """Test that deleting the same listing twice returns False the second time."""
        created = listing_module.create_listing(sample_create_data)

        first_delete = listing_module.delete_listing(created["id"])
        second_delete = listing_module.delete_listing(created["id"])

        assert first_delete is True
        assert second_delete is False


# ===========================================================================
# Error Handling Tests
# ===========================================================================


class TestErrorHandling:
    """Tests for error handling across the service."""

    def test_listing_validation_error_message(self):
        """Test that ListingValidationError has a descriptive message."""
        error = ListingValidationError("title", "must be at least 3 characters")

        assert error.field == "title"
        assert error.message == "must be at least 3 characters"
        assert "title" in str(error)
        assert "must be at least 3 characters" in str(error)

    def test_listing_not_found_error_message(self):
        """Test that ListingNotFoundError has a descriptive message."""
        error = ListingNotFoundError("listing-123")

        assert error.listing_id == "listing-123"
        assert "listing-123" in str(error)

    def test_money_negative_amount(self):
        """Test that Money with negative amount raises ValueError."""
        with pytest.raises(ValueError):
            Money(amount_cents=-100, currency="USD")

    def test_money_invalid_currency(self):
        """Test that Money with invalid currency raises ValueError."""
        with pytest.raises(ValueError):
            Money(amount_cents=100, currency="INVALID")

    def test_money_valid_currency_lowercase(self):
        """Test that Money with lowercase currency raises ValueError."""
        with pytest.raises(ValueError):
            Money(amount_cents=100, currency="usd")

    def test_money_default_currency(self):
        """Test that Money defaults to USD."""
        money = Money(amount_cents=100)

        assert money.currency == "USD"

    def test_listing_category_enum_values(self):
        """Test that all expected category values exist."""
        expected = {
            "digital_art", "photography", "video", "audio",
            "writing", "template", "other",
        }
        actual = {c.value for c in ListingCategory}

        assert expected == actual

    def test_listing_status_enum_values(self):
        """Test that all expected status values exist."""
        expected = {"draft", "active", "paused", "sold", "archived"}
        actual = {s.value for s in ListingStatus}

        assert expected == actual


# ===========================================================================
# Edge Case Tests
# ===========================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_create_listing_with_minimal_valid_data(self):
        """Test creating a listing with the minimum required fields."""
        data = {
            "seller_id": "seller-001",
            "title": "abc",  # Minimum 3 characters
            "description": "1234567890",  # Minimum 10 characters
            "category": "other",
            "price": {"amount_cents": 0, "currency": "USD"},
        }

        result = listing_module.create_listing(data)

        assert result is not None
        assert result["title"] == "abc"
        assert result["price"]["amount_cents"] == 0

    def test_create_listing_with_max_tags(self):
        """Test creating a listing with exactly 10 tags."""
        data = {
            "seller_id": "seller-001",
            "title": "Max Tags Listing",
            "description": "A listing with maximum tags",
            "category": "digital_art",
            "price": {"amount_cents": 100, "currency": "USD"},
            "tags": [f"tag{i}" for i in range(10)],
        }

        result = listing_module.create_listing(data)

        assert result is not None
        assert len(result["tags"]) == 10

    def test_create_listing_with_max_media_urls(self):
        """Test creating a listing with exactly 20 media URLs."""
        data = {
            "seller_id": "seller-001",
            "title": "Max Media Listing",
            "description": "A listing with maximum media URLs",
            "category": "digital_art",
            "price": {"amount_cents": 100, "currency": "USD"},
            "media_urls": [f"https://example.com/{i}.png" for i in range(20)],
        }

        result = listing_module.create_listing(data)

        assert result is not None
        assert len(result["media_urls"]) == 20

    def test_create_listing_with_max_title_length(self):
        """Test creating a listing with exactly 120 character title."""
        data = {
            "seller_id": "seller-001",
            "title": "a" * 120,
            "description": "A listing with maximum title length",
            "category": "digital_art",
            "price": {"amount_cents": 100, "currency": "USD"},
        }

        result = listing_module.create_listing(data)

        assert result is not None
        assert len(result["title"]) == 120

    def test_create_listing_with_max_description_length(self):
        """Test creating a listing with exactly 5000 character description."""
        data = {
            "seller_id": "seller-001",
            "title": "Max Description Listing",
            "description": "a" * 5000,
            "category": "digital_art",
            "price": {"amount_cents": 100, "currency": "USD"},
        }

        result = listing_module.create_listing(data)

        assert result is not None
        assert len(result["description"]) == 5000

    def test_create_listing_with_empty_tags(self):
        """Test creating a listing with empty tags list."""
        data = {
            "seller_id": "seller-001",
            "title": "Empty Tags Listing",
            "description": "A listing with no tags",
            "category": "digital_art",
            "price": {"amount_cents": 100, "currency": "USD"},
            "tags": [],
        }

        result = listing_module.create_listing(data)

        assert result is not None
        assert result["tags"] == []

    def test_create_listing_with_empty_media_urls(self):
        """Test creating a listing with empty media URLs list."""
        data = {
            "seller_id": "seller-001",
            "title": "Empty Media Listing",
            "description": "A listing with no media",
            "category": "digital_art",
            "price": {"amount_cents": 100, "currency": "USD"},
            "media_urls": [],
        }

        result = listing_module.create_listing(data)

        assert result is not None
        assert result["media_urls"] == []

    def test_create_listing_with_empty_metadata(self):
        """Test creating a listing with empty metadata."""
        data = {
            "seller_id": "seller-001",
            "title": "Empty Metadata Listing",
            "description": "A listing with no metadata",
            "category": "digital_art",
            "price": {"amount_cents": 100, "currency": "USD"},
            "metadata": {},
        }

        result = listing_module.create_listing(data)

        assert result is not None
        assert result["metadata"] == {}

    def test_create_listing_with_complex_metadata(self):
        """Test creating a listing with nested metadata."""
        data = {
            "seller_id": "seller-001",
            "title": "Complex Metadata Listing",
            "description": "A listing with complex metadata",
            "category": "digital_art",
            "price": {"amount_cents": 100, "currency": "USD"},
            "metadata": {
                "nested": {"key": "value"},
                "list": [1, 2, 3],
                "number": 42,
                "boolean": True,
            },
        }

        result = listing_module.create_listing(data)

        assert result is not None
        assert result["metadata"]["nested"]["key"] == "value"

    def test_search_listings_with_special_characters(self, listing_service, mock_repository):
        """Test searching with special characters in query."""
        mock_repository.search.return_value = []
        mock_repository.count.return_value = 0

        result = listing_service.search_listings(
            query="test & <script>alert('xss')</script>",
            filters={},
            limit=10,
            offset=0,
        )

        assert result is not None

    def test_search_listings_with_unicode_query(self, listing_service, mock_repository):
        """Test searching with unicode characters."""
        mock_repository.search.return_value = []
        mock_repository.count.return_value = 0

        result = listing_service.search_listings(
            query="测试 🎨 émojis",
            filters={},
            limit=10,
            offset=0,
        )

        assert result is not None

    def test_create_listing_with_unicode_content(self):
        """Test creating a listing with unicode characters."""
        data = {
            "seller_id": "seller-001",
            "title": "测试列表 🎨",
            "description": "这是一个测试列表，包含表情符号 🎉🎊",
            "category": "digital_art",
            "price": {"amount_cents": 100, "currency": "USD"},
            "tags": ["测试", "🎨"],
        }

        result = listing_module.create_listing(data)

        assert result is not None
        assert result["title"] == "测试列表 🎨"
        assert "测试" in result["tags"]

    def test_create_listing_with_all_currencies(self):
        """Test creating listings with various valid currency codes."""
        currencies = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF"]

        for currency in currencies:
            data = {
                "seller_id": "seller-001",
                "title": f"{currency} Listing",
                "description": f"A listing priced in {currency}",
                "category": "digital_art",
                "price": {"amount_cents": 100, "currency": currency},
            }

            result = listing_module.create_listing(data)

            assert result is not None
            assert result["price"]["currency"] == currency
