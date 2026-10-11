"""Coverage-gap tests for :mod:`ugc_marketplace.services.category_service`
and :mod:`ugc_marketplace.services.tag_service`.

Both were zero-reference under ``tests/``.  Each wraps an injected repository,
so a small in-memory stub stands in for the database.
"""

from __future__ import annotations

import pytest

from ugc_marketplace.services.category_service import (
    CategoryNotFoundError,
    CategoryService,
    CategoryServiceError,
)
from ugc_marketplace.services.tag_service import (
    TagNotFoundError,
    TagService,
    TagServiceError,
)


# ---------------------------------------------------------------------------
# CategoryService
# ---------------------------------------------------------------------------


class _CategoryRepo:
    def __init__(self):
        self.rows: dict[str, dict] = {}
        self.fail = False

    def _maybe_fail(self):
        if self.fail:
            raise RuntimeError("db exploded")

    def get_category(self, category_id):
        self._maybe_fail()
        return self.rows.get(category_id)

    def list_categories(self, filters, offset, limit):
        self._maybe_fail()
        return list(self.rows.values())[offset : offset + limit]

    def create_category(self, data):
        self._maybe_fail()
        row = {"id": str(len(self.rows) + 1), **data}
        self.rows[row["id"]] = row
        return row

    def update_category(self, category_id, data):
        self._maybe_fail()
        if category_id not in self.rows:
            return None
        self.rows[category_id].update(data)
        return self.rows[category_id]

    def delete_category(self, category_id):
        self._maybe_fail()
        return self.rows.pop(category_id, None) is not None


def test_category_crud_roundtrip():
    repo = _CategoryRepo()
    service = CategoryService(repo)

    created = service.create_category({"name": "Art"})
    assert service.get_category(created["id"])["name"] == "Art"

    updated = service.update_category(created["id"], {"name": "Fine Art"})
    assert updated["name"] == "Fine Art"
    assert service.delete_category(created["id"]) is True


def test_category_listing_paginates():
    repo = _CategoryRepo()
    service = CategoryService(repo)
    for i in range(5):
        service.create_category({"name": f"cat-{i}"})

    page = service.list_categories({}, page=2, page_size=2)
    assert len(page) == 2


def test_category_not_found_paths():
    service = CategoryService(_CategoryRepo())
    with pytest.raises(CategoryNotFoundError):
        service.get_category("missing")
    with pytest.raises(CategoryNotFoundError):
        service.update_category("missing", {"name": "x"})
    with pytest.raises(CategoryNotFoundError):
        service.delete_category("missing")


def test_category_wraps_repository_failures():
    repo = _CategoryRepo()
    repo.fail = True
    service = CategoryService(repo)

    with pytest.raises(CategoryServiceError):
        service.get_category("any")
    with pytest.raises(CategoryServiceError):
        service.list_categories({}, 1, 10)
    with pytest.raises(CategoryServiceError):
        service.create_category({"name": "x"})


# ---------------------------------------------------------------------------
# TagService
# ---------------------------------------------------------------------------


class _TagRepo:
    def __init__(self):
        self.rows: dict[str, dict] = {}

    def get_tag(self, tag_id):
        return self.rows.get(tag_id)

    def list_tags(self, filters, offset, limit):
        return list(self.rows.values())[offset : offset + limit]

    def create_tag(self, data):
        row = {"id": str(len(self.rows) + 1), **data}
        self.rows[row["id"]] = row
        return row

    def update_tag(self, tag_id, data):
        self.rows[tag_id].update(data)
        return self.rows[tag_id]

    def delete_tag(self, tag_id):
        self.rows.pop(tag_id, None)


def test_tag_crud_roundtrip():
    service = TagService(_TagRepo())

    created = service.create_tag({"name": "art"})
    assert service.get_tag(created["id"])["name"] == "art"
    assert service.update_tag(created["id"], {"name": "painting"})["name"] == "painting"
    assert service.delete_tag(created["id"]) is True


def test_tag_create_requires_name():
    service = TagService(_TagRepo())
    with pytest.raises(ValueError):
        service.create_tag({})


def test_tag_listing_rejects_bad_pagination():
    service = TagService(_TagRepo())
    with pytest.raises(ValueError):
        service.list_tags({}, page=0, page_size=10)
    with pytest.raises(ValueError):
        service.list_tags({}, page=1, page_size=0)


def test_tag_not_found_paths():
    service = TagService(_TagRepo())
    with pytest.raises(TagNotFoundError):
        service.get_tag("missing")
    with pytest.raises(TagNotFoundError):
        service.update_tag("missing", {"name": "x"})
    with pytest.raises(TagNotFoundError):
        service.delete_tag("missing")


def test_tag_without_repository_is_inert_but_valid():
    # No repository: reads yield not-found, creation echoes the payload.
    service = TagService(db=None)
    with pytest.raises(TagNotFoundError):
        service.get_tag("anything")
    assert service.create_tag({"name": "echo"}) == {"name": "echo"}
    assert service.list_tags({}, 1, 10) == []
