"""Unit tests for the listing service module.

Targets the real public API of ``ugc_marketplace.services.listing_service``:

* domain types ``Money``, ``Listing``, ``ListingStatus``, ``ListingCategory``
* ``ListingService`` validation / create / get / search behaviour against an
  injected repository (the in-memory repo shipped for tests)
* ``InMemoryListingRepository`` search / count semantics
* the module-level ``create_listing`` / ``get_listing`` / ``list_listings``
  helpers backed by the default in-memory service

The default service and its repository are module-global, so an autouse
fixture resets them to keep each test independent.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from ugc_marketplace.services import listing_service as ls
from ugc_marketplace.services._memory_repo import InMemoryListingRepository
from ugc_marketplace.services.listing_service import (
    Listing,
    ListingCategory,
    ListingNotFoundError,
    ListingService,
    ListingStatus,
    ListingValidationError,
    Money,
    create_listing,
    delete_listing,
    get_listing,
    list_listings,
    update_listing,
)


@pytest.fixture(autouse=True)
def reset_default_service():
    """Reset the module-global default service around every test."""
    ls._default_service = None
    yield
    ls._default_service = None


@pytest.fixture
def service():
    """A ListingService backed by a fresh in-memory repository."""
    return ListingService(InMemoryListingRepository())


@pytest.fixture
def valid_data():
    """Minimal valid listing payload."""
    return {
        "seller_id": "seller-001",
        "title": "Sunset Overdrive Art",
        "description": "A vibrant digital painting of a sunset.",
        "category": "digital_art",
        "price": {"amount_cents": 1500, "currency": "USD"},
    }


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


class TestMoney:
    """Money is a validated frozen value object."""

    def test_valid_money(self):
        money = Money(amount_cents=100, currency="EUR")

        assert money.amount_cents == 100
        assert money.currency == "EUR"

    def test_default_currency_is_usd(self):
        assert Money(amount_cents=0).currency == "USD"

    def test_negative_amount_raises(self):
        with pytest.raises(ValueError, match="amount_cents must be non-negative"):
            Money(amount_cents=-1)

    def test_zero_amount_is_allowed(self):
        assert Money(amount_cents=0).amount_cents == 0

    @pytest.mark.parametrize("currency", ["usd", "US", "USDD", "", "U1D"])
    def test_invalid_currency_raises(self, currency):
        with pytest.raises(ValueError, match="3-letter ISO 4217 code"):
            Money(amount_cents=10, currency=currency)

    def test_money_is_frozen(self):
        money = Money(amount_cents=10)

        with pytest.raises(Exception):
            money.amount_cents = 20  # type: ignore[misc]


class TestListingDomain:
    """Listing defaults and enum values."""

    def test_listing_defaults(self):
        listing = Listing(
            id="l-1",
            seller_id="s-1",
            title="t",
            description="d",
            category=ListingCategory.OTHER,
            price=Money(amount_cents=1),
        )

        assert listing.status is ListingStatus.DRAFT
        assert listing.tags == []
        assert listing.media_urls == []
        assert listing.metadata == {}
        assert isinstance(listing.created_at, datetime)
        assert isinstance(listing.updated_at, datetime)

    def test_status_values(self):
        assert {s.value for s in ListingStatus} == {
            "draft", "active", "paused", "sold", "archived"
        }

    def test_category_values(self):
        assert {c.value for c in ListingCategory} == {
            "digital_art", "photography", "video", "audio",
            "writing", "template", "other",
        }

    def test_not_found_error_carries_id(self):
        err = ListingNotFoundError("l-42")
        assert err.listing_id == "l-42"
        assert "l-42" in str(err)

    def test_validation_error_carries_field_and_message(self):
        err = ListingValidationError("title", "is required")
        assert err.field == "title"
        assert err.message == "is required"
        assert str(err) == "title: is required"


# ---------------------------------------------------------------------------
# create_listing
# ---------------------------------------------------------------------------


class TestCreateListing:
    """ListingService.create_listing validation and persistence."""

    def test_creates_and_persists(self, service, valid_data):
        listing = service.create_listing(valid_data)

        assert isinstance(listing, Listing)
        assert uuid.UUID(listing.id)
        assert listing.seller_id == "seller-001"
        assert listing.title == "Sunset Overdrive Art"
        assert listing.category is ListingCategory.DIGITAL_ART
        assert listing.price.amount_cents == 1500
        assert listing.status is ListingStatus.DRAFT
        # persisted via the repository
        assert service.get_listing(listing.id) is listing

    def test_title_and_description_are_stripped(self, service, valid_data):
        valid_data["title"] = "  Padded Title  "
        valid_data["description"] = "  padded description text  "

        listing = service.create_listing(valid_data)

        assert listing.title == "Padded Title"
        assert listing.description == "padded description text"

    def test_tags_and_media_are_stripped_and_filtered(self, service, valid_data):
        valid_data["tags"] = ["art", "  sunset  "]
        valid_data["media_urls"] = ["  http://x/1.png  "]

        listing = service.create_listing(valid_data)

        assert listing.tags == ["art", "sunset"]
        assert listing.media_urls == ["http://x/1.png"]

    def test_status_can_be_set(self, service, valid_data):
        valid_data["status"] = "active"

        assert service.create_listing(valid_data).status is ListingStatus.ACTIVE

    def test_price_money_instance_is_accepted(self, service, valid_data):
        valid_data["price"] = Money(amount_cents=99, currency="GBP")

        assert service.create_listing(valid_data).price.currency == "GBP"

    def test_ids_are_unique(self, service, valid_data):
        first = service.create_listing(valid_data).id
        second = service.create_listing(valid_data).id

        assert first != second

    def test_non_dict_data_raises(self, service):
        with pytest.raises(ListingValidationError, match="data: must be a dictionary"):
            service.create_listing("nope")

    @pytest.mark.parametrize("field", ["seller_id", "title", "description"])
    def test_missing_required_field_raises(self, service, valid_data, field):
        del valid_data[field]

        with pytest.raises(ListingValidationError) as exc:
            service.create_listing(valid_data)

        assert exc.value.field == field

    @pytest.mark.parametrize("field", ["seller_id", "title", "description"])
    def test_blank_required_field_raises(self, service, valid_data, field):
        valid_data[field] = "   "

        with pytest.raises(ListingValidationError, match="must be a non-empty string"):
            service.create_listing(valid_data)

    def test_missing_category_raises(self, service, valid_data):
        del valid_data["category"]

        with pytest.raises(ListingValidationError, match="category: is required"):
            service.create_listing(valid_data)

    def test_invalid_category_lists_valid_values(self, service, valid_data):
        valid_data["category"] = "not-a-category"

        with pytest.raises(ListingValidationError, match="category") as exc:
            service.create_listing(valid_data)

        assert "digital_art" in str(exc.value)

    def test_missing_price_raises(self, service, valid_data):
        del valid_data["price"]

        with pytest.raises(ListingValidationError, match="price: is required"):
            service.create_listing(valid_data)

    def test_invalid_price_type_raises(self, service, valid_data):
        valid_data["price"] = 1500  # bare int, not a dict

        with pytest.raises(ListingValidationError, match="amount_cents"):
            service.create_listing(valid_data)

    def test_negative_amount_raises(self, service, valid_data):
        valid_data["price"] = {"amount_cents": -5, "currency": "USD"}

        with pytest.raises(ListingValidationError, match="amount_cents"):
            service.create_listing(valid_data)

    def test_non_int_amount_raises(self, service, valid_data):
        valid_data["price"] = {"amount_cents": "5.0", "currency": "USD"}

        with pytest.raises(ListingValidationError, match="amount_cents"):
            service.create_listing(valid_data)

    def test_price_missing_currency_defaults_to_usd(self, service, valid_data):
        valid_data["price"] = {"amount_cents": 500}

        assert service.create_listing(valid_data).price.currency == "USD"

    def test_price_bad_currency_raises(self, service, valid_data):
        valid_data["price"] = {"amount_cents": 500, "currency": "usd"}

        with pytest.raises(ListingValidationError, match="currency"):
            service.create_listing(valid_data)

    def test_invalid_status_lists_valid_values(self, service, valid_data):
        valid_data["status"] = "ghosted"

        with pytest.raises(ListingValidationError, match="status") as exc:
            service.create_listing(valid_data)

        assert "draft" in str(exc.value)

    def test_too_short_title_raises(self, service, valid_data):
        valid_data["title"] = "ab"

        with pytest.raises(ListingValidationError, match="at least 3"):
            service.create_listing(valid_data)

    def test_too_long_title_raises(self, service, valid_data):
        valid_data["title"] = "x" * 121

        with pytest.raises(ListingValidationError, match="cannot exceed 120"):
            service.create_listing(valid_data)

    def test_too_short_description_raises(self, service, valid_data):
        valid_data["description"] = "short"

        with pytest.raises(ListingValidationError, match="at least 10"):
            service.create_listing(valid_data)

    def test_too_long_description_raises(self, service, valid_data):
        valid_data["description"] = "x" * 5001

        with pytest.raises(ListingValidationError, match="cannot exceed 5000"):
            service.create_listing(valid_data)

    def test_tags_must_be_a_list(self, service, valid_data):
        valid_data["tags"] = "art"

        with pytest.raises(ListingValidationError, match="tags: must be a list"):
            service.create_listing(valid_data)

    def test_too_many_tags_raises(self, service, valid_data):
        valid_data["tags"] = [f"t{i}" for i in range(11)]

        with pytest.raises(ListingValidationError, match="cannot exceed 10 tags"):
            service.create_listing(valid_data)

    def test_non_string_tag_raises(self, service, valid_data):
        valid_data["tags"] = ["ok", 3]

        with pytest.raises(ListingValidationError, match="tag at index 1"):
            service.create_listing(valid_data)

    def test_media_urls_must_be_a_list(self, service, valid_data):
        valid_data["media_urls"] = "http://x"

        with pytest.raises(ListingValidationError, match="media_urls: must be a list"):
            service.create_listing(valid_data)

    def test_too_many_media_urls_raises(self, service, valid_data):
        valid_data["media_urls"] = [f"http://x/{i}" for i in range(21)]

        with pytest.raises(ListingValidationError, match="cannot exceed 20 URLs"):
            service.create_listing(valid_data)

    def test_blank_media_url_raises(self, service, valid_data):
        valid_data["media_urls"] = ["http://ok", "   "]

        with pytest.raises(ListingValidationError, match="URL at index 1"):
            service.create_listing(valid_data)

    def test_metadata_must_be_a_dict(self, service, valid_data):
        valid_data["metadata"] = ["not", "a", "dict"]

        with pytest.raises(ListingValidationError, match="metadata: must be a dictionary"):
            service.create_listing(valid_data)

    def test_failed_validation_does_not_persist(self, service, valid_data):
        valid_data["title"] = "ab"

        with pytest.raises(ListingValidationError):
            service.create_listing(valid_data)

        assert service.search_listings()["total"] == 0


# ---------------------------------------------------------------------------
# get_listing
# ---------------------------------------------------------------------------


class TestGetListing:
    """ListingService.get_listing."""

    def test_get_returns_created(self, service, valid_data):
        created = service.create_listing(valid_data)

        assert service.get_listing(created.id) is created

    @pytest.mark.parametrize("bad_id", ["", "   ", None])
    def test_blank_id_raises_validation_error(self, service, bad_id):
        with pytest.raises(ListingValidationError, match="listing_id"):
            service.get_listing(bad_id)

    def test_missing_id_raises_not_found(self, service):
        with pytest.raises(ListingNotFoundError, match="not found"):
            service.get_listing("does-not-exist")


# ---------------------------------------------------------------------------
# search_listings
# ---------------------------------------------------------------------------


class TestSearchListings:
    """ListingService.search_listings pagination and validation."""

    def test_empty_search_shape(self, service):
        result = service.search_listings()

        assert result == {"results": [], "total": 0, "limit": 20, "offset": 0}

    def test_returns_all(self, service, valid_data):
        service.create_listing(valid_data)
        service.create_listing(valid_data)

        result = service.search_listings()

        assert result["total"] == 2
        assert len(result["results"]) == 2

    def test_unknown_filter_key_raises(self, service):
        with pytest.raises(ListingValidationError, match="unknown filter keys"):
            service.search_listings(filters={"banana": 1})

    def test_allowed_filter_keys_do_not_raise(self, service):
        service.search_listings(filters={
            "category": "digital_art", "status": "draft",
            "seller_id": "s", "min_price_cents": 0, "max_price_cents": 9999,
        })

    def test_limit_must_be_positive_int(self, service):
        with pytest.raises(ListingValidationError, match="limit"):
            service.search_listings(limit=0)

    def test_limit_is_clamped_to_max(self, service, valid_data):
        service.create_listing(valid_data)

        assert service.search_listings(limit=500)["limit"] == 100

    def test_negative_offset_raises(self, service):
        with pytest.raises(ListingValidationError, match="offset"):
            service.search_listings(offset=-1)

    def test_offset_slices_results(self, service, valid_data):
        for i in range(3):
            service.create_listing({**valid_data, "seller_id": f"s-{i}"})

        page = service.search_listings(limit=2, offset=2)

        assert len(page["results"]) == 1
        assert page["offset"] == 2


# ---------------------------------------------------------------------------
# In-memory repository semantics
# ---------------------------------------------------------------------------


class TestInMemoryListingRepository:
    """The shipped in-memory repository used by the default service."""

    def _make(self, service, valid_data, **overrides):
        return service.create_listing({**valid_data, **overrides})

    def test_save_and_get_by_id(self, service, valid_data):
        repo = InMemoryListingRepository()
        listing = Listing(
            id="l-1", seller_id="s", title="t", description="d",
            category=ListingCategory.OTHER, price=Money(amount_cents=1),
        )

        assert repo.save(listing) is listing
        assert repo.get_by_id("l-1") is listing
        assert repo.get_by_id("nope") is None

    def test_search_matches_title_and_description(self, service, valid_data):
        self._make(service, valid_data, title="Ocean Waves")

        repo = service._repo
        assert repo.search("ocean", {}, limit=10, offset=0)
        assert repo.search("vibrant", {}, limit=10, offset=0)
        assert repo.search("zzz", {}, limit=10, offset=0) == []

    def test_search_filters_by_status(self, service, valid_data):
        self._make(service, valid_data, status="active")
        self._make(service, valid_data, status="draft")

        repo = service._repo
        active = repo.search("", {"status": "active"}, limit=10, offset=0)
        assert len(active) == 1
        assert active[0].status is ListingStatus.ACTIVE

    def test_search_filters_by_seller_and_category(self, service, valid_data):
        self._make(service, valid_data, seller_id="s-1", category="video")
        self._make(service, valid_data, seller_id="s-2", category="audio")

        repo = service._repo
        assert len(repo.search("", {"seller_id": "s-1"}, limit=10, offset=0)) == 1
        assert len(repo.search("", {"category": "audio"}, limit=10, offset=0)) == 1

    def test_count_is_filtered(self, service, valid_data):
        self._make(service, valid_data, status="active")
        self._make(service, valid_data, status="draft")

        repo = service._repo
        assert repo.count("", {"status": "active"}) == 1
        assert repo.count("", {}) == 2


# ---------------------------------------------------------------------------
# Module-level helpers (default service)
# ---------------------------------------------------------------------------


class TestModuleLevelHelpers:
    """create/get/list module helpers over the default in-memory service."""

    def test_create_listing_returns_dict(self, valid_data):
        result = create_listing(valid_data)

        assert isinstance(result, dict)
        assert result["title"] == "Sunset Overdrive Art"
        assert result["category"] == "digital_art"
        assert result["status"] == "draft"
        assert result["price"] == {"amount_cents": 1500, "currency": "USD"}
        assert "id" in result and "created_at" in result

    def test_create_then_get_round_trip(self, valid_data):
        created = create_listing(valid_data)

        fetched = get_listing(created["id"])

        assert fetched["id"] == created["id"]

    def test_get_missing_raises(self):
        with pytest.raises(ListingNotFoundError):
            get_listing("missing")

    def test_list_listings_returns_page(self, valid_data):
        create_listing(valid_data)

        page = list_listings({}, 1, 20)

        assert len(page) == 1
        assert page[0]["seller_id"] == "seller-001"

    def test_list_listings_filters_by_status(self, valid_data):
        create_listing({**valid_data, "status": "active"})
        create_listing({**valid_data, "status": "draft"})

        assert len(list_listings({"status": "active"}, 1, 20)) == 1

    def test_delete_missing_returns_false(self):
        assert delete_listing("missing") is False


# ---------------------------------------------------------------------------
# Regression guard: update_listing/delete_listing used to touch a non-existent
# repository attribute (InMemoryListingRepository stores under `_storage`, but
# listing_service read `_repo._listings`). Fixed in listing_service.py — these
# tests pin the fix so it cannot silently regress.
# ---------------------------------------------------------------------------


class TestUpdateDeleteRepositoryContract:
    """Regression coverage for a real src defect that was found and fixed.

    ``update_listing`` / ``delete_listing`` previously reached into
    ``service._repo._listings``, which the shipped ``InMemoryListingRepository``
    does not define (it uses ``_storage``), so both raised AttributeError against
    the default service. Fixed in ``listing_service.py``.
    """

    def test_update_listing_round_trip(self, valid_data):
        created = create_listing(valid_data)

        updated = update_listing(created["id"], {"title": "Brand New Title"})

        assert updated["id"] == created["id"]
        assert updated["title"] == "Brand New Title"

    def test_delete_listing_removes(self, valid_data):
        created = create_listing(valid_data)

        assert delete_listing(created["id"]) is True
        with pytest.raises(ListingNotFoundError):
            get_listing(created["id"])
