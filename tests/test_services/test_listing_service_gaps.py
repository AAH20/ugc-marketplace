"""Coverage-gap tests for :mod:`ugc_marketplace.services.listing_service`.

These tests target the module-level convenience functions (``create_listing``,
``get_listing``, ``list_listings``, ``update_listing``, ``delete_listing``)
which are backed by the module-global default ``ListingService`` instance and
its ``InMemoryListingRepository``.  The default service is reset around every
test so the module-global store stays isolated.
"""

from __future__ import annotations

import pytest

from ugc_marketplace.services import listing_service as ls
from ugc_marketplace.services.listing_service import (
    ListingNotFoundError,
    ListingValidationError,
)


@pytest.fixture(autouse=True)
def _reset_default_service():
    """Give each test a pristine module-global default service."""
    ls._default_service = None
    yield
    ls._default_service = None


def _valid_payload(**overrides):
    payload = {
        "seller_id": "seller-1",
        "title": "Hand drawn art pack",
        "description": "A collection of hand drawn assets for games.",
        "category": "digital_art",
        "price": {"amount_cents": 2500, "currency": "USD"},
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# create_listing
# ---------------------------------------------------------------------------


def test_create_listing_returns_persisted_dict():
    created = ls.create_listing(_valid_payload())

    assert created["id"]
    assert created["seller_id"] == "seller-1"
    assert created["title"] == "Hand drawn art pack"
    assert created["category"] == "digital_art"
    assert created["status"] == "draft"
    assert created["price"] == {"amount_cents": 2500, "currency": "USD"}

    # And it is retrievable by ID.
    fetched = ls.get_listing(created["id"])
    assert fetched["id"] == created["id"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "ab"),  # below _TITLE_MIN_LEN
        ("description", "short"),  # below _DESC_MIN_LEN
        ("category", "not-a-category"),
        ("price", {"amount_cents": -1, "currency": "USD"}),
        ("price", {"amount_cents": 10, "currency": "usd"}),
    ],
)
def test_create_listing_rejects_invalid_fields(field, value):
    with pytest.raises(ListingValidationError):
        ls.create_listing(_valid_payload(**{field: value}))


# ---------------------------------------------------------------------------
# get_listing
# ---------------------------------------------------------------------------


def test_get_listing_missing_raises_not_found():
    with pytest.raises(ListingNotFoundError):
        ls.get_listing("does-not-exist")


# ---------------------------------------------------------------------------
# list_listings
# ---------------------------------------------------------------------------


def test_list_listings_paginates():
    for i in range(3):
        ls.create_listing(_valid_payload(title=f"Listing number {i}"))

    page1 = ls.list_listings({}, page=1, page_size=2)
    page2 = ls.list_listings({}, page=2, page_size=2)
    assert len(page1) == 2
    assert len(page2) == 1


def test_list_listings_filters_by_seller():
    ls.create_listing(_valid_payload(seller_id="seller-A"))
    ls.create_listing(_valid_payload(seller_id="seller-B"))

    results = ls.list_listings({"seller_id": "seller-A"}, page=1, page_size=10)
    assert len(results) == 1
    assert results[0]["seller_id"] == "seller-A"


# ---------------------------------------------------------------------------
# update_listing  (regression: default repo exposed no ``_listings`` attribute)
# ---------------------------------------------------------------------------


def test_update_listing_applies_changes_and_keeps_id():
    created = ls.create_listing(_valid_payload())

    updated = ls.update_listing(created["id"], {"title": "A brand new title"})

    assert updated["id"] == created["id"]
    assert updated["title"] == "A brand new title"
    # Change is visible through a fresh read too.
    assert ls.get_listing(created["id"])["title"] == "A brand new title"


def test_update_listing_missing_raises_not_found():
    with pytest.raises(ListingNotFoundError):
        ls.update_listing("nope", {"title": "Whatever"})


def test_update_listing_does_not_duplicate_record():
    """Updating must not leave an orphaned copy under a fresh random id."""
    created = ls.create_listing(_valid_payload())

    ls.update_listing(created["id"], {"title": "A brand new title"})

    assert len(ls.list_listings({}, page=1, page_size=10)) == 1


# ---------------------------------------------------------------------------
# delete_listing  (regression: default repo exposed no ``_listings`` attribute)
# ---------------------------------------------------------------------------


def test_delete_listing_removes_record():
    created = ls.create_listing(_valid_payload())

    assert ls.delete_listing(created["id"]) is True
    with pytest.raises(ListingNotFoundError):
        ls.get_listing(created["id"])


def test_delete_listing_missing_returns_false():
    assert ls.delete_listing("does-not-exist") is False

