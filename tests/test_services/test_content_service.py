"""Coverage-gap tests for :mod:`ugc_marketplace.services.content_service`.

``content_service`` had zero references anywhere under ``tests/``.  It keeps
content in a module-global store, which is reset around each test.
"""

from __future__ import annotations

import pytest

from ugc_marketplace.services import content_service as cs
from ugc_marketplace.services.content_service import (
    ContentFilters,
    ContentNotFoundError,
    ContentStatus,
    ContentType,
    PaginationParams,
    ContentValidationError,
)


@pytest.fixture(autouse=True)
def _clean_store():
    cs._content_store.clear()
    yield
    cs._content_store.clear()


def _payload(**overrides):
    data = {
        "title": "A reasonably long title",
        "description": "A description that is comfortably over ten chars.",
        "content_type": "video",
        "creator_id": "creator-1",
    }
    data.update(overrides)
    return data


def test_create_content_persists_and_is_retrievable():
    created = cs.create_content(_payload(tags=["a", "b"]))

    assert created.status is ContentStatus.DRAFT
    assert created.content_type is ContentType.VIDEO
    assert cs.get_content(created.id).id == created.id


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": ""},
        {"title": "x" * 201},
        {"description": ""},
        {"content_type": "hologram"},
        {"creator_id": ""},
        {"tags": "not-a-list"},
        {"tags": [1, 2]},
        {},
    ],
)
def test_create_content_validation_errors(overrides):
    data = _payload()
    if overrides == {}:
        del data["title"]
    else:
        data.update(overrides)
    with pytest.raises(ContentValidationError):
        cs.create_content(data)


def test_get_content_missing_raises():
    with pytest.raises(ContentNotFoundError):
        cs.get_content("missing-id")


def test_list_content_filters_and_pagination():
    cs.create_content(_payload(title="Alpha one", content_type="image", creator_id="c1"))
    cs.create_content(_payload(title="Beta two", content_type="video", creator_id="c2"))
    cs.create_content(_payload(title="Gamma three", content_type="image", creator_id="c1"))

    result = cs.list_content(
        ContentFilters(content_type=ContentType.IMAGE, creator_id="c1"),
        PaginationParams(page=1, page_size=10),
    )
    assert result.total == 2
    assert all(c.content_type is ContentType.IMAGE for c in result.items)


def test_list_content_search_query_and_total_pages():
    cs.create_content(_payload(title="Unique keyword here"))
    cs.create_content(_payload(title="Something else entirely"))

    result = cs.list_content(
        ContentFilters(search_query="unique"), PaginationParams(page=1, page_size=1)
    )
    assert result.total == 1
    assert result.total_pages == 1


def test_update_content_changes_status_and_validates():
    created = cs.create_content(_payload())

    updated = cs.update_content(created.id, {"status": "published", "tags": ["new"]})
    assert updated.status is ContentStatus.PUBLISHED
    assert updated.tags == ["new"]

    with pytest.raises(ContentValidationError):
        cs.update_content(created.id, {"status": "not-a-status"})


def test_update_content_missing_raises():
    with pytest.raises(ContentNotFoundError):
        cs.update_content("nope", {"title": "New"})


def test_delete_content_removes_and_returns_true():
    created = cs.create_content(_payload())
    assert cs.delete_content(created.id) is True
    with pytest.raises(ContentNotFoundError):
        cs.get_content(created.id)
