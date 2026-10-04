"""SQL injection prevention tests for ugc-marketplace."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ugc_marketplace.middleware.sanitization import SanitizationMiddleware


class TestSQLInjectionPrevention:
    """Test that SQL injection attacks are prevented."""

    SQL_INJECTION_PAYLOADS = [
        "' OR '1'='1",
        "' OR 1=1--",
        "'; DROP TABLE content;--",
        "1' UNION SELECT * FROM content--",
        "' OR '1'='1' /*",
        "admin'--",
        "' OR 1=1#",
        "1 AND 1=1",
        "'; EXEC xp_cmdshell('dir');--",
        "' OR ''='",
        "1; SELECT * FROM content",
        "' UNION SELECT null, null, null--",
        "1' AND (SELECT COUNT(*) FROM content) > 0--",
        "'; INSERT INTO content VALUES ('hacked')--",
        "' OR 1=1 LIMIT 1--",
        "1' OR '1'='1",
        "'; UPDATE content SET title='hacked'--",
        "' OR 'x'='x",
        "1 AND 1=2",
        "'; DELETE FROM content WHERE '1'='1",
    ]

    def test_sanitization_middleware_strips_sql_keywords(self):
        """Test that sanitization middleware strips SQL keywords."""
        app = FastAPI()
        middleware = SanitizationMiddleware(app)
        for payload in self.SQL_INJECTION_PAYLOADS:
            sanitized = middleware._sanitize_string(payload)
            # Should not contain dangerous SQL patterns
            assert "DROP TABLE" not in sanitized.upper(), (
                f"SQL DROP TABLE not sanitized: {payload} -> {sanitized}"
            )
            assert "UNION SELECT" not in sanitized.upper(), (
                f"SQL UNION SELECT not sanitized: {payload} -> {sanitized}"
            )

    def test_sanitization_middleware_strips_quotes(self):
        """Test that sanitization middleware strips quotes."""
        app = FastAPI()
        middleware = SanitizationMiddleware(app)
        for payload in self.SQL_INJECTION_PAYLOADS:
            sanitized = middleware._sanitize_string(payload)
            # Should not contain unescaped quotes
            assert "'" not in sanitized, (
                f"Quote not sanitized: {payload} -> {sanitized}"
            )

    def test_sanitization_middleware_strips_comments(self):
        """Test that sanitization middleware strips SQL comments."""
        app = FastAPI()
        middleware = SanitizationMiddleware(app)
        for payload in self.SQL_INJECTION_PAYLOADS:
            sanitized = middleware._sanitize_string(payload)
            # Should not contain SQL comments
            assert "--" not in sanitized, (
                f"SQL comment not sanitized: {payload} -> {sanitized}"
            )
            assert "/*" not in sanitized, (
                f"SQL block comment not sanitized: {payload} -> {sanitized}"
            )

    def test_sanitization_middleware_strips_semicolons(self):
        """Test that sanitization middleware strips semicolons."""
        app = FastAPI()
        middleware = SanitizationMiddleware(app)
        for payload in self.SQL_INJECTION_PAYLOADS:
            sanitized = middleware._sanitize_string(payload)
            # Should not contain semicolons
            assert ";" not in sanitized, (
                f"Semicolon not sanitized: {payload} -> {sanitized}"
            )

    def test_sanitization_middleware_dict(self):
        """Test that sanitization middleware sanitizes dict values."""
        app = FastAPI()
        middleware = SanitizationMiddleware(app)
        data = {
            "title": "'; DROP TABLE content;--",
            "description": "Normal text",
            "nested": {
                "field": "' OR '1'='1"
            },
            "list": ["' OR 1=1--", "normal"]
        }
        sanitized = middleware._sanitize_dict(data)
        assert "DROP TABLE" not in sanitized["title"].upper()
        assert "'" not in sanitized["nested"]["field"]
        assert "'" not in sanitized["list"][0]
        assert sanitized["description"] == "Normal text"
        assert sanitized["list"][1] == "normal"
