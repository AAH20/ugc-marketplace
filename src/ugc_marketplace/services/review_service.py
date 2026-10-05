"""Review service for managing UGC marketplace reviews."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select, update

from ugc_marketplace.database.manager import get_db_manager
from ugc_marketplace.models import Review

logger = logging.getLogger(__name__)


class ReviewNotFoundError(Exception):
    """Raised when a review is not found."""


class ReviewValidationError(Exception):
    """Raised when review data is invalid."""


def _review_to_dict(review: Review) -> dict[str, Any]:
    """Convert a Review ORM object to a dictionary."""
    return {
        "id": str(review.id),
        "transaction_id": str(review.transaction_id),
        "reviewer_id": str(review.reviewer_id),
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at.isoformat() if review.created_at else None,
        "updated_at": review.updated_at.isoformat() if review.updated_at else None,
    }


def _run_async(coro: Any) -> Any:
    """Run an async coroutine from sync code.

    If called from within a running event loop, executes the coroutine
    in a separate thread to avoid "asyncio.run() cannot be called from a
    running event loop" errors.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — safe to use asyncio.run()
        return asyncio.run(coro)
    else:
        # Already in an async context — run in a new thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()


def get_review(review_id: str) -> dict[str, Any]:
    """Get a review by its ID.

    Args:
        review_id: The unique identifier of the review.

    Returns:
        A dictionary containing the review data.

    Raises:
        ReviewNotFoundError: If no review exists with the given ID.
        ReviewValidationError: If the review_id is empty or invalid.
    """
    if not review_id or not isinstance(review_id, str):
        raise ReviewValidationError("review_id must be a non-empty string")

    async def _get():
        manager = get_db_manager()
        async with manager.session() as session:
            try:
                review_uuid = uuid.UUID(review_id)
            except ValueError:
                raise ReviewNotFoundError(f"Review with id '{review_id}' not found")
            result = await session.execute(
                select(Review).where(Review.id == review_uuid)
            )
            review = result.scalar_one_or_none()
            if review is None:
                raise ReviewNotFoundError(f"Review with id '{review_id}' not found")
            return _review_to_dict(review)

    try:
        return _run_async(_get())
    except ReviewNotFoundError:
        raise
    except Exception as e:
        logger.error("Error fetching review %s: %s", review_id, e)
        raise


def list_reviews(filters: dict[str, Any], page: int, page_size: int) -> list[dict[str, Any]]:
    """List reviews with optional filters and pagination.

    Args:
        filters: A dictionary of filter criteria (e.g., {"user_id": "123"}).
            Supported keys: reviewer_id, transaction_id, rating.
        page: The page number (1-indexed).
        page_size: The number of reviews per page.

    Returns:
        A list of review dictionaries matching the filters.

    Raises:
        ReviewValidationError: If page or page_size is invalid.
    """
    if not isinstance(page, int) or page < 1:
        raise ReviewValidationError("page must be a positive integer")
    if not isinstance(page_size, int) or page_size < 1:
        raise ReviewValidationError("page_size must be a positive integer")
    if not isinstance(filters, dict):
        raise ReviewValidationError("filters must be a dictionary")

    async def _list():
        manager = get_db_manager()
        async with manager.session() as session:
            query = select(Review)

            # Apply filters
            if "reviewer_id" in filters:
                try:
                    reviewer_uuid = uuid.UUID(filters["reviewer_id"])
                    query = query.where(Review.reviewer_id == reviewer_uuid)
                except ValueError:
                    pass
            if "transaction_id" in filters:
                try:
                    txn_uuid = uuid.UUID(filters["transaction_id"])
                    query = query.where(Review.transaction_id == txn_uuid)
                except ValueError:
                    pass
            if "rating" in filters:
                try:
                    rating = int(filters["rating"])
                    query = query.where(Review.rating == rating)
                except (ValueError, TypeError):
                    pass

            # Apply pagination
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)

            result = await session.execute(query)
            reviews = result.scalars().all()
            return [_review_to_dict(r) for r in reviews]

    try:
        return _run_async(_list())
    except Exception as e:
        logger.error("Error listing reviews: %s", e)
        raise


def create_review(data: dict[str, Any]) -> dict[str, Any]:
    """Create a new review.

    Args:
        data: A dictionary containing the review data to create.
            Required fields: transaction_id, reviewer_id, rating.
            Optional fields: comment.

    Returns:
        A dictionary containing the created review data.

    Raises:
        ReviewValidationError: If the data is invalid or missing required fields.
    """
    if not isinstance(data, dict):
        raise ReviewValidationError("data must be a dictionary")

    # Validate required fields
    required = ["transaction_id", "reviewer_id", "rating"]
    missing = [f for f in required if f not in data]
    if missing:
        raise ReviewValidationError(f"Missing required fields: {', '.join(missing)}")

    try:
        rating = int(data["rating"])
        if rating < 1 or rating > 5:
            raise ReviewValidationError("rating must be between 1 and 5")
    except (ValueError, TypeError):
        raise ReviewValidationError("rating must be an integer between 1 and 5")

    async def _create():
        manager = get_db_manager()
        async with manager.session() as session:
            try:
                txn_uuid = uuid.UUID(data["transaction_id"])
                reviewer_uuid = uuid.UUID(data["reviewer_id"])
            except ValueError as e:
                raise ReviewValidationError(f"Invalid UUID: {e}")

            review = Review(
                transaction_id=txn_uuid,
                reviewer_id=reviewer_uuid,
                rating=rating,
                comment=data.get("comment"),
            )
            session.add(review)
            await session.flush()
            await session.refresh(review)
            return _review_to_dict(review)

    try:
        return _run_async(_create())
    except ReviewValidationError:
        raise
    except Exception as e:
        logger.error("Error creating review: %s", e)
        raise


def update_review(review_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Update an existing review.

    Args:
        review_id: The unique identifier of the review to update.
        data: A dictionary containing the fields to update.

    Returns:
        A dictionary containing the updated review data.

    Raises:
        ReviewNotFoundError: If no review exists with the given ID.
        ReviewValidationError: If the review_id or data is invalid.
    """
    if not review_id or not isinstance(review_id, str):
        raise ReviewValidationError("review_id must be a non-empty string")
    if not isinstance(data, dict):
        raise ReviewValidationError("data must be a dictionary")

    async def _update():
        manager = get_db_manager()
        async with manager.session() as session:
            try:
                review_uuid = uuid.UUID(review_id)
            except ValueError:
                raise ReviewNotFoundError(f"Review with id '{review_id}' not found")

            # Build update values
            update_values: dict[str, Any] = {}
            if "rating" in data:
                try:
                    rating = int(data["rating"])
                    if rating < 1 or rating > 5:
                        raise ReviewValidationError("rating must be between 1 and 5")
                    update_values["rating"] = rating
                except (ValueError, TypeError):
                    raise ReviewValidationError("rating must be an integer between 1 and 5")
            if "comment" in data:
                update_values["comment"] = data["comment"]

            if not update_values:
                # No fields to update — return current state
                result = await session.execute(
                    select(Review).where(Review.id == review_uuid)
                )
                review = result.scalar_one_or_none()
                if review is None:
                    raise ReviewNotFoundError(f"Review with id '{review_id}' not found")
                return _review_to_dict(review)

            update_values["updated_at"] = datetime.now(UTC)

            result = await session.execute(
                update(Review)
                .where(Review.id == review_uuid)
                .values(**update_values)
                .returning(Review)
            )
            review = result.scalar_one_or_none()
            if review is None:
                raise ReviewNotFoundError(f"Review with id '{review_id}' not found")
            return _review_to_dict(review)

    try:
        return _run_async(_update())
    except (ReviewNotFoundError, ReviewValidationError):
        raise
    except Exception as e:
        logger.error("Error updating review %s: %s", review_id, e)
        raise


def delete_review(review_id: str) -> bool:
    """Delete a review by its ID.

    Args:
        review_id: The unique identifier of the review to delete.

    Returns:
        True if the review was successfully deleted.

    Raises:
        ReviewNotFoundError: If no review exists with the given ID.
        ReviewValidationError: If the review_id is empty or invalid.
    """
    if not review_id or not isinstance(review_id, str):
        raise ReviewValidationError("review_id must be a non-empty string")

    async def _delete():
        manager = get_db_manager()
        async with manager.session() as session:
            try:
                review_uuid = uuid.UUID(review_id)
            except ValueError:
                raise ReviewNotFoundError(f"Review with id '{review_id}' not found")

            result = await session.execute(
                delete(Review).where(Review.id == review_uuid)
            )
            if result.rowcount == 0:
                raise ReviewNotFoundError(f"Review with id '{review_id}' not found")
            return True

    try:
        return _run_async(_delete())
    except ReviewNotFoundError:
        raise
    except Exception as e:
        logger.error("Error deleting review %s: %s", review_id, e)
        raise


class ReviewService:
    """Service class for review operations.

    Wraps the module-level review functions with a class-based interface
    that accepts a database session.
    """

    def __init__(self, db: Any) -> None:
        """Initialize the ReviewService.

        Args:
            db: Database session for executing queries.
        """
        self.db = db

    def get_review(self, review_id: str) -> dict[str, Any]:
        """Get a review by its ID."""
        return get_review(review_id)

    def list_reviews(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict[str, Any]]:
        """List reviews with optional filters and pagination."""
        if filters is None:
            filters = {}
        return list_reviews(filters, page, page_size)

    def create_review(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new review."""
        return create_review(data)

    def update_review(self, review_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing review."""
        return update_review(review_id, data)

    def delete_review(self, review_id: str) -> bool:
        """Delete a review by its ID."""
        return delete_review(review_id)
