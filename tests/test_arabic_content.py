"""Tests for basic Arabic content generation."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.arabic.arabic_content import (
    generate_marketing_copy,
    is_arabic,
    router,
    wrap_rtl,
)


def test_is_arabic_detects_arabic_text():
    """Text containing Arabic-script characters is detected as Arabic."""
    assert is_arabic("مرحبا بك") is True
    assert is_arabic("Hello مرحبا") is True  # mixed text still counts


def test_is_arabic_rejects_non_arabic():
    """Purely non-Arabic text is not detected as Arabic."""
    assert is_arabic("Hello world") is False
    assert is_arabic("") is False
    assert is_arabic("12345") is False


def test_wrap_rtl_produces_dir_rtl_span():
    """wrap_rtl wraps text in an HTML span with dir=rtl and lang=ar."""
    result = wrap_rtl("مرحبا")
    assert result == '<span dir="rtl" lang="ar">مرحبا</span>'


def test_generate_marketing_copy_contains_prompt():
    """Generated copy embeds the prompt and is itself Arabic."""
    content = generate_marketing_copy("متجرنا الجديد")
    assert "متجرنا الجديد" in content
    assert is_arabic(content) is True


def test_generate_marketing_copy_rejects_empty_prompt():
    """Empty or whitespace-only prompts raise ValueError."""
    import pytest

    with pytest.raises(ValueError):
        generate_marketing_copy("")
    with pytest.raises(ValueError):
        generate_marketing_copy("   ")


def test_api_endpoint_returns_arabic_content():
    """POST /api/v1/arabic/generate returns Arabic content with RTL HTML."""
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.post("/api/v1/arabic/generate", json={"prompt": "عروض الصيف"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["prompt"] == "عروض الصيف"
    assert data["is_arabic"] is True
    assert "عروض الصيف" in data["content"]
    assert 'dir="rtl"' in data["rtl_html"]
