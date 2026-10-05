"""
Comprehensive service tests for the Payment Service.

Tests cover:
- get_payment: Retrieve a single payment by ID
- list_payments: List payments with various filters
- create_payment: Create a new payment
- update_payment_status: Update payment status
- delete_payment: Delete a payment
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def payment_service():
    """Create a payment service instance with mocked dependencies."""
    from ugc_marketplace.services.payment_service import PaymentService
    
    mock_db = MagicMock()
    mock_cache = MagicMock()
    mock_event_bus = MagicMock()
    
    service = PaymentService(
        db=mock_db,
        cache=mock_cache,
        event_bus=mock_event_bus,
    )
    return service


@pytest.fixture
def sample_payment_data():
    """Return sample payment data for testing."""
    return {
        "id": str(uuid4()),
        "order_id": str(uuid4()),
        "user_id": str(uuid4()),
        "amount": Decimal("99.99"),
        "currency": "USD",
        "status": "pending",
        "payment_method": "credit_card",
        "payment_method_id": "pm_test_123",
        "description": "Test payment",
        "metadata": {"order_type": "digital_content"},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


@pytest.fixture
def sample_payment(sample_payment_data):
    """Return a sample payment object."""
    from ugc_marketplace.models.payment import Payment
    return Payment(**sample_payment_data)


@pytest.fixture
def multiple_payments():
    """Return a list of sample payments for list testing."""
    from ugc_marketplace.models.payment import Payment
    
    payments = []
    statuses = ["pending", "completed", "failed", "refunded", "cancelled"]
    for i, status in enumerate(statuses):
        payments.append(Payment(
            id=str(uuid4()),
            order_id=str(uuid4()),
            user_id=str(uuid4()),
            amount=Decimal(f"{10 + i}.99"),
            currency="USD",
            status=status,
            payment_method="credit_card",
            payment_method_id=f"pm_test_{i}",
            description=f"Test payment {i}",
            metadata={},
            created_at=datetime.utcnow() - timedelta(days=i),
            updated_at=datetime.utcnow() - timedelta(days=i),
        ))
    return payments


# ---------------------------------------------------------------------------
# Test: get_payment
# ---------------------------------------------------------------------------


class TestGetPayment:
    """Tests for the get_payment function."""

    @pytest.mark.asyncio
    async def test_get_payment_success(self, payment_service, sample_payment):
        """Test successful retrieval of a payment by ID."""
        payment_id = sample_payment.id
        
        # Mock the database query
        payment_service.db.get_payment = AsyncMock(return_value=sample_payment)
        
        result = await payment_service.get_payment(payment_id)
        
        assert result is not None
        assert result.id == payment_id
        assert result.order_id == sample_payment.order_id
        assert result.amount == sample_payment.amount
        assert result.status == sample_payment.status
        payment_service.db.get_payment.assert_called_once_with(payment_id)

    @pytest.mark.asyncio
    async def test_get_payment_not_found(self, payment_service):
        """Test get_payment returns None when payment doesn't exist."""
        payment_id = str(uuid4())
        
        payment_service.db.get_payment = AsyncMock(return_value=None)
        
        result = await payment_service.get_payment(payment_id)
        
        assert result is None
        payment_service.db.get_payment.assert_called_once_with(payment_id)

    @pytest.mark.asyncio
    async def test_get_payment_invalid_id(self, payment_service):
        """Test get_payment with invalid ID format."""
        with pytest.raises(ValueError, match="Invalid payment ID"):
            await payment_service.get_payment("not-a-valid-uuid")

    @pytest.mark.asyncio
    async def test_get_payment_database_error(self, payment_service):
        """Test get_payment handles database errors gracefully."""
        payment_id = str(uuid4())
        
        payment_service.db.get_payment = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        
        with pytest.raises(Exception, match="Database connection failed"):
            await payment_service.get_payment(payment_id)

    @pytest.mark.asyncio
    async def test_get_payment_caching(self, payment_service, sample_payment):
        """Test that get_payment uses cache when available."""
        payment_id = sample_payment.id
        
        # First call - cache miss
        payment_service.cache.get = AsyncMock(return_value=None)
        payment_service.cache.set = AsyncMock()
        payment_service.db.get_payment = AsyncMock(return_value=sample_payment)
        
        result1 = await payment_service.get_payment(payment_id)
        
        assert result1.id == payment_id
        payment_service.cache.set.assert_called_once()
        
        # Second call - cache hit
        payment_service.cache.get = AsyncMock(return_value=sample_payment)
        payment_service.db.get_payment = AsyncMock()
        
        result2 = await payment_service.get_payment(payment_id)
        
        assert result2.id == payment_id
        # DB should not be called on cache hit
        payment_service.db.get_payment.assert_not_called()


# ---------------------------------------------------------------------------
# Test: list_payments
# ---------------------------------------------------------------------------


class TestListPayments:
    """Tests for the list_payments function with filters."""

    @pytest.mark.asyncio
    async def test_list_payments_no_filters(self, payment_service, multiple_payments):
        """Test listing all payments without filters."""
        payment_service.db.list_payments = AsyncMock(return_value=multiple_payments)
        
        result = await payment_service.list_payments()
        
        assert len(result) == 5
        payment_service.db.list_payments.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_payments_filter_by_status(self, payment_service, multiple_payments):
        """Test listing payments filtered by status."""
        filtered = [p for p in multiple_payments if p.status == "completed"]
        payment_service.db.list_payments = AsyncMock(return_value=filtered)
        
        result = await payment_service.list_payments(status="completed")
        
        assert len(result) == 1
        assert all(p.status == "completed" for p in result)

    @pytest.mark.asyncio
    async def test_list_payments_filter_by_user_id(self, payment_service, multiple_payments):
        """Test listing payments filtered by user ID."""
        user_id = multiple_payments[0].user_id
        filtered = [p for p in multiple_payments if p.user_id == user_id]
        payment_service.db.list_payments = AsyncMock(return_value=filtered)
        
        result = await payment_service.list_payments(user_id=user_id)
        
        assert all(p.user_id == user_id for p in result)

    @pytest.mark.asyncio
    async def test_list_payments_filter_by_order_id(self, payment_service, multiple_payments):
        """Test listing payments filtered by order ID."""
        order_id = multiple_payments[0].order_id
        filtered = [p for p in multiple_payments if p.order_id == order_id]
        payment_service.db.list_payments = AsyncMock(return_value=filtered)
        
        result = await payment_service.list_payments(order_id=order_id)
        
        assert all(p.order_id == order_id for p in result)

    @pytest.mark.asyncio
    async def test_list_payments_filter_by_date_range(self, payment_service, multiple_payments):
        """Test listing payments filtered by date range."""
        start_date = datetime.utcnow() - timedelta(days=2)
        end_date = datetime.utcnow()
        filtered = [
            p for p in multiple_payments
            if start_date <= p.created_at <= end_date
        ]
        payment_service.db.list_payments = AsyncMock(return_value=filtered)
        
        result = await payment_service.list_payments(
            start_date=start_date,
            end_date=end_date,
        )
        
        assert all(start_date <= p.created_at <= end_date for p in result)

    @pytest.mark.asyncio
    async def test_list_payments_filter_by_amount_range(self, payment_service, multiple_payments):
        """Test listing payments filtered by amount range."""
        min_amount = Decimal("11.00")
        max_amount = Decimal("13.00")
        filtered = [
            p for p in multiple_payments
            if min_amount <= p.amount <= max_amount
        ]
        payment_service.db.list_payments = AsyncMock(return_value=filtered)
        
        result = await payment_service.list_payments(
            min_amount=min_amount,
            max_amount=max_amount,
        )
        
        assert all(min_amount <= p.amount <= max_amount for p in result)

    @pytest.mark.asyncio
    async def test_list_payments_pagination(self, payment_service, multiple_payments):
        """Test listing payments with pagination."""
        payment_service.db.list_payments = AsyncMock(return_value=multiple_payments[:2])
        
        result = await payment_service.list_payments(limit=2, offset=0)
        
        assert len(result) == 2
        call_kwargs = payment_service.db.list_payments.call_args[1]
        assert call_kwargs.get("limit") == 2
        assert call_kwargs.get("offset") == 0

    @pytest.mark.asyncio
    async def test_list_payments_empty_result(self, payment_service):
        """Test listing payments returns empty list when no matches."""
        payment_service.db.list_payments = AsyncMock(return_value=[])
        
        result = await payment_service.list_payments(status="nonexistent")
        
        assert result == []

    @pytest.mark.asyncio
    async def test_list_payments_multiple_filters(self, payment_service, multiple_payments):
        """Test listing payments with multiple filters combined."""
        filtered = [
            p for p in multiple_payments
            if p.status == "pending" and p.currency == "USD"
        ]
        payment_service.db.list_payments = AsyncMock(return_value=filtered)
        
        result = await payment_service.list_payments(
            status="pending",
            currency="USD",
        )
        
        assert all(p.status == "pending" and p.currency == "USD" for p in result)

    @pytest.mark.asyncio
    async def test_list_payments_sorting(self, payment_service, multiple_payments):
        """Test listing payments with sorting."""
        sorted_payments = sorted(multiple_payments, key=lambda p: p.created_at, reverse=True)
        payment_service.db.list_payments = AsyncMock(return_value=sorted_payments)
        
        result = await payment_service.list_payments(
            sort_by="created_at",
            sort_order="desc",
        )
        
        # Verify results are sorted
        for i in range(len(result) - 1):
            assert result[i].created_at >= result[i + 1].created_at


# ---------------------------------------------------------------------------
# Test: create_payment
# ---------------------------------------------------------------------------


class TestCreatePayment:
    """Tests for the create_payment function."""

    @pytest.mark.asyncio
    async def test_create_payment_success(self, payment_service, sample_payment_data):
        """Test successful payment creation."""
        payment_service.db.create_payment = AsyncMock(return_value=sample_payment_data)
        payment_service.event_bus.publish = AsyncMock()
        
        result = await payment_service.create_payment(
            order_id=sample_payment_data["order_id"],
            user_id=sample_payment_data["user_id"],
            amount=sample_payment_data["amount"],
            currency=sample_payment_data["currency"],
            payment_method=sample_payment_data["payment_method"],
            payment_method_id=sample_payment_data["payment_method_id"],
            description=sample_payment_data["description"],
            metadata=sample_payment_data["metadata"],
        )
        
        assert result is not None
        assert result["order_id"] == sample_payment_data["order_id"]
        assert result["amount"] == sample_payment_data["amount"]
        assert result["status"] == "pending"
        payment_service.db.create_payment.assert_called_once()
        payment_service.event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_payment_with_minimal_data(self, payment_service):
        """Test payment creation with minimal required fields."""
        order_id = str(uuid4())
        user_id = str(uuid4())
        amount = Decimal("50.00")
        
        payment_service.db.create_payment = AsyncMock(return_value={
            "id": str(uuid4()),
            "order_id": order_id,
            "user_id": user_id,
            "amount": amount,
            "currency": "USD",
            "status": "pending",
            "payment_method": "credit_card",
            "payment_method_id": "pm_minimal",
            "description": None,
            "metadata": {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        
        result = await payment_service.create_payment(
            order_id=order_id,
            user_id=user_id,
            amount=amount,
            currency="USD",
            payment_method="credit_card",
            payment_method_id="pm_minimal",
        )
        
        assert result["order_id"] == order_id
        assert result["amount"] == amount
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_payment_invalid_amount(self, payment_service):
        """Test create_payment rejects negative amounts."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            await payment_service.create_payment(
                order_id=str(uuid4()),
                user_id=str(uuid4()),
                amount=Decimal("-10.00"),
                currency="USD",
                payment_method="credit_card",
                payment_method_id="pm_test",
            )

    @pytest.mark.asyncio
    async def test_create_payment_zero_amount(self, payment_service):
        """Test create_payment rejects zero amount."""
        with pytest.raises(ValueError, match="Amount must be positive"):
            await payment_service.create_payment(
                order_id=str(uuid4()),
                user_id=str(uuid4()),
                amount=Decimal("0.00"),
                currency="USD",
                payment_method="credit_card",
                payment_method_id="pm_test",
            )

    @pytest.mark.asyncio
    async def test_create_payment_invalid_currency(self, payment_service):
        """Test create_payment rejects invalid currency."""
        with pytest.raises(ValueError, match="Invalid currency"):
            await payment_service.create_payment(
                order_id=str(uuid4()),
                user_id=str(uuid4()),
                amount=Decimal("10.00"),
                currency="INVALID",
                payment_method="credit_card",
                payment_method_id="pm_test",
            )

    @pytest.mark.asyncio
    async def test_create_payment_database_error(self, payment_service):
        """Test create_payment handles database errors."""
        payment_service.db.create_payment = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        with pytest.raises(Exception, match="Database error"):
            await payment_service.create_payment(
                order_id=str(uuid4()),
                user_id=str(uuid4()),
                amount=Decimal("10.00"),
                currency="USD",
                payment_method="credit_card",
                payment_method_id="pm_test",
            )

    @pytest.mark.asyncio
    async def test_create_payment_publishes_event(self, payment_service, sample_payment_data):
        """Test that create_payment publishes a payment.created event."""
        payment_service.db.create_payment = AsyncMock(return_value=sample_payment_data)
        payment_service.event_bus.publish = AsyncMock()
        
        await payment_service.create_payment(
            order_id=sample_payment_data["order_id"],
            user_id=sample_payment_data["user_id"],
            amount=sample_payment_data["amount"],
            currency=sample_payment_data["currency"],
            payment_method=sample_payment_data["payment_method"],
            payment_method_id=sample_payment_data["payment_method_id"],
        )
        
        # Verify event was published
        payment_service.event_bus.publish.assert_called_once()
        call_args = payment_service.event_bus.publish.call_args
        assert "payment.created" in str(call_args)


# ---------------------------------------------------------------------------
# Test: update_payment_status
# ---------------------------------------------------------------------------


class TestUpdatePaymentStatus:
    """Tests for the update_payment_status function."""

    @pytest.mark.asyncio
    async def test_update_payment_status_success(self, payment_service, sample_payment):
        """Test successful payment status update."""
        new_status = "completed"
        updated_payment = MagicMock()
        updated_payment.id = sample_payment.id
        updated_payment.status = new_status
        
        payment_service.db.update_payment_status = AsyncMock(return_value=updated_payment)
        payment_service.event_bus.publish = AsyncMock()
        
        result = await payment_service.update_payment_status(
            sample_payment.id, new_status
        )
        
        assert result.status == new_status
        payment_service.db.update_payment_status.assert_called_once_with(
            sample_payment.id, new_status
        )

    @pytest.mark.asyncio
    async def test_update_payment_status_pending_to_completed(self, payment_service, sample_payment):
        """Test updating status from pending to completed."""
        sample_payment.status = "pending"
        updated_payment = MagicMock()
        updated_payment.id = sample_payment.id
        updated_payment.status = "completed"
        
        payment_service.db.update_payment_status = AsyncMock(return_value=updated_payment)
        payment_service.event_bus.publish = AsyncMock()
        
        result = await payment_service.update_payment_status(
            sample_payment.id, "completed"
        )
        
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_update_payment_status_pending_to_failed(self, payment_service, sample_payment):
        """Test updating status from pending to failed."""
        sample_payment.status = "pending"
        updated_payment = MagicMock()
        updated_payment.id = sample_payment.id
        updated_payment.status = "failed"
        
        payment_service.db.update_payment_status = AsyncMock(return_value=updated_payment)
        payment_service.event_bus.publish = AsyncMock()
        
        result = await payment_service.update_payment_status(
            sample_payment.id, "failed"
        )
        
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_update_payment_status_invalid_transition(self, payment_service, sample_payment):
        """Test that invalid status transitions are rejected."""
        sample_payment.status = "completed"
        
        with pytest.raises(ValueError, match="Invalid status transition"):
            await payment_service.update_payment_status(
                sample_payment.id, "pending"
            )

    @pytest.mark.asyncio
    async def test_update_payment_status_not_found(self, payment_service):
        """Test updating status of non-existent payment."""
        payment_id = str(uuid4())
        
        payment_service.db.update_payment_status = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError, match="Payment not found"):
            await payment_service.update_payment_status(payment_id, "completed")

    @pytest.mark.asyncio
    async def test_update_payment_status_invalid_status(self, payment_service, sample_payment):
        """Test that invalid status values are rejected."""
        with pytest.raises(ValueError, match="Invalid status"):
            await payment_service.update_payment_status(
                sample_payment.id, "invalid_status"
            )

    @pytest.mark.asyncio
    async def test_update_payment_status_publishes_event(self, payment_service, sample_payment):
        """Test that status update publishes an event."""
        updated_payment = MagicMock()
        updated_payment.id = sample_payment.id
        updated_payment.status = "completed"
        
        payment_service.db.update_payment_status = AsyncMock(return_value=updated_payment)
        payment_service.event_bus.publish = AsyncMock()
        
        await payment_service.update_payment_status(sample_payment.id, "completed")
        
        payment_service.event_bus.publish.assert_called_once()
        call_args = payment_service.event_bus.publish.call_args
        assert "payment.status_updated" in str(call_args)

    @pytest.mark.asyncio
    async def test_update_payment_status_with_metadata(self, payment_service, sample_payment):
        """Test updating status with additional metadata."""
        updated_payment = MagicMock()
        updated_payment.id = sample_payment.id
        updated_payment.status = "refunded"
        updated_payment.metadata = {"refund_reason": "customer_request"}
        
        payment_service.db.update_payment_status = AsyncMock(return_value=updated_payment)
        payment_service.event_bus.publish = AsyncMock()
        
        result = await payment_service.update_payment_status(
            sample_payment.id,
            "refunded",
            metadata={"refund_reason": "customer_request"},
        )
        
        assert result.status == "refunded"
        assert result.metadata["refund_reason"] == "customer_request"


# ---------------------------------------------------------------------------
# Test: delete_payment
# ---------------------------------------------------------------------------


class TestDeletePayment:
    """Tests for the delete_payment function."""

    @pytest.mark.asyncio
    async def test_delete_payment_success(self, payment_service, sample_payment):
        """Test successful payment deletion."""
        payment_service.db.delete_payment = AsyncMock(return_value=True)
        payment_service.cache.delete = AsyncMock()
        
        result = await payment_service.delete_payment(sample_payment.id)
        
        assert result is True
        payment_service.db.delete_payment.assert_called_once_with(sample_payment.id)

    @pytest.mark.asyncio
    async def test_delete_payment_not_found(self, payment_service):
        """Test deleting non-existent payment."""
        payment_id = str(uuid4())
        
        payment_service.db.delete_payment = AsyncMock(return_value=False)
        
        result = await payment_service.delete_payment(payment_id)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_payment_clears_cache(self, payment_service, sample_payment):
        """Test that delete_payment clears the cache entry."""
        payment_service.db.delete_payment = AsyncMock(return_value=True)
        payment_service.cache.delete = AsyncMock()
        
        await payment_service.delete_payment(sample_payment.id)
        
        payment_service.cache.delete.assert_called_once()
        cache_key = payment_service.cache.delete.call_args[0][0]
        assert sample_payment.id in cache_key

    @pytest.mark.asyncio
    async def test_delete_payment_invalid_id(self, payment_service):
        """Test delete_payment with invalid ID format."""
        with pytest.raises(ValueError, match="Invalid payment ID"):
            await payment_service.delete_payment("not-a-valid-uuid")

    @pytest.mark.asyncio
    async def test_delete_payment_database_error(self, payment_service):
        """Test delete_payment handles database errors."""
        payment_id = str(uuid4())
        
        payment_service.db.delete_payment = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        with pytest.raises(Exception, match="Database error"):
            await payment_service.delete_payment(payment_id)

    @pytest.mark.asyncio
    async def test_delete_payment_already_deleted(self, payment_service, sample_payment):
        """Test deleting an already deleted payment."""
        payment_service.db.delete_payment = AsyncMock(return_value=False)
        
        result = await payment_service.delete_payment(sample_payment.id)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_payment_cannot_delete_completed(self, payment_service, sample_payment):
        """Test that completed payments cannot be deleted."""
        sample_payment.status = "completed"
        
        with pytest.raises(ValueError, match="Cannot delete completed payment"):
            await payment_service.delete_payment(sample_payment.id)

    @pytest.mark.asyncio
    async def test_delete_payment_publishes_event(self, payment_service, sample_payment):
        """Test that delete_payment publishes an event."""
        payment_service.db.delete_payment = AsyncMock(return_value=True)
        payment_service.cache.delete = AsyncMock()
        payment_service.event_bus.publish = AsyncMock()
        
        await payment_service.delete_payment(sample_payment.id)
        
        payment_service.event_bus.publish.assert_called_once()
        call_args = payment_service.event_bus.publish.call_args
        assert "payment.deleted" in str(call_args)
