"""Category service for UGC marketplace."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CategoryNotFoundError(Exception):
    """Raised when a category is not found."""


class CategoryServiceError(Exception):
    """Raised when a category service operation fails."""


class CategoryService:
    """Service for managing categories in the UGC marketplace."""

    def __init__(self, db: Any = None) -> None:
        """Initialize the category service.

        Args:
            db: Database session or repository instance.
        """
        self._db = db

    def get_category(self, category_id: str) -> dict:
        """Get a category by its ID.

        Args:
            category_id: The unique identifier of the category.

        Returns:
            A dictionary containing the category data.

        Raises:
            CategoryNotFoundError: If no category exists with the given ID.
            CategoryServiceError: If the lookup fails for any other reason.
        """
        try:
            category = self._db.get_category(category_id)
            if category is None:
                raise CategoryNotFoundError(
                    f"Category with id '{category_id}' not found"
                )
            return category
        except CategoryNotFoundError:
            raise
        except Exception as exc:
            logger.error("Failed to get category %s: %s", category_id, exc)
            raise CategoryServiceError(
                f"Failed to retrieve category '{category_id}'"
            ) from exc

    def list_categories(
        self, filters: dict, page: int, page_size: int
    ) -> list[dict]:
        """List categories with optional filters and pagination.

        Args:
            filters: A dictionary of filter criteria (e.g., name, parent_id).
            page: The page number (1-indexed).
            page_size: The number of categories per page.

        Returns:
            A list of category dictionaries matching the filters.

        Raises:
            CategoryServiceError: If the listing operation fails.
        """
        try:
            offset = (page - 1) * page_size
            return self._db.list_categories(
                filters=filters, offset=offset, limit=page_size
            )
        except Exception as exc:
            logger.error("Failed to list categories: %s", exc)
            raise CategoryServiceError("Failed to list categories") from exc

    def create_category(self, data: dict) -> dict:
        """Create a new category.

        Args:
            data: A dictionary containing the category fields
                  (e.g., name, description, parent_id).

        Returns:
            A dictionary containing the newly created category data.

        Raises:
            CategoryServiceError: If the creation fails.
        """
        try:
            return self._db.create_category(data)
        except Exception as exc:
            logger.error("Failed to create category: %s", exc)
            raise CategoryServiceError("Failed to create category") from exc

    def update_category(self, category_id: str, data: dict) -> dict:
        """Update an existing category.

        Args:
            category_id: The unique identifier of the category to update.
            data: A dictionary containing the fields to update.

        Returns:
            A dictionary containing the updated category data.

        Raises:
            CategoryNotFoundError: If no category exists with the given ID.
            CategoryServiceError: If the update fails for any other reason.
        """
        try:
            updated = self._db.update_category(category_id, data)
            if updated is None:
                raise CategoryNotFoundError(
                    f"Category with id '{category_id}' not found"
                )
            return updated
        except CategoryNotFoundError:
            raise
        except Exception as exc:
            logger.error("Failed to update category %s: %s", category_id, exc)
            raise CategoryServiceError(
                f"Failed to update category '{category_id}'"
            ) from exc

    def delete_category(self, category_id: str) -> bool:
        """Delete a category by its ID.

        Args:
            category_id: The unique identifier of the category to delete.

        Returns:
            True if the category was successfully deleted.

        Raises:
            CategoryNotFoundError: If no category exists with the given ID.
            CategoryServiceError: If the deletion fails for any other reason.
        """
        try:
            deleted = self._db.delete_category(category_id)
            if not deleted:
                raise CategoryNotFoundError(
                    f"Category with id '{category_id}' not found"
                )
            return True
        except CategoryNotFoundError:
            raise
        except Exception as exc:
            logger.error("Failed to delete category %s: %s", category_id, exc)
            raise CategoryServiceError(
                f"Failed to delete category '{category_id}'"
            ) from exc
