"""Tag service for managing tags in the UGC marketplace."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TagNotFoundError(Exception):
    """Raised when a tag with the given ID does not exist."""


class TagServiceError(Exception):
    """Raised when a tag service operation fails."""


class TagService:
    """Service for managing tags in the UGC marketplace."""

    def __init__(self, db: Any = None) -> None:
        """Initialize the TagService.

        Args:
            db: Database session or connection object.
        """
        self._db = db

    def get_tag(self, tag_id: str) -> dict:
        """Get a tag by its ID.

        Args:
            tag_id: The unique identifier of the tag.

        Returns:
            A dictionary containing the tag data.

        Raises:
            TagNotFoundError: If no tag exists with the given ID.
            TagServiceError: If the database query fails.
        """
        try:
            tag = self._db.get_tag(tag_id) if self._db else None
            if tag is None:
                raise TagNotFoundError(f"Tag with ID '{tag_id}' not found")
            return dict(tag)
        except TagNotFoundError:
            raise
        except Exception as exc:
            logger.error("Failed to get tag %s: %s", tag_id, exc)
            raise TagServiceError(f"Failed to get tag: {exc}") from exc

    def list_tags(self, filters: dict, page: int, page_size: int) -> list[dict]:
        """List tags with optional filters and pagination.

        Args:
            filters: A dictionary of filter criteria (e.g., {"name": "art"}).
            page: The page number (1-indexed).
            page_size: The number of tags per page.

        Returns:
            A list of dictionaries containing tag data.

        Raises:
            TagServiceError: If the database query fails.
            ValueError: If page or page_size is less than 1.
        """
        if page < 1:
            raise ValueError("page must be >= 1")
        if page_size < 1:
            raise ValueError("page_size must be >= 1")

        try:
            offset = (page - 1) * page_size
            tags = (
                self._db.list_tags(filters=filters, offset=offset, limit=page_size)
                if self._db
                else []
            )
            return [dict(tag) for tag in tags]
        except Exception as exc:
            logger.error("Failed to list tags: %s", exc)
            raise TagServiceError(f"Failed to list tags: {exc}") from exc

    def create_tag(self, data: dict) -> dict:
        """Create a new tag.

        Args:
            data: A dictionary containing the tag data (e.g., {"name": "art"}).

        Returns:
            A dictionary containing the created tag data.

        Raises:
            TagServiceError: If the tag creation fails.
            ValueError: If required fields are missing.
        """
        if not data or "name" not in data:
            raise ValueError("Tag data must include a 'name' field")

        try:
            tag = self._db.create_tag(data) if self._db else data
            return dict(tag)
        except Exception as exc:
            logger.error("Failed to create tag: %s", exc)
            raise TagServiceError(f"Failed to create tag: {exc}") from exc

    def update_tag(self, tag_id: str, data: dict) -> dict:
        """Update an existing tag.

        Args:
            tag_id: The unique identifier of the tag to update.
            data: A dictionary containing the fields to update.

        Returns:
            A dictionary containing the updated tag data.

        Raises:
            TagNotFoundError: If no tag exists with the given ID.
            TagServiceError: If the update fails.
        """
        try:
            existing = self._db.get_tag(tag_id) if self._db else None
            if existing is None:
                raise TagNotFoundError(f"Tag with ID '{tag_id}' not found")

            updated = self._db.update_tag(tag_id, data) if self._db else data
            return dict(updated)
        except TagNotFoundError:
            raise
        except Exception as exc:
            logger.error("Failed to update tag %s: %s", tag_id, exc)
            raise TagServiceError(f"Failed to update tag: {exc}") from exc

    def delete_tag(self, tag_id: str) -> bool:
        """Delete a tag by its ID.

        Args:
            tag_id: The unique identifier of the tag to delete.

        Returns:
            True if the tag was successfully deleted.

        Raises:
            TagNotFoundError: If no tag exists with the given ID.
            TagServiceError: If the deletion fails.
        """
        try:
            existing = self._db.get_tag(tag_id) if self._db else None
            if existing is None:
                raise TagNotFoundError(f"Tag with ID '{tag_id}' not found")

            self._db.delete_tag(tag_id) if self._db else None
            return True
        except TagNotFoundError:
            raise
        except Exception as exc:
            logger.error("Failed to delete tag %s: %s", tag_id, exc)
            raise TagServiceError(f"Failed to delete tag: {exc}") from exc
