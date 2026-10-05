"""SQLAlchemy 2.0 models for the UGC Marketplace."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""


from ugc_marketplace.models.category import Category  # noqa: E402
from ugc_marketplace.models.content import Content  # noqa: E402
from ugc_marketplace.models.creator import Creator  # noqa: E402
from ugc_marketplace.models.listing import Listing  # noqa: E402
from ugc_marketplace.models.notification import Notification  # noqa: E402
from ugc_marketplace.models.payment import Payment  # noqa: E402
from ugc_marketplace.models.review import Review  # noqa: E402
from ugc_marketplace.models.transaction import Transaction  # noqa: E402

__all__ = [
    "Base",
    "Category",
    "Content",
    "Creator",
    "Listing",
    "Notification",
    "Payment",
    "Review",
    "Transaction",
]
