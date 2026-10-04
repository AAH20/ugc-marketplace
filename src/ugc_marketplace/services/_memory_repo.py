"""In-memory repository implementations for services."""
from __future__ import annotations

from typing import Any

from ugc_marketplace.services.listing_service import Listing, ListingRepository


class InMemoryListingRepository(ListingRepository):
    """In-memory implementation of ListingRepository for testing."""

    def __init__(self) -> None:
        self._storage: dict[str, Listing] = {}

    def save(self, listing: Listing) -> Listing:
        self._storage[listing.id] = listing
        return listing

    def get_by_id(self, listing_id: str) -> Listing | None:
        return self._storage.get(listing_id)

    def search(
        self,
        query: str,
        filters: dict[str, Any],
        limit: int,
        offset: int,
    ) -> list[Listing]:
        results = list(self._storage.values())
        if query:
            q = query.lower()
            results = [
                l for l in results
                if q in l.title.lower() or q in l.description.lower()
            ]
        if "status" in filters:
            results = [l for l in results if l.status.value == filters["status"]]
        if "seller_id" in filters:
            results = [l for l in results if l.seller_id == filters["seller_id"]]
        if "category" in filters:
            results = [l for l in results if l.category.value == filters["category"]]
        return results[offset : offset + limit]

    def count(
        self,
        query: str,
        filters: dict[str, Any],
    ) -> int:
        return len(self.search(query, filters, limit=10000, offset=0))
