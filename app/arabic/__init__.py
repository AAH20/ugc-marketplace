"""Arabic content generation module."""

from app.arabic.dialects import (
    ArabicDialect,
    DialectDetector,
    get_dialect,
    get_dialect_region,
    get_dialect_greeting,
    is_valid_dialect,
)

__all__ = [
    "ArabicDialect",
    "DialectDetector",
    "get_dialect",
    "get_dialect_region",
    "get_dialect_greeting",
    "is_valid_dialect",
]
