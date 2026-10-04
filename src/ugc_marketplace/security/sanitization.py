"""Input sanitization and output encoding utilities for XSS prevention."""
from __future__ import annotations

import html
from typing import Any

import bleach

# Allowed HTML tags for rich text fields (descriptions, bios, etc.)
ALLOWED_TAGS = [
    "p", "br", "strong", "em", "u", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "a", "blockquote", "code", "pre",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_text(value: str | None) -> str | None:
    """Sanitize plain text input — strips all HTML tags."""
    if value is None:
        return None
    return bleach.clean(value, tags=[], attributes={}, strip=True)


def sanitize_html(value: str | None) -> str | None:
    """Sanitize rich text input — allows safe HTML tags only."""
    if value is None:
        return None
    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )


def sanitize_dict(data: dict[str, Any], html_fields: set[str] | None = None) -> dict[str, Any]:
    """Sanitize all string values in a dict.

    Args:
        data: Dictionary with user input
        html_fields: Set of field names that allow safe HTML (others are stripped)
    """
    if html_fields is None:
        html_fields = set()
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            if key in html_fields:
                result[key] = sanitize_html(value)
            else:
                result[key] = sanitize_text(value)
        elif isinstance(value, list):
            result[key] = [
                sanitize_text(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def encode_for_html(value: str | None) -> str | None:
    """HTML-encode a string for safe output in HTML contexts."""
    if value is None:
        return None
    return html.escape(value, quote=True)


def encode_response(data: Any) -> Any:
    """Recursively HTML-encode all string values in a response structure."""
    if isinstance(data, str):
        return encode_for_html(data)
    if isinstance(data, dict):
        return {k: encode_response(v) for k, v in data.items()}
    if isinstance(data, list):
        return [encode_response(item) for item in data]
    return data
