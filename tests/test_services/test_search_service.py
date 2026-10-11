"""Coverage-gap tests for :mod:`ugc_marketplace.services.search_service`.

``search_service`` had zero references anywhere under ``tests/``.  Its
behaviour is deterministic and driven entirely through an injectable backend,
so a lightweight stub stands in for Elasticsearch/Algolia.
"""

from __future__ import annotations

import pytest

from ugc_marketplace.services import search_service as ss
from ugc_marketplace.services.search_service import (
    SearchBackendError,
    SearchFilters,
    SearchService,
)


class _StubBackend:
    def __init__(self, content=None, creators=None, suggestions=None, boom=False):
        self._content = content or []
        self._creators = creators or []
        self._suggestions = suggestions or []
        self._boom = boom

    def search_content(self, query, filters):
        if self._boom:
            raise RuntimeError("backend down")
        return self._content

    def search_creators(self, query, filters):
        return self._creators

    def suggestions(self, query):
        return self._suggestions


# ---------------------------------------------------------------------------
# SearchFilters validation
# ---------------------------------------------------------------------------


def test_filters_reject_out_of_range_values():
    with pytest.raises(ValueError):
        SearchFilters(limit=0)
    with pytest.raises(ValueError):
        SearchFilters(limit=101)
    with pytest.raises(ValueError):
        SearchFilters(offset=-1)
    with pytest.raises(ValueError):
        SearchFilters(min_price=10, max_price=5)
    with pytest.raises(ValueError):
        SearchFilters(rating_min=9)


def test_filters_defaults_are_valid():
    filters = SearchFilters()
    assert filters.limit == 20
    assert filters.sort_by == "relevance"


# ---------------------------------------------------------------------------
# search_content
# ---------------------------------------------------------------------------


def test_search_content_maps_backend_rows():
    backend = _StubBackend(
        content=[{"id": "1", "title": "Art", "score": 0.9, "metadata": {"k": "v"}}]
    )
    service = SearchService(backend)

    response = service.search_content("art")

    assert response.total == 1
    assert response.query == "art"
    assert response.results[0].id == "1"
    assert response.results[0].type == "content"
    assert response.results[0].metadata == {"k": "v"}


def test_search_content_without_backend_returns_empty():
    assert SearchService().search_content("anything").total == 0


def test_search_content_rejects_blank_query():
    with pytest.raises(ValueError):
        SearchService().search_content("   ")


def test_search_content_wraps_backend_failure():
    service = SearchService(_StubBackend(boom=True))
    with pytest.raises(SearchBackendError):
        service.search_content("art")


# ---------------------------------------------------------------------------
# search_creators
# ---------------------------------------------------------------------------


def test_search_creators_maps_name_to_title():
    backend = _StubBackend(creators=[{"id": "c1", "name": "Ada", "score": 0.5}])
    response = SearchService(backend).search_creators("ada")

    assert response.total == 1
    assert response.results[0].type == "creator"
    assert response.results[0].title == "Ada"


def test_search_creators_rejects_blank_query():
    with pytest.raises(ValueError):
        SearchService().search_creators("")


# ---------------------------------------------------------------------------
# suggestions + module-level helpers
# ---------------------------------------------------------------------------


def test_get_search_suggestions_maps_rows():
    backend = _StubBackend(suggestions=[{"text": "art prints", "highlight": "art"}])
    suggestions = SearchService(backend).get_search_suggestions("ar")

    assert suggestions[0].text == "art prints"
    assert suggestions[0].highlight == "art"


def test_module_level_helpers_use_default_service():
    # Default service has no backend, so results are empty but well-formed.
    assert ss.search_content("hello").total == 0
    assert ss.search_creators("hello").total == 0
    assert ss.get_search_suggestions("he") == []
