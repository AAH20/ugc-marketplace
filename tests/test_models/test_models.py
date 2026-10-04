"""Tests for ugc-marketplace models and schemas."""

import pytest
from pydantic import ValidationError


class TestContentModel:
    """Test content Pydantic model."""

    def test_valid_content(self):
        """Test valid content data."""
        from ugc_marketplace.models import ContentCreate
        
        data = {
            "title": "Test Content",
            "description": "Test description",
            "content_type": "video",
        }
        
        content = ContentCreate(**data)
        assert content.title == "Test Content"

    def test_content_title_too_long(self):
        """Test content title max length."""
        from ugc_marketplace.models import ContentCreate
        
        with pytest.raises(ValidationError):
            ContentCreate(title="A" * 501, description="Test")


class TestLicenseModel:
    """Test license Pydantic model."""

    def test_valid_license(self):
        """Test valid license data."""
        from ugc_marketplace.models import LicenseCreate
        
        data = {
            "content_id": 1,
            "license_type": "standard",
            "price": 99.99,
        }
        
        license_obj = LicenseCreate(**data)
        assert license_obj.content_id == 1

    def test_license_price_validation(self):
        """Test license price validation."""
        from ugc_marketplace.models import LicenseCreate
        
        with pytest.raises(ValidationError):
            LicenseCreate(content_id=1, price=-10)


class TestCreatorModel:
    """Test creator Pydantic model."""

    def test_valid_creator(self):
        """Test valid creator data."""
        from ugc_marketplace.models import CreatorCreate
        
        data = {
            "name": "Test Creator",
            "email": "creator@example.com",
        }
        
        creator = CreatorCreate(**data)
        assert creator.name == "Test Creator"

    def test_creator_invalid_email(self):
        """Test creator email validation."""
        from ugc_marketplace.models import CreatorCreate
        
        with pytest.raises(ValidationError):
            CreatorCreate(name="Test", email="invalid")


class TestTransactionModel:
    """Test transaction Pydantic model."""

    def test_valid_transaction(self):
        """Test valid transaction data."""
        from ugc_marketplace.models import TransactionCreate
        
        data = {
            "content_id": 1,
            "buyer_id": 1,
            "amount": 99.99,
        }
        
        transaction = TransactionCreate(**data)
        assert transaction.amount == 99.99
