"""Coverage-gap tests for :mod:`ugc_marketplace.security.sanitization`.

``security.sanitization`` had zero references anywhere under ``tests/``.  It
provides the XSS-prevention primitives (input stripping + output encoding).
"""

from __future__ import annotations

from ugc_marketplace.security.sanitization import (
    encode_for_html,
    encode_response,
    sanitize_dict,
    sanitize_html,
    sanitize_text,
)


def test_sanitize_text_strips_all_tags():
    cleaned = sanitize_text("<script>alert(1)</script><b>hi</b>")
    assert cleaned is not None
    assert "<script>" not in cleaned
    assert "<b>" not in cleaned


def test_sanitize_text_none_passthrough():
    assert sanitize_text(None) is None


def test_sanitize_html_keeps_allowed_drops_dangerous():
    cleaned = sanitize_html('<p>ok</p><script>alert(1)</script>')
    assert cleaned is not None
    assert "<p>ok</p>" in cleaned
    assert "<script>" not in cleaned


def test_sanitize_html_none_passthrough():
    assert sanitize_html(None) is None


def test_sanitize_dict_uses_html_fields():
    cleaned = sanitize_dict(
        {"bio": "<strong>rich</strong>", "name": "<b>plain</b>", "count": 3},
        html_fields={"bio"},
    )
    assert "<strong>rich</strong>" in cleaned["bio"]
    assert "<b>" not in cleaned["name"]
    assert cleaned["count"] == 3


def test_sanitize_dict_strips_strings_inside_lists():
    cleaned = sanitize_dict({"tags": ["<i>a</i>", "b"]})
    assert "<i>" not in cleaned["tags"][0]


def test_encode_for_html_escapes_special_chars():
    assert encode_for_html("<a>&\"'") == "&lt;a&gt;&amp;&quot;&#x27;"
    assert encode_for_html(None) is None


def test_encode_response_recurses_through_structures():
    encoded = encode_response({"a": "<x>", "b": ["<y>", 1], "c": 2})
    assert encoded["a"] == "&lt;x&gt;"
    assert encoded["b"][0] == "&lt;y&gt;"
    assert encoded["b"][1] == 1
    assert encoded["c"] == 2
