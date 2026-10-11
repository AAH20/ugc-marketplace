"""Unit tests for the search service module.

Targets the real public API of ``ugc_marketplace.services.search_service``:

* ``SearchFilters`` / ``SearchResult`` / ``SearchResponse`` / ``Suggestion``
* ``SearchService`` with an injected backend (dependency inversion)
* ``SearchServiceError`` / ``SearchBackendError``
* the module-level ``search_content`` / ``search_creators`` /
  ``get_search_suggestions`` helpers backed by the default service

No backend is required: the service accepts any object exposing
``search_content`` / ``search_creators`` / ``suggestions``. A tiny fake
backend exercises the mapping and error-wrapping paths.
"""
from __future__ import annotations

import pytest

from ugc_marketplace.services import search_service as ss
from ugc_marketplace.services.search_service import (
    SearchBackendError,
    SearchFilters,
    SearchResponse,
    SearchResult,
    SearchService,
    SearchServiceError,
    Suggestion,
    get_search_suggestions,
    search_content,
    search_creators,
)


class FakeBackend:
    """Minimal stand-in for a real search backend (Elasticsearch/Algolia)."""

    def __init__(self, content=None, creators=None, suggestions=None, raises=None):
        self._content = content or []
        self._creators = creators or []
        self._suggestions = suggestions or []
        self._raises = raises
        self.calls: list[tuple] = []

    def _maybe_raise(self):
        if self._raises is not None:
            raise self._raises

    def search_content(self, query, filters):
        self.calls.append(("content", query, filters))
        self._maybe_raise()
        return self._content

    def search_creators(self, query, filters):
        self.calls.append(("creators", query, filters))
        self._maybe_raise()
        return self._creators

    def suggestions(self, query):
        self.calls.append(("suggestions", query))
        self._maybe_raise()
        return self._suggestions


# ---------------------------------------------------------------------------
# SearchFilters validation
# ---------------------------------------------------------------------------


class TestSearchFilters:
    """``SearchFilters.__post_init__`` guards the query contract."""

    def test_defaults(self):
        f = SearchFilters()

        assert f.category is None
        assert f.min_price is None
        assert f.max_price is None
        assert f.rating_min is None
        assert f.tags == []
        assert f.sort_by == "relevance"
        assert f.limit == 20
        assert f.offset == 0

    @pytest.mark.parametrize("limit", [0, -1, 101, 1000])
    def test_limit_out_of_range_raises(self, limit):
        with pytest.raises(ValueError, match="limit must be between 1 and 100"):
            SearchFilters(limit=limit)

    @pytest.mark.parametrize("limit", [1, 50, 100])
    def test_limit_boundaries_accepted(self, limit):
        assert SearchFilters(limit=limit).limit == limit

    def test_negative_offset_raises(self):
        with pytest.raises(ValueError, match="offset must be non-negative"):
            SearchFilters(offset=-1)

    def test_min_price_greater_than_max_price_raises(self):
        with pytest.raises(ValueError, match="min_price cannot exceed max_price"):
            SearchFilters(min_price=100.0, max_price=10.0)

    def test_equal_min_and_max_price_is_allowed(self):
        assert SearchFilters(min_price=10.0, max_price=10.0).min_price == 10.0

    @pytest.mark.parametrize("rating", [-0.1, 5.1, 10])
    def test_rating_min_out_of_range_raises(self, rating):
        with pytest.raises(ValueError, match="rating_min must be between 0 and 5"):
            SearchFilters(rating_min=rating)

    @pytest.mark.parametrize("rating", [0, 2.5, 5])
    def test_rating_min_boundaries_accepted(self, rating):
        assert SearchFilters(rating_min=rating).rating_min == rating


class TestSearchServiceWithNoBackend:
    """With no backend the service returns empty, well-formed responses."""

    def test_content_search_returns_empty_response(self):
        response = SearchService().search_content("video")

        assert isinstance(response, SearchResponse)
        assert response.results == []
        assert response.total == 0
        assert response.query == "video"
        assert isinstance(response.filters, SearchFilters)

    def test_creator_search_returns_empty_response(self):
        response = SearchService().search_creators("alice")

        assert response.results == []
        assert response.total == 0
        assert response.query == "alice"

    def test_suggestions_return_empty_list(self):
        assert SearchService().get_search_suggestions("vi") == []

    @pytest.mark.parametrize("query", ["", "   ", None])
    def test_blank_content_query_raises(self, query):
        with pytest.raises(ValueError, match="query must be a non-empty string"):
            SearchService().search_content(query)

    @pytest.mark.parametrize("query", ["", "   ", None])
    def test_blank_creator_query_raises(self, query):
        with pytest.raises(ValueError, match="query must be a non-empty string"):
            SearchService().search_creators(query)

    @pytest.mark.parametrize("query", ["", "   ", None])
    def test_blank_suggestion_query_raises(self, query):
        with pytest.raises(ValueError, match="query must be a non-empty string"):
            SearchService().get_search_suggestions(query)


class TestSearchServiceWithBackend:
    """Mapping and delegation against an injected backend."""

    def test_content_results_are_mapped(self):
        backend = FakeBackend(content=[
            {"id": "c-1", "title": "Sunset", "type": "video", "score": 0.9,
             "metadata": {"creator": "amy"}},
            {"id": "c-2", "title": "Dawn"},
        ])

        response = SearchService(backend).search_content("sky")

        assert all(isinstance(r, SearchResult) for r in response.results)
        first = response.results[0]
        assert (first.id, first.title, first.type) == ("c-1", "Sunset", "video")
        assert first.score == 0.9
        assert first.metadata == {"creator": "amy"}
        assert response.total == 2

    def test_content_result_defaults_when_fields_absent(self):
        backend = FakeBackend(content=[{"id": "c-1", "title": "Dawn"}])

        result = SearchService(backend).search_content("sky").results[0]

        assert result.type == "content"
        assert result.score == 0.0
        assert result.metadata == {}

    def test_content_score_is_coerced_to_float(self):
        backend = FakeBackend(content=[{"id": "c-1", "title": "Dawn", "score": "0.5"}])

        assert isinstance(SearchService(backend).search_content("sky").results[0].score, float)

    def test_query_is_stripped_before_backend_call(self):
        backend = FakeBackend()

        service = SearchService(backend)
        service.search_content("  sky  ")

        assert backend.calls[0][1] == "sky"

    def test_filters_are_forwarded_as_dict(self):
        backend = FakeBackend()

        SearchService(backend).search_content("sky", SearchFilters(category="video"))

        _, _, forwarded = backend.calls[0]
        assert forwarded["category"] == "video"

    def test_creator_results_use_name_as_title(self):
        backend = FakeBackend(creators=[
            {"id": "u-1", "name": "Alice", "score": 1.5, "metadata": {"tier": "gold"}},
        ])

        result = SearchService(backend).search_creators("ali").results[0]

        assert result.title == "Alice"
        assert result.type == "creator"
        assert result.score == 1.5

    def test_suggestions_are_mapped(self):
        backend = FakeBackend(suggestions=[
            {"text": "video editing", "type": "content", "highlight": "<b>video</b>"},
            {"text": "videos"},
        ])

        suggestions = SearchService(backend).get_search_suggestions("vi")

        assert all(isinstance(s, Suggestion) for s in suggestions)
        assert suggestions[0].text == "video editing"
        assert suggestions[0].highlight == "<b>video</b>"
        assert suggestions[1].type == "content"
        assert suggestions[1].highlight is None

    def test_empty_query_not_sent_to_backend(self):
        backend = FakeBackend()

        with pytest.raises(ValueError):
            SearchService(backend).search_content("")

        assert backend.calls == []


class TestSearchErrorHandling:
    """Backend failures are wrapped or propagated appropriately."""

    def test_generic_backend_error_is_wrapped(self):
        backend = FakeBackend(raises=RuntimeError("backend down"))

        with pytest.raises(SearchBackendError, match="Content search failed"):
            SearchService(backend).search_content("x")

    def test_existing_search_backend_error_propagates_unchanged(self):
        boom = SearchBackendError("already typed")
        backend = FakeBackend(raises=boom)

        with pytest.raises(SearchBackendError) as exc:
            SearchService(backend).search_content("x")

        assert exc.value is boom

    def test_creator_generic_error_is_wrapped(self):
        backend = FakeBackend(raises=RuntimeError("nope"))

        with pytest.raises(SearchBackendError, match="Creator search failed"):
            SearchService(backend).search_creators("x")

    def test_suggestion_generic_error_is_wrapped(self):
        backend = FakeBackend(raises=RuntimeError("nope"))

        with pytest.raises(SearchBackendError, match="Suggestion fetch failed"):
            SearchService(backend).get_search_suggestions("x")

    def test_backend_error_is_a_search_service_error(self):
        assert issubclass(SearchBackendError, SearchServiceError)
        assert issubclass(SearchServiceError, Exception)


class TestModuleLevelHelpers:
    """The module-level helpers delegate to the default service."""

    def test_search_content_returns_response(self):
        response = search_content("something")

        assert isinstance(response, SearchResponse)
        assert response.query == "something"

    def test_search_creators_returns_response(self):
        response = search_creators("someone")

        assert isinstance(response, SearchResponse)
        assert response.query == "someone"

    def test_get_search_suggestions_returns_list(self):
        assert get_search_suggestions("x") == []

    def test_helpers_use_the_module_default_service(self):
        assert ss._default_service is not None
        response = ss.search_content("x")
        # the default service has no backend, so responses are empty
        assert response.results == []
