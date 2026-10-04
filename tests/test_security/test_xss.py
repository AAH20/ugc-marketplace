"""XSS prevention tests for ugc-marketplace."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ugc_marketplace.middleware.sanitization import SanitizationMiddleware


class TestXSSPrevention:
    """Test that XSS attacks are prevented."""

    XSS_PAYLOADS = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert('XSS')>",
        "javascript:alert('XSS')",
        "<body onload=alert('XSS')>",
        "<iframe src='javascript:alert(1)'>",
        "<input onfocus=alert('XSS') autofocus>",
        "<marquee onstart=alert('XSS')>",
        "<details open ontoggle=alert('XSS')>",
        "\"><script>alert('XSS')</script>",
        "'><script>alert('XSS')</script>",
        "<img src=\"javascript:alert('XSS')\">",
        "<a href=\"javascript:alert('XSS')\">click</a>",
        "<div style=\"background-image: url(javascript:alert('XSS'))\">",
        "<object data=\"javascript:alert('XSS')\">",
        "<embed src=\"javascript:alert('XSS')\">",
        "<form><button formaction=\"javascript:alert('XSS')\">",
        "<video><source onerror=\"alert('XSS')\">",
        "<audio src=x onerror=alert('XSS')>",
    ]

    def test_sanitization_middleware_strips_html(self):
        """Test that sanitization middleware strips HTML tags."""
        app = FastAPI()
        middleware = SanitizationMiddleware(app)
        for payload in self.XSS_PAYLOADS:
            sanitized = middleware._sanitize_string(payload)
            # Should not contain script tags
            assert "<script>" not in sanitized.lower(), (
                f"XSS payload not sanitized: {payload} -> {sanitized}"
            )

    def test_sanitization_middleware_strips_javascript(self):
        """Test that sanitization middleware strips javascript: URIs."""
        app = FastAPI()
        middleware = SanitizationMiddleware(app)
        for payload in self.XSS_PAYLOADS:
            sanitized = middleware._sanitize_string(payload)
            assert "javascript:" not in sanitized.lower(), (
                f"JavaScript URI not sanitized: {payload} -> {sanitized}"
            )

    def test_sanitization_middleware_strips_event_handlers(self):
        """Test that sanitization middleware strips event handlers."""
        app = FastAPI()
        middleware = SanitizationMiddleware(app)
        for payload in self.XSS_PAYLOADS:
            sanitized = middleware._sanitize_string(payload)
            assert "onerror=" not in sanitized.lower(), (
                f"Event handler not sanitized: {payload} -> {sanitized}"
            )

    def test_sanitization_middleware_strips_iframes(self):
        """Test that sanitization middleware strips iframes."""
        app = FastAPI()
        middleware = SanitizationMiddleware(app)
        for payload in self.XSS_PAYLOADS:
            sanitized = middleware._sanitize_string(payload)
            assert "<iframe" not in sanitized.lower(), (
                f"iframe not sanitized: {payload} -> {sanitized}"
            )

    def test_sanitization_middleware_strips_objects(self):
        """Test that sanitization middleware strips object/embed tags."""
        app = FastAPI()
        middleware = SanitizationMiddleware(app)
        for payload in self.XSS_PAYLOADS:
            sanitized = middleware._sanitize_string(payload)
            assert "<object" not in sanitized.lower(), (
                f"object tag not sanitized: {payload} -> {sanitized}"
            )
            assert "<embed" not in sanitized.lower(), (
                f"embed tag not sanitized: {payload} -> {sanitized}"
            )

    def test_sanitization_middleware_dict(self):
        """Test that sanitization middleware sanitizes dict values."""
        app = FastAPI()
        middleware = SanitizationMiddleware(app)
        data = {
            "title": "<script>alert('XSS')</script>",
            "description": "Normal text",
            "nested": {
                "field": "<img src=x onerror=alert('XSS')>"
            },
            "list": ["<script>alert(1)</script>", "normal"]
        }
        sanitized = middleware._sanitize_dict(data)
        assert "<script>" not in sanitized["title"].lower()
        assert "<img" not in sanitized["nested"]["field"].lower()
        assert "<script>" not in sanitized["list"][0].lower()
        assert sanitized["description"] == "Normal text"
        assert sanitized["list"][1] == "normal"
