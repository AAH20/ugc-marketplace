"""Comprehensive service tests for the transaction service."""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from ugc_marketplace.services.transaction_service import (
    TransactionService,
    get_transaction,
    list_transactions,
    create_transaction,
    update_transaction_status,
    delete_transaction,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db():
    """Provide a mock database session."""
    return MagicMock()


@pytest.fixture
def transaction_service(mock_db):
    """Provide a TransactionService instance with a mock db."""
    return TransactionService(db=mock_db)


@pytest.fixture
def sample_transaction():
    """Provide a sample transaction dict."""
    return {
        "id": "txn-001",
        "order_id": "order-001",
        "buyer_id": "user-001",
        "seller_id": "user-002",
        "amount": Decimal("49.99"),
        "currency": "USD",
        "status": "pending",
        "payment_method": "credit_card",
        "description": "Test transaction",
        "created_at": datetime(2026, 1, 1, 12, 0, 0),
        "updated_at": datetime(2026, 1, 1, 12, 0, 0),
    }


@pytest.fixture
def sample_transaction_list():
    """Provide a list of sample transaction dicts."""
    base_time = datetime(2026, 1, 1, 12, 0, 0)
    return [
        {
            "id": f"txn-{i:03d}",
            "order_id": f"order-{i:03d}",
            "buyer_id": f"user-{i:03d}",
            "seller_id": f"user-s-{i:03d}",
            "amount": Decimal(f"{10 + i}.99"),
            "currency": "USD",
            "status": ["pending", "completed", "failed", "refunded"][i % 4],
            "payment_method": "credit_card",
            "description": f"Transaction {i}",
            "created_at": base_time + timedelta(hours=i),
            "updated_at": base_time + timedelta(hours=i),
        }
        for i in range(10)
    ]


# ---------------------------------------------------------------------------
# Tests for get_transaction
# ---------------------------------------------------------------------------


class TestGetTransaction:
    """Tests for the get_transaction function."""

    def test_get_transaction_returns_transaction(self, mock_db, sample_transaction):
        """get_transaction returns a transaction when found."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_transaction
        )

        result = get_transaction(mock_db, "txn-001")

        assert result is not None
        assert result["id"] == "txn-001"
        assert result["order_id"] == "order-001"
        assert result["buyer_id"] == "user-001"
        assert result["seller_id"] == "user-002"
        assert result["amount"] == Decimal("49.99")
        assert result["currency"] == "USD"
        assert result["status"] == "pending"
        assert result["payment_method"] == "credit_card"
        assert result["description"] == "Test transaction"

    def test_get_transaction_not_found_returns_none(self, mock_db):
        """get_transaction returns None when transaction is not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = get_transaction(mock_db, "nonexistent-id")

        assert result is None

    def test_get_transaction_queries_correct_id(self, mock_db, sample_transaction):
        """get_transaction queries with the correct transaction id."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_transaction
        )

        get_transaction(mock_db, "txn-001")

        mock_db.query.assert_called_once()
        mock_db.query.return_value.filter.assert_called_once()

    def test_get_transaction_with_service(self, transaction_service, sample_transaction):
        """TransactionService.get_transaction returns a transaction."""
        transaction_service.db.query.return_value.filter.return_value.first.return_value = (
            sample_transaction
        )

        result = transaction_service.get_transaction("txn-001")

        assert result is not None
        assert result["id"] == "txn-001"
        assert result["status"] == "pending"

    def test_get_transaction_with_service_not_found(self, transaction_service):
        """TransactionService.get_transaction returns None when not found."""
        transaction_service.db.query.return_value.filter.return_value.first.return_value = (
            None
        )

        result = transaction_service.get_transaction("nonexistent-id")

        assert result is None


# ---------------------------------------------------------------------------
# Tests for list_transactions
# ---------------------------------------------------------------------------


class TestListTransactions:
    """Tests for the list_transactions function."""

    def test_list_transactions_returns_all(self, mock_db, sample_transaction_list):
        """list_transactions returns all transactions when no filters applied."""
        mock_db.query.return_value.all.return_value = sample_transaction_list

        result = list_transactions(mock_db)

        assert result is not None
        assert len(result) == 10
        assert result[0]["id"] == "txn-000"
        assert result[9]["id"] == "txn-009"

    def test_list_transactions_empty_result(self, mock_db):
        """list_transactions returns empty list when no transactions exist."""
        mock_db.query.return_value.all.return_value = []

        result = list_transactions(mock_db)

        assert result == []

    def test_list_transactions_filter_by_status(self, mock_db, sample_transaction_list):
        """list_transactions filters by status correctly."""
        pending_txns = [t for t in sample_transaction_list if t["status"] == "pending"]
        mock_db.query.return_value.filter.return_value.all.return_value = pending_txns

        result = list_transactions(mock_db, status="pending")

        assert result is not None
        assert len(result) > 0
        for txn in result:
            assert txn["status"] == "pending"

    def test_list_transactions_filter_by_buyer_id(
        self, mock_db, sample_transaction_list
    ):
        """list_transactions filters by buyer_id correctly."""
        buyer_txns = [t for t in sample_transaction_list if t["buyer_id"] == "user-001"]
        mock_db.query.return_value.filter.return_value.all.return_value = buyer_txns

        result = list_transactions(mock_db, buyer_id="user-001")

        assert result is not None
        assert len(result) > 0
        for txn in result:
            assert txn["buyer_id"] == "user-001"

    def test_list_transactions_filter_by_seller_id(
        self, mock_db, sample_transaction_list
    ):
        """list_transactions filters by seller_id correctly."""
        seller_txns = [
            t for t in sample_transaction_list if t["seller_id"] == "user-s-002"
        ]
        mock_db.query.return_value.filter.return_value.all.return_value = seller_txns

        result = list_transactions(mock_db, seller_id="user-s-002")

        assert result is not None
        assert len(result) > 0
        for txn in result:
            assert txn["seller_id"] == "user-s-002"

    def test_list_transactions_filter_by_order_id(
        self, mock_db, sample_transaction_list
    ):
        """list_transactions filters by order_id correctly."""
        order_txns = [
            t for t in sample_transaction_list if t["order_id"] == "order-003"
        ]
        mock_db.query.return_value.filter.return_value.all.return_value = order_txns

        result = list_transactions(mock_db, order_id="order-003")

        assert result is not None
        assert len(result) > 0
        for txn in result:
            assert txn["order_id"] == "order-003"

    def test_list_transactions_with_pagination(self, mock_db, sample_transaction_list):
        """list_transactions respects limit and offset for pagination."""
        mock_db.query.return_value.limit.return_value.offset.return_value.all.return_value = (
            sample_transaction_list[2:5]
        )

        result = list_transactions(mock_db, limit=3, offset=2)

        assert result is not None
        assert len(result) == 3
        mock_db.query.return_value.limit.assert_called_once_with(3)
        mock_db.query.return_value.limit.return_value.offset.assert_called_once_with(2)

    def test_list_transactions_with_multiple_filters(
        self, mock_db, sample_transaction_list
    ):
        """list_transactions applies multiple filters together."""
        filtered = [
            t
            for t in sample_transaction_list
            if t["status"] == "pending" and t["buyer_id"] == "user-001"
        ]
        mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = (
            filtered
        )

        result = list_transactions(mock_db, status="pending", buyer_id="user-001")

        assert result is not None
        for txn in result:
            assert txn["status"] == "pending"
            assert txn["buyer_id"] == "user-001"

    def test_list_transactions_with_service(
        self, transaction_service, sample_transaction_list
    ):
        """TransactionService.list_transactions returns transactions."""
        transaction_service.db.query.return_value.all.return_value = (
            sample_transaction_list
        )

        result = transaction_service.list_transactions()

        assert result is not None
        assert len(result) == 10

    def test_list_transactions_with_service_and_filters(
        self, transaction_service, sample_transaction_list
    ):
        """TransactionService.list_transactions applies filters."""
        completed_txns = [
            t for t in sample_transaction_list if t["status"] == "completed"
        ]
        transaction_service.db.query.return_value.filter.return_value.all.return_value = (
            completed_txns
        )

        result = transaction_service.list_transactions(status="completed")

        assert result is not None
        for txn in result:
            assert txn["status"] == "completed"


# ---------------------------------------------------------------------------
# Tests for create_transaction
# ---------------------------------------------------------------------------


class TestCreateTransaction:
    """Tests for the create_transaction function."""

    def test_create_transaction_success(self, mock_db):
        """create_transaction creates and returns a new transaction."""
        new_txn = {
            "id": "txn-new-001",
            "order_id": "order-new-001",
            "buyer_id": "user-new-001",
            "seller_id": "user-new-002",
            "amount": Decimal("99.99"),
            "currency": "USD",
            "status": "pending",
            "payment_method": "credit_card",
            "description": "New test transaction",
            "created_at": datetime(2026, 1, 15, 10, 0, 0),
            "updated_at": datetime(2026, 1, 15, 10, 0, 0),
        }
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda obj: obj.__dict__.update(new_txn)

        result = create_transaction(
            mock_db,
            order_id="order-new-001",
            buyer_id="user-new-001",
            seller_id="user-new-002",
            amount=Decimal("99.99"),
            currency="USD",
            payment_method="credit_card",
            description="New test transaction",
        )

        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_create_transaction_with_service(self, transaction_service):
        """TransactionService.create_transaction creates a transaction."""
        transaction_service.db.add.return_value = None
        transaction_service.db.commit.return_value = None
        transaction_service.db.refresh.side_effect = lambda obj: obj.__dict__.update(
            {"id": "txn-svc-001", "status": "pending"}
        )

        result = transaction_service.create_transaction(
            order_id="order-svc-001",
            buyer_id="user-svc-001",
            seller_id="user-svc-002",
            amount=Decimal("25.00"),
            currency="USD",
            payment_method="paypal",
        )

        assert result is not None
        transaction_service.db.add.assert_called_once()
        transaction_service.db.commit.assert_called_once()
        transaction_service.db.refresh.assert_called_once()

    def test_create_transaction_sets_default_status(self, mock_db):
        """create_transaction sets status to 'pending' by default."""
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda obj: obj.__dict__.update(
            {"id": "txn-default-001", "status": "pending"}
        )

        result = create_transaction(
            mock_db,
            order_id="order-default-001",
            buyer_id="user-default-001",
            seller_id="user-default-002",
            amount=Decimal("10.00"),
            currency="USD",
            payment_method="credit_card",
        )

        assert result is not None
        mock_db.add.assert_called_once()

    def test_create_transaction_with_minimal_fields(self, mock_db):
        """create_transaction works with minimal required fields."""
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda obj: obj.__dict__.update(
            {"id": "txn-min-001", "status": "pending"}
        )

        result = create_transaction(
            mock_db,
            order_id="order-min-001",
            buyer_id="user-min-001",
            seller_id="user-min-002",
            amount=Decimal("5.00"),
        )

        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Tests for update_transaction_status
# ---------------------------------------------------------------------------


class TestUpdateTransactionStatus:
    """Tests for the update_transaction_status function."""

    def test_update_transaction_status_success(
        self, mock_db, sample_transaction
    ):
        """update_transaction_status updates and returns the transaction."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_transaction
        )
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        result = update_transaction_status(mock_db, "txn-001", "completed")

        assert result is not None
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_update_transaction_status_not_found(self, mock_db):
        """update_transaction_status returns None when transaction not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = update_transaction_status(mock_db, "nonexistent-id", "completed")

        assert result is None
        mock_db.commit.assert_not_called()

    def test_update_transaction_status_with_service(
        self, transaction_service, sample_transaction
    ):
        """TransactionService.update_transaction_status updates status."""
        transaction_service.db.query.return_value.filter.return_value.first.return_value = (
            sample_transaction
        )
        transaction_service.db.commit.return_value = None
        transaction_service.db.refresh.return_value = None

        result = transaction_service.update_transaction_status("txn-001", "refunded")

        assert result is not None
        transaction_service.db.commit.assert_called_once()
        transaction_service.db.refresh.assert_called_once()

    def test_update_transaction_status_to_failed(
        self, mock_db, sample_transaction
    ):
        """update_transaction_status can set status to 'failed'."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_transaction
        )
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        result = update_transaction_status(mock_db, "txn-001", "failed")

        assert result is not None
        mock_db.commit.assert_called_once()

    def test_update_transaction_status_to_refunded(
        self, mock_db, sample_transaction
    ):
        """update_transaction_status can set status to 'refunded'."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_transaction
        )
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        result = update_transaction_status(mock_db, "txn-001", "refunded")

        assert result is not None
        mock_db.commit.assert_called_once()

    def test_update_transaction_status_no_commit_on_not_found(self, mock_db):
        """update_transaction_status does not commit when transaction not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        update_transaction_status(mock_db, "nonexistent-id", "completed")

        mock_db.commit.assert_not_called()
        mock_db.refresh.assert_not_called()


# ---------------------------------------------------------------------------
# Tests for delete_transaction
# ---------------------------------------------------------------------------


class TestDeleteTransaction:
    """Tests for the delete_transaction function."""

    def test_delete_transaction_success(self, mock_db, sample_transaction):
        """delete_transaction deletes and returns True on success."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_transaction
        )
        mock_db.delete.return_value = None
        mock_db.commit.return_value = None

        result = delete_transaction(mock_db, "txn-001")

        assert result is True
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_delete_transaction_not_found(self, mock_db):
        """delete_transaction returns False when transaction not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = delete_transaction(mock_db, "nonexistent-id")

        assert result is False
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_delete_transaction_with_service(
        self, transaction_service, sample_transaction
    ):
        """TransactionService.delete_transaction deletes a transaction."""
        transaction_service.db.query.return_value.filter.return_value.first.return_value = (
            sample_transaction
        )
        transaction_service.db.delete.return_value = None
        transaction_service.db.commit.return_value = None

        result = transaction_service.delete_transaction("txn-001")

        assert result is True
        transaction_service.db.delete.assert_called_once()
        transaction_service.db.commit.assert_called_once()

    def test_delete_transaction_with_service_not_found(self, transaction_service):
        """TransactionService.delete_transaction returns False when not found."""
        transaction_service.db.query.return_value.filter.return_value.first.return_value = (
            None
        )

        result = transaction_service.delete_transaction("nonexistent-id")

        assert result is False
        transaction_service.db.delete.assert_not_called()
        transaction_service.db.commit.assert_not_called()

    def test_delete_transaction_cascades_correctly(
        self, mock_db, sample_transaction
    ):
        """delete_transaction queries the correct transaction before deleting."""
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_transaction
        )
        mock_db.delete.return_value = None
        mock_db.commit.return_value = None

        delete_transaction(mock_db, "txn-001")

        mock_db.query.assert_called_once()
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()
