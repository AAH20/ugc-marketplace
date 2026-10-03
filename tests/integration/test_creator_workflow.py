"""Integration tests for creator workflow: lifecycle, content, and monetization.

These tests exercise the full creator workflow across multiple services:
- CreatorService: create, read, update, delete creators
- ContentService: create and list content for creators
- PaymentService: process payments and initiate payouts
- CreatorMonetization: calculate and process payouts
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

import pytest

from ugc_marketplace.services.creator_service import (
    CreatorService,
    CreatorNotFoundError,
    CreatorValidationError,
)
from ugc_marketplace.services.content_service import (
    Content,
    ContentFilters,
    ContentNotFoundError,
    ContentStatus,
    ContentType,
    ContentValidationError,
    PaginatedResult,
    PaginationParams,
    _content_store,
    create_content,
    get_content,
    list_content,
)
from ugc_marketplace.services.payment_service import (
    InsufficientFundsError,
    InvalidPaymentDataError,
    PaymentNotFoundError,
    _payments_store,
    _user_balances,
    create_payment,
    get_payment,
    get_payment_history,
    initiate_payout,
    list_payments,
    process_payment,
)
from ugc_marketplace.agents.creator_monetization import (
    PayoutManagerAgent,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_stores():
    """Ensure all in-memory stores are empty before and after each test."""
    _content_store.clear()
    _payments_store.clear()
    _user_balances.clear()
    yield
    _content_store.clear()
    _payments_store.clear()
    _user_balances.clear()


@pytest.fixture
def creator_service() -> CreatorService:
    """Provide a CreatorService instance."""
    return CreatorService()


@pytest.fixture
def sample_creator_data() -> Dict[str, Any]:
    """Return valid creator data for creation."""
    return {
        "name": "Integration Test Creator",
        "email": "integration@example.com",
        "bio": "A creator for integration testing",
    }


@pytest.fixture
def created_creator(creator_service: CreatorService, sample_creator_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a creator and return the created record."""
    return creator_service.create_creator(sample_creator_data)


@pytest.fixture
def sample_content_data(created_creator: Dict[str, Any]) -> Dict[str, Any]:
    """Return valid content data for the created creator."""
    return {
        "title": "Integration Test Content",
        "description": "Content created during integration testing",
        "content_type": "image",
        "creator_id": created_creator["id"],
        "tags": ["integration", "test"],
    }


@pytest.fixture
def created_content(sample_content_data: Dict[str, Any]) -> Content:
    """Create a content item and return it."""
    return create_content(sample_content_data)


@pytest.fixture
def funded_creator(created_creator: Dict[str, Any]) -> Dict[str, Any]:
    """Create a creator and add funds to their balance via a payment."""
    creator_id = created_creator["id"]
    payment_data = {
        "user_id": creator_id,
        "amount": 500.00,
        "currency": "USD",
        "payment_method": "stripe",
        "description": "Test funding",
    }
    process_payment(payment_data)
    return created_creator


# ---------------------------------------------------------------------------
# Test: Full Creator Lifecycle
# ---------------------------------------------------------------------------


class TestFullCreatorLifecycle:
    """Integration test: create creator → update → delete."""

    def test_full_creator_lifecycle(self, creator_service: CreatorService):
        """Test complete CRUD lifecycle: create → read → update → delete."""
        # Step 1: Create a creator
        create_data = {
            "name": "Lifecycle Creator",
            "email": "lifecycle@example.com",
            "bio": "Creator for lifecycle test",
        }
        creator = creator_service.create_creator(create_data)

        assert creator is not None
        assert creator["id"] is not None
        assert creator["name"] == "Lifecycle Creator"
        assert creator["email"] == "lifecycle@example.com"
        assert creator["bio"] == "Creator for lifecycle test"
        assert creator["is_active"] is True

        creator_id = creator["id"]

        # Step 2: Read the creator
        fetched = creator_service.get_creator(creator_id)
        assert fetched is not None
        assert fetched["id"] == creator_id
        assert fetched["name"] == "Lifecycle Creator"
        assert fetched["email"] == "lifecycle@example.com"

        # Step 3: Update the creator
        update_data = {
            "name": "Updated Lifecycle Creator",
            "bio": "Updated bio for lifecycle test",
        }
        updated = creator_service.update_creator(creator_id, update_data)

        assert updated is not None
        assert updated["id"] == creator_id
        assert updated["name"] == "Updated Lifecycle Creator"
        assert updated["bio"] == "Updated bio for lifecycle test"
        # Unspecified fields should remain unchanged
        assert updated["email"] == "lifecycle@example.com"

        # Verify update persisted
        refetched = creator_service.get_creator(creator_id)
        assert refetched["name"] == "Updated Lifecycle Creator"
        assert refetched["bio"] == "Updated bio for lifecycle test"

        # Step 4: Delete the creator
        deleted = creator_service.delete_creator(creator_id)
        assert deleted is True

        # Verify deletion
        with pytest.raises(CreatorNotFoundError):
            creator_service.get_creator(creator_id)

    def test_full_creator_lifecycle_with_list_verification(
        self, creator_service: CreatorService
   ):
        """Test lifecycle with list verification at each step."""
        # Create
        creator = creator_service.create_creator({
            "name": "List Verify Creator",
            "email": "listverify@example.com",
        })
        creator_id = creator["id"]

        # Verify in list
        list_result = creator_service.list_creators()
        assert list_result["total"] == 1
        assert any(c["id"] == creator_id for c in list_result["items"])

        # Update
        creator_service.update_creator(creator_id, {"name": "Updated List Verify"})

        # Verify update in list
        list_result = creator_service.list_creators()
        found = [c for c in list_result["items"] if c["id"] == creator_id]
        assert len(found) == 1
        assert found[0]["name"] == "Updated List Verify"

        # Delete
        creator_service.delete_creator(creator_id)

        # Verify removal from list
        list_result = creator_service.list_creators()
        assert list_result["total"] == 0
        assert all(c["id"] != creator_id for c in list_result["items"])


# ---------------------------------------------------------------------------
# Test: Creator Content Flow
# ---------------------------------------------------------------------------


class TestCreatorContentFlow:
    """Integration test: create creator → create content → list."""

    def test_creator_content_flow(
        self,
        creator_service: CreatorService,
        sample_creator_data: Dict[str, Any],
    ):
        """Test creating a creator, adding content, and listing it."""
        # Step 1: Create a creator
        creator = creator_service.create_creator(sample_creator_data)
        creator_id = creator["id"]
        assert creator_id is not None

        # Step 2: Create content for the creator
        content_data = {
            "title": "Test Content Item",
            "description": "A test content item",
            "content_type": "image",
            "creator_id": creator_id,
            "tags": ["test", "integration"],
        }
        content = create_content(content_data)

        assert content is not None
        assert content.id is not None
        assert content.title == "Test Content Item"
        assert content.creator_id == creator_id
        assert content.content_type == ContentType.IMAGE
        assert content.status == ContentStatus.DRAFT

        # Step 3: List content for the creator
        filters = ContentFilters(creator_id=creator_id)
        result = list_content(filters=filters)

        assert isinstance(result, PaginatedResult)
        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].id == content.id
        assert result.items[0].creator_id == creator_id

    def test_creator_content_flow_multiple_content(
        self,
        creator_service: CreatorService,
    ):
        """Test creating a creator with multiple content items."""
        # Create creator
        creator = creator_service.create_creator({
            "name": "Multi Content Creator",
            "email": "multi@example.com",
        })
        creator_id = creator["id"]

        # Create multiple content items
        content_items = []
        for i in range(3):
            content_data = {
                "title": f"Content {i}",
                "description": f"Description for content {i}",
                "content_type": "video" if i % 2 == 0 else "image",
                "creator_id": creator_id,
                "tags": [f"tag-{i}"],
            }
            content_items.append(create_content(content_data))

        # List all content for the creator
        filters = ContentFilters(creator_id=creator_id)
        result = list_content(filters=filters)

        assert result.total == 3
        assert len(result.items) == 3

        # Verify all content belongs to the creator
        for item in result.items:
            assert item.creator_id == creator_id

        # Verify content can be retrieved individually
        for content in content_items:
            fetched = get_content(content.id)
            assert fetched.id == content.id
            assert fetched.creator_id == creator_id

    def test_creator_content_flow_with_creator_deletion(
        self,
        creator_service: CreatorService,
    ):
        """Test that content persists even after creator is deleted (no cascade)."""
        # Create creator
        creator = creator_service.create_creator({
            "name": "Temp Creator",
            "email": "temp@example.com",
        })
        creator_id = creator["id"]

        # Create content
        content = create_content({
            "title": "Persistent Content",
            "description": "Content that survives creator deletion",
            "content_type": "text",
            "creator_id": creator_id,
        })

        # Delete creator
        creator_service.delete_creator(creator_id)

        # Content should still exist (no cascade delete in this implementation)
        fetched = get_content(content.id)
        assert fetched.id == content.id
        assert fetched.creator_id == creator_id

        # Content should still be listable
        filters = ContentFilters(creator_id=creator_id)
        result = list_content(filters=filters)
        assert result.total == 1


# ---------------------------------------------------------------------------
# Test: Creator Monetization Flow
# ---------------------------------------------------------------------------


class TestCreatorMonetizationFlow:
    """Integration test: create creator → calculate payout → process payout."""

    @pytest.mark.asyncio
    async def test_creator_monetization_flow(
        self,
        creator_service: CreatorService,
    ):
        """Test the full monetization flow: create → fund → calculate → payout."""
        # Step 1: Create a creator
        creator = creator_service.create_creator({
            "name": "Monetization Creator",
            "email": "monetization@example.com",
        })
        creator_id = creator["id"]
        assert creator_id is not None

        # Step 2: Fund the creator's balance via a payment
        payment_data = {
            "user_id": creator_id,
            "amount": 1000.00,
            "currency": "USD",
            "payment_method": "stripe",
            "description": "Creator funding",
        }
        payment = process_payment(payment_data)

        assert payment is not None
        assert payment["status"] == "completed"
        assert payment["user_id"] == creator_id
        assert payment["amount"] == 1000.00

        # Verify balance was updated
        assert _user_balances.get(creator_id, 0.0) == 1000.00

        # Step 3: Initiate a payout
        payout_amount = 100.00
        payout = initiate_payout(creator_id, payout_amount)

        assert payout is not None
        assert payout["creator_id"] == creator_id
        assert payout["amount"] == payout_amount
        assert payout["status"] == "initiated"
        assert "payout_id" in payout

        # Verify balance was deducted
        assert _user_balances.get(creator_id, 0.0) == 900.00

        # Step 4: Verify payment history
        history = get_payment_history(creator_id)
        assert len(history) >= 2  # payment + payout

        # Verify payout appears in history
        payout_ids = [h.get("payout_id") for h in history if "payout_id" in h]
        assert payout["payout_id"] in payout_ids

    @pytest.mark.asyncio
    async def test_creator_monetization_flow_with_multiple_payouts(
        self,
        creator_service: CreatorService,
    ):
        """Test multiple payouts for a single creator."""
        # Create and fund creator
        creator = creator_service.create_creator({
            "name": "Multi Payout Creator",
            "email": "multipayout@example.com",
        })
        creator_id = creator["id"]

        # Fund with multiple payments
        for amount in [200.00, 300.00, 500.00]:
            process_payment({
                "user_id": creator_id,
                "amount": amount,
                "currency": "USD",
                "payment_method": "stripe",
            })

        assert _user_balances.get(creator_id, 0.0) == 1000.00

        # Process multiple payouts
        payout1 = initiate_payout(creator_id, 100.00)
        assert payout1["status"] == "initiated"
        assert _user_balances.get(creator_id, 0.0) == 900.00

        payout2 = initiate_payout(creator_id, 200.00)
        assert payout2["status"] == "initiated"
        assert _user_balances.get(creator_id, 0.0) == 700.00

        payout3 = initiate_payout(creator_id, 50.00)
        assert payout3["status"] == "initiated"
        assert _user_balances.get(creator_id, 0.0) == 650.00

        # Verify all payouts in history
        history = get_payment_history(creator_id)
        payout_records = [h for h in history if "payout_id" in h]
        assert len(payout_records) == 3

    @pytest.mark.asyncio
    async def test_creator_monetization_insufficient_funds(
        self,
        creator_service: CreatorService,
    ):
        """Test that payout fails when creator has insufficient balance."""
        # Create creator without funding
        creator = creator_service.create_creator({
            "name": "Broke Creator",
            "email": "broke@example.com",
        })
        creator_id = creator["id"]

        # Attempt payout without funds
        with pytest.raises(InsufficientFundsError):
            initiate_payout(creator_id, 100.00)

    @pytest.mark.asyncio
    async def test_creator_monetization_payout_manager_agent(
        self,
        creator_service: CreatorService,
    ):
        """Test the PayoutManagerAgent for creator payout lifecycle."""
        # Create creator
        creator = creator_service.create_creator({
            "name": "Agent Payout Creator",
            "email": "agentpayout@example.com",
        })
        creator_id = creator["id"]

        # Initialize PayoutManagerAgent
        payout_manager = PayoutManagerAgent()

        # Create a payout
        payout = await payout_manager.create_payout(
            creator_id=creator_id,
            amount=Decimal("250.00"),
            currency="USD",
        )

        assert payout is not None
        assert payout["creator_id"] == creator_id
        assert payout["amount"] == "250.00"
        assert payout["currency"] == "USD"
        assert payout["status"] == "pending"
        assert "payout_id" in payout

        payout_id = payout["payout_id"]

        # Process the payout
        processing_payout = await payout_manager.process_payout(payout_id)
        assert processing_payout["status"] == "processing"

        # Complete the payout
        completed_payout = await payout_manager.complete_payout(payout_id)
        assert completed_payout["status"] == "completed"
        assert "paid_at" in completed_payout

        # Verify payout can be retrieved
        fetched_payout = payout_manager.get_payout(payout_id)
        assert fetched_payout is not None
        assert fetched_payout["status"] == "completed"

        # Verify creator balance
        balance = payout_manager.get_creator_balance(creator_id)
        assert balance["creator_id"] == creator_id
        assert balance["total_paid"] == "250.00"
        assert balance["currency"] == "USD"

    @pytest.mark.asyncio
    async def test_creator_monetization_payout_manager_multiple_creators(
        self,
        creator_service: CreatorService,
    ):
        """Test PayoutManagerAgent with multiple creators."""
        # Create two creators
        creator1 = creator_service.create_creator({
            "name": "Creator One",
            "email": "creator1@example.com",
        })
        creator2 = creator_service.create_creator({
            "name": "Creator Two",
            "email": "creator2@example.com",
        })

        payout_manager = PayoutManagerAgent()

        # Create payouts for both creators
        payout1 = await payout_manager.create_payout(
            creator_id=creator1["id"],
            amount=Decimal("100.00"),
        )
        payout2 = await payout_manager.create_payout(
            creator_id=creator2["id"],
            amount=Decimal("200.00"),
        )

        # Complete both payouts
        await payout_manager.complete_payout(payout1["payout_id"])
        await payout_manager.complete_payout(payout2["payout_id"])

        # Verify individual creator balances
        balance1 = payout_manager.get_creator_balance(creator1["id"])
        assert balance1["total_paid"] == "100.00"

        balance2 = payout_manager.get_creator_balance(creator2["id"])
        assert balance2["total_paid"] == "200.00"

        # Verify list_payouts filtering
        creator1_payouts = payout_manager.list_payouts(creator_id=creator1["id"])
        assert len(creator1_payouts) == 1
        assert creator1_payouts[0]["amount"] == "100.00"

        completed_payouts = payout_manager.list_payouts(status="completed")
        assert len(completed_payouts) == 2
