"""Input validation tests for ugc-marketplace."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, field_validator


class TestInputValidation:
    """Test that input validation is properly enforced."""

    def test_content_type_validation(self):
        """Test that content type validation works."""
        from ugc_marketplace.api.content import ContentCreate, VALID_TYPES

        # Valid types
        for content_type in VALID_TYPES:
            content = ContentCreate(
                title="Test",
                type=content_type,
                author_id="user-123"
            )
            assert content.type == content_type

        # Invalid type should raise
        with pytest.raises(Exception):
            ContentCreate(
                title="Test",
                type="invalid_type",
                author_id="user-123"
            )

    def test_content_title_required(self):
        """Test that content title is required."""
        from ugc_marketplace.api.content import ContentCreate

        with pytest.raises(Exception):
            ContentCreate(
                type="image",
                author_id="user-123"
            )

    def test_content_author_id_required(self):
        """Test that author_id is required."""
        from ugc_marketplace.api.content import ContentCreate

        with pytest.raises(Exception):
            ContentCreate(
                title="Test",
                type="image"
            )

    def test_content_title_max_length(self):
        """Test that content title has max length."""
        from ugc_marketplace.api.content import ContentCreate

        with pytest.raises(Exception):
            ContentCreate(
                title="a" * 500,
                type="image",
                author_id="user-123"
            )

    def test_content_tags_max_count(self):
        """Test that content tags have max count."""
        from ugc_marketplace.api.content import ContentCreate

        with pytest.raises(Exception):
            ContentCreate(
                title="Test",
                type="image",
                author_id="user-123",
                tags=[f"tag_{i}" for i in range(25)]
            )

    def test_content_tags_max_length(self):
        """Test that each tag has max length."""
        from ugc_marketplace.api.content import ContentCreate

        with pytest.raises(Exception):
            ContentCreate(
                title="Test",
                type="image",
                author_id="user-123",
                tags=["a" * 100]
            )

    def test_content_update_type_validation(self):
        """Test that content update validates type."""
        from ugc_marketplace.api.content import ContentUpdate

        with pytest.raises(Exception):
            ContentUpdate(type="invalid_type")

    def test_content_update_status_validation(self):
        """Test that content update validates status."""
        from ugc_marketplace.api.content import ContentUpdate

        with pytest.raises(Exception):
            ContentUpdate(status="invalid_status")

    def test_content_status_validation(self):
        """Test that content status validation works."""
        from ugc_marketplace.api.content import ContentCreate, VALID_STATUSES

        # Valid statuses should work in update
        from ugc_marketplace.api.content import ContentUpdate
        for status in VALID_STATUSES:
            update = ContentUpdate(status=status)
            assert update.status == status
