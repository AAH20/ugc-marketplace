"""Tests for content_service module."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from ugc_marketplace.services.content_service import (
    Content,
    ContentFilters,
    ContentNotFoundError,
    ContentStatus,
    ContentType,
    ContentValidationError,
    PaginatedResult,
    PaginationParams,
    _content_store,
    create_content,
    delete_content,
    get_content,
    list_content,
    update_content,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_store():
    """Ensure the in-memory store is empty before and after each test."""
    _content_store.clear()
    yield
    _content_store.clear()


@pytest.fixture
def sample_content_data() -> dict:
    """Return a valid payload for create_content."""
    return {
        "title": "Test Content",
        "description": "A test content piece",
        "content_type": "image",
        "creator_id": "creator-001",
        "tags": ["test", "sample"],
        "metadata": {"key": "value"},
    }


@pytest.fixture
def created_content(sample_content_data) -> Content:
    """Create and return a Content object via create_content."""
    return create_content(sample_content_data)


@pytest.fixture
def multiple_contents() -> list[Content]:
    """Create several content items with varied attributes for filter tests."""
    items = []
    for i in range(5):
        data = {
            "title": f"Content {i}",
            "description": f"Description for content {i}",
            "content_type": ["image", "video", "text", "audio", "image"][i],
            "creator_id": f"creator-{i % 2}",
            "tags": [f"tag-{i}", "common"] if i % 2 == 0 else [f"tag-{i}"],
            "metadata": {},
        }
        items.append(create_content(data))
    return items


# ---------------------------------------------------------------------------
# Tests: create_content
# ---------------------------------------------------------------------------


class TestCreateContent:
    """Tests for create_content function."""

    def test_create_content_returns_content_instance(self, sample_content_data):
        result = create_content(sample_content_data)
        assert isinstance(result, Content)

    def test_create_content_generates_uuid(self, sample_content_data):
        result = create_content(sample_content_data)
        # Should not raise — validates UUID format
        uuid.UUID(result.id)

    def test_create_content_sets_default_status_draft(self, sample_content_data):
        result = create_content(sample_content_data)
        assert result.status == ContentStatus.DRAFT

    def test_create_content_strips_whitespace(self):
        data = {
            "title": "  Padded Title  ",
            "description": "  Padded description  ",
            "content_type": "text",
            "creator_id": "  creator-001  ",
        }
        result = create_content(data)
        assert result.title == "Padded Title"
        assert result.description == "Padded description"
        assert result.creator_id == "creator-001"

    def test_create_content_stores_in_store(self, sample_content_data):
        result = create_content(sample_content_data)
        assert result.id in _content_store
        assert _content_store[result.id] is result

    def test_create_content_missing_title_raises(self):
        data = {
            "description": "desc",
            "content_type": "image",
            "creator_id": "c1",
        }
        with pytest.raises(ContentValidationError, match="title"):
            create_content(data)

    def test_create_content_empty_title_raises(self):
        data = {
            "title": "",
            "description": "desc",
            "content_type": "image",
            "creator_id": "c1",
        }
        with pytest.raises(ContentValidationError, match="title"):
            create_content(data)

    def test_create_content_title_too_long_raises(self):
        data = {
            "title": "x" * 201,
            "description": "desc",
            "content_type": "image",
            "creator_id": "c1",
        }
        with pytest.raises(ContentValidationError, match="title"):
            create_content(data)

    def test_create_content_missing_description_raises(self):
        data = {
            "title": "Title",
            "content_type": "image",
            "creator_id": "c1",
        }
        with pytest.raises(ContentValidationError, match="description"):
            create_content(data)

    def test_create_content_description_too_long_raises(self):
        data = {
            "title": "Title",
            "description": "x" * 5001,
            "content_type": "image",
            "creator_id": "c1",
        }
        with pytest.raises(ContentValidationError, match="description"):
            create_content(data)

    def test_create_content_invalid_content_type_raises(self):
        data = {
            "title": "Title",
            "description": "desc",
            "content_type": "invalid_type",
            "creator_id": "c1",
        }
        with pytest.raises(ContentValidationError, match="content_type"):
            create_content(data)

    def test_create_content_missing_creator_id_raises(self):
        data = {
            "title": "Title",
            "description": "desc",
            "content_type": "image",
        }
        with pytest.raises(ContentValidationError, match="creator_id"):
            create_content(data)

    def test_create_content_empty_creator_id_raises(self):
        data = {
            "title": "Title",
            "description": "desc",
            "content_type": "image",
            "creator_id": "",
        }
        with pytest.raises(ContentValidationError, match="creator_id"):
            create_content(data)

    def test_create_content_tags_must_be_list(self):
        data = {
            "title": "Title",
            "description": "desc",
            "content_type": "image",
            "creator_id": "c1",
            "tags": "not-a-list",
        }
        with pytest.raises(ContentValidationError, match="tags"):
            create_content(data)

    def test_create_content_tags_must_be_strings(self):
        data = {
            "title": "Title",
            "description": "desc",
            "content_type": "image",
            "creator_id": "c1",
            "tags": [1, 2, 3],
        }
        with pytest.raises(ContentValidationError, match="tags"):
            create_content(data)

    def test_create_content_default_tags_empty_list(self, sample_content_data):
        # sample_content_data has tags; create without tags
        data = {k: v for k, v in sample_content_data.items() if k != "tags"}
        result = create_content(data)
        assert result.tags == []

    def test_create_content_default_metadata_empty_dict(self, sample_content_data):
        data = {k: v for k, v in sample_content_data.items() if k != "metadata"}
        result = create_content(data)
        assert result.metadata == {}

    def test_create_content_sets_timestamps(self, sample_content_data):
        before = datetime.now(timezone.utc)
        result = create_content(sample_content_data)
        after = datetime.now(timezone.utc)
        assert before <= result.created_at <= after
        assert before <= result.updated_at <= after

    def test_create_content_all_valid_types(self):
        for ct in ContentType:
            data = {
                "title": f"Title for {ct.value}",
                "description": "desc",
                "content_type": ct.value,
                "creator_id": "c1",
            }
            result = create_content(data)
            assert result.content_type == ct


# ---------------------------------------------------------------------------
# Tests: get_content
# ---------------------------------------------------------------------------


class TestGetContent:
    """Tests for get_content function."""

    def test_get_content_returns_content(self, created_content):
        result = get_content(created_content.id)
        assert result is created_content

    def test_get_content_returns_correct_fields(self, created_content):
        result = get_content(created_content.id)
        assert result.id == created_content.id
        assert result.title == created_content.title
        assert result.description == created_content.description
        assert result.content_type == created_content.content_type
        assert result.status == created_content.status
        assert result.creator_id == created_content.creator_id

    def test_get_content_not_found_raises(self):
        with pytest.raises(ContentNotFoundError):
            get_content("nonexistent-id")

    def test_get_content_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            get_content("")

    def test_get_content_whitespace_string_raises_value_error(self):
        with pytest.raises(ValueError):
            get_content("   ")

    def test_get_content_non_string_raises_value_error(self):
        with pytest.raises(ValueError):
            get_content(123)

    def test_get_content_none_raises_value_error(self):
        with pytest.raises(ValueError):
            get_content(None)

    def test_get_content_error_contains_id(self):
        with pytest.raises(ContentNotFoundError) as exc_info:
            get_content("missing-id")
        assert "missing-id" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Tests: list_content
# ---------------------------------------------------------------------------


class TestListContent:
    """Tests for list_content function."""

    def test_list_content_empty_store_returns_empty(self):
        result = list_content()
        assert isinstance(result, PaginatedResult)
        assert result.items == []
        assert result.total == 0
        assert result.total_pages == 0

    def test_list_content_returns_all_items(self, multiple_contents):
        result = list_content()
        assert result.total == 5
        assert len(result.items) == 5

    def test_list_content_default_pagination(self, multiple_contents):
        result = list_content()
        assert result.page == 1
        assert result.page_size == 20

    def test_list_content_filter_by_content_type(self, multiple_contents):
        filters = ContentFilters(content_type=ContentType.IMAGE)
        result = list_content(filters=filters)
        assert result.total == 2  # items 0 and 4 are images
        for item in result.items:
            assert item.content_type == ContentType.IMAGE

    def test_list_content_filter_by_status(self, multiple_contents):
        # All start as DRAFT
        filters = ContentFilters(status=ContentStatus.DRAFT)
        result = list_content(filters=filters)
        assert result.total == 5

    def test_list_content_filter_by_creator_id(self, multiple_contents):
        filters = ContentFilters(creator_id="creator-0")
        result = list_content(filters=filters)
        assert result.total == 3  # items 0, 2, 4
        for item in result.items:
            assert item.creator_id == "creator-0"

    def test_list_content_filter_by_tags(self, multiple_contents):
        filters = ContentFilters(tags=["common"])
        result = list_content(filters=filters)
        assert result.total == 3  # items 0, 2, 4 have "common" tag

    def test_list_content_filter_by_search_query_title(self, multiple_contents):
        filters = ContentFilters(search_query="Content 1")
        result = list_content(filters=filters)
        assert result.total == 1
        assert result.items[0].title == "Content 1"

    def test_list_content_filter_by_search_query_description(self, multiple_contents):
        filters = ContentFilters(search_query="Description for content 3")
        result = list_content(filters=filters)
        assert result.total == 1

    def test_list_content_search_query_case_insensitive(self, multiple_contents):
        filters = ContentFilters(search_query="CONTENT 2")
        result = list_content(filters=filters)
        assert result.total == 1

    def test_list_content_combined_filters(self, multiple_contents):
        filters = ContentFilters(
            content_type=ContentType.IMAGE,
            creator_id="creator-0",
        )
        result = list_content(filters=filters)
        assert result.total == 2  # items 0 and 4

    def test_list_content_pagination_first_page(self, multiple_contents):
        pagination = PaginationParams(page=1, page_size=2)
        result = list_content(pagination=pagination)
        assert len(result.items) == 2
        assert result.page == 1
        assert result.page_size == 2
        assert result.total_pages == 3

    def test_list_content_pagination_second_page(self, multiple_contents):
        pagination = PaginationParams(page=2, page_size=2)
        result = list_content(pagination=pagination)
        assert len(result.items) == 2
        assert result.page == 2

    def test_list_content_pagination_last_page_partial(self, multiple_contents):
        pagination = PaginationParams(page=3, page_size=2)
        result = list_content(pagination=pagination)
        assert len(result.items) == 1
        assert result.page == 3

    def test_list_content_pagination_beyond_last_page(self, multiple_contents):
        pagination = PaginationParams(page=10, page_size=2)
        result = list_content(pagination=pagination)
        assert len(result.items) == 0
        assert result.total == 5

    def test_list_content_sorted_newest_first(self, multiple_contents):
        result = list_content()
        items = result.items
        for i in range(len(items) - 1):
            assert items[i].created_at >= items[i + 1].created_at

    def test_list_content_invalid_page_raises(self, multiple_contents):
        with pytest.raises(ValueError):
            PaginationParams(page=0)

    def test_list_content_invalid_page_size_zero_raises(self, multiple_contents):
        with pytest.raises(ValueError):
            PaginationParams(page_size=0)

    def test_list_content_invalid_page_size_too_large_raises(self, multiple_contents):
        with pytest.raises(ValueError):
            PaginationParams(page_size=101)

    def test_list_content_no_filters_returns_all(self, multiple_contents):
        result = list_content(filters=ContentFilters())
        assert result.total == 5


# ---------------------------------------------------------------------------
# Tests: update_content
# ---------------------------------------------------------------------------


class TestUpdateContent:
    """Tests for update_content function."""

    def test_update_content_title(self, created_content):
        result = update_content(created_content.id, {"title": "New Title"})
        assert result.title == "New Title"

    def test_update_content_description(self, created_content):
        result = update_content(created_content.id, {"description": "New desc"})
        assert result.description == "New desc"

    def test_update_content_status(self, created_content):
        result = update_content(created_content.id, {"status": "published"})
        assert result.status == ContentStatus.PUBLISHED

    def test_update_content_tags(self, created_content):
        result = update_content(created_content.id, {"tags": ["new", "tags"]})
        assert result.tags == ["new", "tags"]

    def test_update_content_metadata(self, created_content):
        result = update_content(created_content.id, {"metadata": {"new": "data"}})
        assert result.metadata == {"new": "data"}

    def test_update_content_multiple_fields(self, created_content):
        result = update_content(
            created_content.id,
            {"title": "Updated", "status": "archived"},
        )
        assert result.title == "Updated"
        assert result.status == ContentStatus.ARCHIVED

    def test_update_content_strips_whitespace(self, created_content):
        result = update_content(created_content.id, {"title": "  Trimmed  "})
        assert result.title == "Trimmed"

    def test_update_content_updates_timestamp(self, created_content):
        original_updated = created_content.updated_at
        result = update_content(created_content.id, {"title": "New"})
        assert result.updated_at >= original_updated

    def test_update_content_not_found_raises(self):
        with pytest.raises(ContentNotFoundError):
            update_content("nonexistent", {"title": "New"})

    def test_update_content_empty_id_raises_value_error(self):
        with pytest.raises(ValueError):
            update_content("", {"title": "New"})

    def test_update_content_non_string_id_raises_value_error(self):
        with pytest.raises(ValueError):
            update_content(123, {"title": "New"})

    def test_update_content_non_dict_data_raises(self, created_content):
        with pytest.raises(ContentValidationError):
            update_content(created_content.id, "not a dict")

    def test_update_content_invalid_title_raises(self, created_content):
        with pytest.raises(ContentValidationError, match="title"):
            update_content(created_content.id, {"title": ""})

    def test_update_content_title_too_long_raises(self, created_content):
        with pytest.raises(ContentValidationError, match="title"):
            update_content(created_content.id, {"title": "x" * 201})

    def test_update_content_invalid_description_raises(self, created_content):
        with pytest.raises(ContentValidationError, match="description"):
            update_content(created_content.id, {"description": ""})

    def test_update_content_description_too_long_raises(self, created_content):
        with pytest.raises(ContentValidationError, match="description"):
            update_content(created_content.id, {"description": "x" * 5001})

    def test_update_content_invalid_status_raises(self, created_content):
        with pytest.raises(ContentValidationError, match="status"):
            update_content(created_content.id, {"status": "invalid_status"})

    def test_update_content_tags_not_list_raises(self, created_content):
        with pytest.raises(ContentValidationError, match="tags"):
            update_content(created_content.id, {"tags": "not-a-list"})

    def test_update_content_tags_non_string_raises(self, created_content):
        with pytest.raises(ContentValidationError, match="tags"):
            update_content(created_content.id, {"tags": [1, 2]})

    def test_update_content_metadata_not_dict_raises(self, created_content):
        with pytest.raises(ContentValidationError, match="metadata"):
            update_content(created_content.id, {"metadata": "not-a-dict"})

    def test_update_content_tags_none_clears(self, created_content):
        result = update_content(created_content.id, {"tags": None})
        assert result.tags == []

    def test_update_content_metadata_none_clears(self, created_content):
        result = update_content(created_content.id, {"metadata": None})
        assert result.metadata == {}

    def test_update_content_all_valid_statuses(self, created_content):
        for status in ContentStatus:
            result = update_content(created_content.id, {"status": status.value})
            assert result.status == status

    def test_update_content_returns_same_object(self, created_content):
        result = update_content(created_content.id, {"title": "New"})
        assert result is created_content


# ---------------------------------------------------------------------------
# Tests: delete_content
# ---------------------------------------------------------------------------


class TestDeleteContent:
    """Tests for delete_content function."""

    def test_delete_content_returns_true(self, created_content):
        result = delete_content(created_content.id)
        assert result is True

    def test_delete_content_removes_from_store(self, created_content):
        delete_content(created_content.id)
        assert created_content.id not in _content_store

    def test_delete_content_then_get_raises(self, created_content):
        delete_content(created_content.id)
        with pytest.raises(ContentNotFoundError):
            get_content(created_content.id)

    def test_delete_content_not_found_raises(self):
        with pytest.raises(ContentNotFoundError):
            delete_content("nonexistent-id")

    def test_delete_content_empty_id_raises_value_error(self):
        with pytest.raises(ValueError):
            delete_content("")

    def test_delete_content_whitespace_id_raises_value_error(self):
        with pytest.raises(ValueError):
            delete_content("   ")

    def test_delete_content_non_string_id_raises_value_error(self):
        with pytest.raises(ValueError):
            delete_content(123)

    def test_delete_content_none_id_raises_value_error(self):
        with pytest.raises(ValueError):
            delete_content(None)

    def test_delete_content_error_contains_id(self):
        with pytest.raises(ContentNotFoundError) as exc_info:
            delete_content("missing-id")
        assert "missing-id" in str(exc_info.value)

    def test_delete_content_only_removes_target(self, multiple_contents):
        target = multiple_contents[0]
        delete_content(target.id)
        assert target.id not in _content_store
        # Others still present
        assert len(_content_store) == 4

    def test_delete_content_idempotent_raises_on_second_call(self, created_content):
        delete_content(created_content.id)
        with pytest.raises(ContentNotFoundError):
            delete_content(created_content.id)
