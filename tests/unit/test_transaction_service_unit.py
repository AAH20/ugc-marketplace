"""Unit tests for the transaction service module-level functions.

The service exposes plain functions (``create_transaction``, ``get_transaction``,
``list_transactions``, ...) operating on a module-level in-memory store, plus a
thin ``TransactionService`` class that wraps them. These tests target the real
signatures and the real custom exceptions.

The in-memory store is module-global, so an autouse fixture snapshots and
restores it around each test to keep cases isolated.
"""
import pytest

from ugc_marketplace.services import transaction_service as ts
from ugc_marketplace.services.transaction_service import (
    RefundReason,
    TransactionNotFoundError,
    TransactionStateError,
    TransactionStatus,
    TransactionValidationError,
    cancel_transaction,
    complete_transaction,
    create_transaction,
    delete_transaction,
    get_transaction,
    list_transactions,
    process_refund,
    update_transaction_status,
)


@pytest.fixture(autouse=True)
def clean_store():
    """Give every test an empty transaction store."""
    ts._transactions.clear()
    yield
    ts._transactions.clear()


@pytest.fixture
def valid_data():
    """Minimal valid payload accepted by create_transaction."""
    return {
        "buyer_id": "user-buyer-001",
        "seller_id": "user-seller-001",
        "amount": 49.99,
        "currency": "USD",
    }


@pytest.fixture
def completed_transaction(valid_data):
    """A COMPLETED transaction, ready to be refunded."""
    txn = create_transaction(valid_data)
    update_transaction_status(txn["id"], "completed")
    return get_transaction(txn["id"])


class TestCreateTransaction:
    """Tests for create_transaction."""

    def test_create_transaction_returns_dict(self, valid_data):
        result = create_transaction(valid_data)

        assert isinstance(result, dict)
        assert result["buyer_id"] == valid_data["buyer_id"]
        assert result["seller_id"] == valid_data["seller_id"]
        assert result["amount"] == valid_data["amount"]
        assert result["currency"] == "USD"

    def test_create_transaction_generates_uuid_and_timestamps(self, valid_data):
        import uuid

        result = create_transaction(valid_data)

        assert uuid.UUID(result["id"])
        assert result["created_at"] is not None
        assert result["updated_at"] is not None

    def test_new_transaction_is_pending(self, valid_data):
        assert create_transaction(valid_data)["status"] == TransactionStatus.PENDING.value

    def test_create_transaction_coerces_amount_to_float(self, valid_data):
        """An int amount is normalized to float."""
        valid_data["amount"] = 100

        assert isinstance(create_transaction(valid_data)["amount"], float)
        assert create_transaction(valid_data)["amount"] == 100.0

    def test_currency_is_uppercased(self, valid_data):
        """Lowercase currency codes are normalised."""
        valid_data["currency"] = "aed"

        assert create_transaction(valid_data)["currency"] == "AED"

    def test_optional_fields_default_sensibly(self, valid_data):
        result = create_transaction(valid_data)

        assert result["description"] is None
        assert result["metadata"] == {}
        assert result["refunds"] == []
        assert result["refunded_amount"] == 0
        assert result["remaining_amount"] == result["amount"]

    def test_optional_fields_are_persisted(self, valid_data):
        valid_data["description"] = "Creator video licence"
        valid_data["metadata"] = {"content_id": "c-1"}

        result = create_transaction(valid_data)

        assert result["description"] == "Creator video licence"
        assert result["metadata"] == {"content_id": "c-1"}

    def test_ids_are_unique(self, valid_data):
        first = create_transaction(valid_data)["id"]
        second = create_transaction(valid_data)["id"]

        assert first != second

    def test_missing_required_fields_raises(self):
        with pytest.raises(TransactionValidationError, match="Missing required fields"):
            create_transaction({"buyer_id": "a"})

    def test_blank_buyer_id_raises(self, valid_data):
        valid_data["buyer_id"] = "   "

        with pytest.raises(TransactionValidationError, match="buyer_id"):
            create_transaction(valid_data)

    def test_non_string_buyer_id_raises(self, valid_data):
        valid_data["buyer_id"] = 123

        with pytest.raises(TransactionValidationError, match="buyer_id must be a non-empty string"):
            create_transaction(valid_data)

    def test_blank_seller_id_raises(self, valid_data):
        valid_data["seller_id"] = ""

        with pytest.raises(TransactionValidationError, match="seller_id"):
            create_transaction(valid_data)

    def test_identical_buyer_and_seller_raises(self, valid_data):
        valid_data["seller_id"] = valid_data["buyer_id"]

        with pytest.raises(TransactionValidationError, match="must differ"):
            create_transaction(valid_data)

    @pytest.mark.parametrize("amount", [0, -1, -0.01])
    def test_non_positive_amount_raises(self, valid_data, amount):
        valid_data["amount"] = amount

        with pytest.raises(TransactionValidationError, match="amount must be a positive number"):
            create_transaction(valid_data)

    def test_non_numeric_amount_raises(self, valid_data):
        valid_data["amount"] = "lots"

        with pytest.raises(TransactionValidationError, match="amount must be a positive number"):
            create_transaction(valid_data)

    @pytest.mark.parametrize("currency", ["US", "USDD", ""])
    def test_invalid_currency_length_raises(self, valid_data, currency):
        """Currency validation only enforces a 3-character ISO-code length."""
        valid_data["currency"] = currency

        with pytest.raises(TransactionValidationError, match="3-letter ISO code"):
            create_transaction(valid_data)

    def test_failed_validation_does_not_persist(self, valid_data):
        valid_data["amount"] = 0

        with pytest.raises(TransactionValidationError):
            create_transaction(valid_data)

        assert ts._transactions == {}


class TestGetTransaction:
    """Tests for get_transaction."""

    def test_get_transaction_returns_stored_data(self, valid_data):
        created = create_transaction(valid_data)

        result = get_transaction(created["id"])

        assert result["id"] == created["id"]
        assert result["amount"] == created["amount"]

    def test_get_transaction_not_found_raises(self):
        with pytest.raises(TransactionNotFoundError, match="Transaction not found"):
            get_transaction("does-not-exist")

    @pytest.mark.parametrize("bad_id", ["", None, 0])
    def test_get_transaction_invalid_id_raises(self, bad_id):
        with pytest.raises(TransactionValidationError, match="transaction_id"):
            get_transaction(bad_id)


class TestListTransactions:
    """Tests for list_transactions."""

    @pytest.fixture
    def several(self, valid_data):
        """Three transactions spanning two buyers, sellers and statuses."""
        created = []
        for i in range(3):
            data = dict(valid_data, buyer_id=f"buyer-{i}", seller_id=f"seller-{i}", amount=10.0 + i)
            created.append(create_transaction(data))
        update_transaction_status(created[0]["id"], "completed")
        update_transaction_status(created[1]["id"], "failed")
        return created

    def test_list_returns_all(self, several):
        results = list_transactions({}, 1, 20)

        assert len(results) == 3
        assert all(isinstance(r, dict) for r in results)

    def test_list_empty_store(self):
        assert list_transactions({}, 1, 20) == []

    def test_filter_by_buyer_id(self, several):
        results = list_transactions({"buyer_id": "buyer-1"}, 1, 20)

        assert len(results) == 1
        assert results[0]["id"] == several[1]["id"]

    def test_filter_by_seller_id(self, several):
        results = list_transactions({"seller_id": "seller-2"}, 1, 20)

        assert [r["id"] for r in results] == [several[2]["id"]]

    def test_filter_by_status(self, several):
        results = list_transactions({"status": "completed"}, 1, 20)

        assert [r["id"] for r in results] == [several[0]["id"]]

    def test_combined_filters(self, several):
        results = list_transactions(
            {"buyer_id": "buyer-0", "status": "failed"}, 1, 20
        )

        assert results == []

    def test_pagination_returns_page_slice(self, several):
        page1 = list_transactions({}, 1, 2)
        page2 = list_transactions({}, 2, 2)

        assert len(page1) == 2
        assert len(page2) == 1
        assert {r["id"] for r in page1}.isdisjoint({r["id"] for r in page2})

    def test_page_beyond_range_returns_empty(self, several):
        assert list_transactions({}, 10, 20) == []

    def test_page_zero_raises(self):
        with pytest.raises(TransactionValidationError, match="page must be >= 1"):
            list_transactions({}, 0, 20)

    def test_page_size_zero_raises(self):
        with pytest.raises(TransactionValidationError, match="page_size must be >= 1"):
            list_transactions({}, 1, 0)


class TestUpdateTransactionStatus:
    """Tests for update_transaction_status."""

    def test_update_status(self, valid_data):
        txn = create_transaction(valid_data)

        result = update_transaction_status(txn["id"], "completed")

        assert result["status"] == "completed"
        assert get_transaction(txn["id"])["status"] == "completed"

    def test_update_status_advances_updated_at(self, valid_data):
        txn = create_transaction(valid_data)

        result = update_transaction_status(txn["id"], "completed")

        assert result["updated_at"] >= txn["updated_at"]

    def test_update_status_to_same_value_is_allowed(self, valid_data):
        txn = create_transaction(valid_data)

        assert update_transaction_status(txn["id"], "pending")["status"] == "pending"

    def test_unknown_status_raises_and_lists_valid_values(self, valid_data):
        txn = create_transaction(valid_data)

        with pytest.raises(TransactionValidationError, match="Invalid status") as exc:
            update_transaction_status(txn["id"], "teleported")

        # the error message enumerates the valid statuses
        assert "completed" in str(exc.value)

    def test_update_status_not_found_raises(self):
        with pytest.raises(TransactionNotFoundError):
            update_transaction_status("nope", "completed")

    def test_update_status_invalid_id_raises(self):
        with pytest.raises(TransactionValidationError, match="transaction_id"):
            update_transaction_status("", "completed")


class TestDeleteTransaction:
    """Tests for delete_transaction."""

    def test_delete_removes_transaction(self, valid_data):
        txn = create_transaction(valid_data)

        assert delete_transaction(txn["id"]) is True
        with pytest.raises(TransactionNotFoundError):
            get_transaction(txn["id"])

    def test_delete_missing_raises(self):
        with pytest.raises(TransactionNotFoundError):
            delete_transaction("does-not-exist")

    def test_delete_invalid_id_raises(self):
        with pytest.raises(TransactionValidationError, match="transaction_id"):
            delete_transaction(None)


class TestProcessRefund:
    """Tests for process_refund."""

    def test_full_refund_marks_refunded(self, completed_transaction):
        result = process_refund(completed_transaction["id"])

        assert isinstance(result, ts.Transaction)
        assert result.status == TransactionStatus.REFUNDED
        assert result.refunded_amount == result.amount
        assert result.remaining_amount == 0

    def test_partial_refund_marks_partially_refunded(self, completed_transaction):
        result = process_refund(completed_transaction["id"], amount=20.00)

        assert result.status == TransactionStatus.PARTIALLY_REFUNDED
        assert result.refunded_amount == 20.00
        assert result.remaining_amount == pytest.approx(29.99)

    def test_refund_records_reason_and_timestamp(self, completed_transaction):
        result = process_refund(completed_transaction["id"], reason=RefundReason.FRAUD)

        refund = result.refunds[0]
        assert refund["amount"] == result.amount
        assert refund["reason"] == RefundReason.FRAUD.value
        assert "processed_at" in refund

    def test_successive_partial_refunds_accumulate(self, completed_transaction):
        """Refunds accumulate; the final one only reaches 'refunded' if the
        running total exactly equals the original amount.

        Amounts are floats, so 20.00 + 29.99 lands a few ULPs short of 49.99
        and the transaction settles as partially_refunded. Pinned here so the
        float behaviour is visible rather than surprising.
        """
        txn_id = completed_transaction["id"]

        process_refund(txn_id, amount=20.00)
        result = process_refund(txn_id, amount=29.99)

        assert result.refunded_amount == pytest.approx(49.99, abs=1e-9)
        assert result.status == TransactionStatus.PARTIALLY_REFUNDED
        assert len(result.refunds) == 2

    def test_single_full_refund_reaches_refunded(self, completed_transaction):
        """Refunding the whole remaining amount in one call does reach REFUNDED."""
        result = process_refund(completed_transaction["id"])

        assert result.refunded_amount == completed_transaction["amount"]
        assert result.status == TransactionStatus.REFUNDED

    def test_refund_not_found_raises(self):
        with pytest.raises(TransactionNotFoundError):
            process_refund("does-not-exist")

    def test_refund_pending_transaction_raises(self, valid_data):
        txn = create_transaction(valid_data)

        with pytest.raises(TransactionStateError, match="pending"):
            process_refund(txn["id"])

    def test_refund_failed_transaction_raises(self, valid_data):
        txn = create_transaction(valid_data)
        update_transaction_status(txn["id"], "failed")

        with pytest.raises(TransactionStateError, match="failed"):
            process_refund(txn["id"])

    def test_double_refund_raises(self, completed_transaction):
        process_refund(completed_transaction["id"])

        with pytest.raises(TransactionStateError, match="already been fully refunded"):
            process_refund(completed_transaction["id"])

    def test_refund_non_positive_amount_raises(self, completed_transaction):
        with pytest.raises(TransactionValidationError, match="must be positive"):
            process_refund(completed_transaction["id"], amount=0)

    def test_refund_exceeding_remaining_raises(self, completed_transaction):
        with pytest.raises(TransactionValidationError, match="exceeds remaining"):
            process_refund(completed_transaction["id"], amount=100.00)


class TestCancelTransaction:
    """Tests for cancel_transaction."""

    def test_cancel_pending_transaction(self, valid_data):
        txn = create_transaction(valid_data)

        result = cancel_transaction(txn["id"])

        assert result.status == TransactionStatus.FAILED
        assert get_transaction(txn["id"])["status"] == "failed"

    def test_cancel_completed_transaction_raises(self, completed_transaction):
        with pytest.raises(TransactionStateError, match="Cannot cancel"):
            cancel_transaction(completed_transaction["id"])

    def test_cancel_not_found_raises(self):
        with pytest.raises(TransactionNotFoundError):
            cancel_transaction("does-not-exist")


class TestCompleteTransaction:
    """Tests for complete_transaction."""

    def test_complete_pending_transaction(self, valid_data):
        txn = create_transaction(valid_data)

        result = complete_transaction(txn["id"])

        assert result.status == TransactionStatus.COMPLETED
        assert get_transaction(txn["id"])["status"] == "completed"

    def test_complete_already_completed_raises(self, completed_transaction):
        with pytest.raises(TransactionStateError, match="Cannot complete"):
            complete_transaction(completed_transaction["id"])

    def test_complete_not_found_raises(self):
        with pytest.raises(TransactionNotFoundError):
            complete_transaction("does-not-exist")


class TestTransactionServiceClass:
    """The TransactionService wrapper delegates to the module functions."""

    @pytest.fixture
    def service(self):
        return ts.TransactionService(db=None)

    def test_create_and_get_through_service(self, service, valid_data):
        created = service.create_transaction(valid_data)

        assert service.get_transaction(created["id"])["id"] == created["id"]

    def test_list_defaults_through_service(self, service, valid_data):
        service.create_transaction(valid_data)

        assert len(service.list_transactions()) == 1

    def test_update_and_delete_through_service(self, service, valid_data):
        created = service.create_transaction(valid_data)

        assert service.update_transaction_status(created["id"], "completed")["status"] == "completed"
        assert service.delete_transaction(created["id"]) is True
        with pytest.raises(TransactionNotFoundError):
            service.get_transaction(created["id"])


class TestTransactionDataclass:
    """The Transaction dataclass and its derived properties."""

    def test_remaining_amount_tracks_refunds(self):
        txn = ts.Transaction(
            id="t-1", buyer_id="b", seller_id="s", amount=100.0, currency="USD",
            status=TransactionStatus.COMPLETED,
            created_at=ts.datetime.now(ts.UTC), updated_at=ts.datetime.now(ts.UTC),
            refunds=[{"amount": 40.0}],
        )

        assert txn.refunded_amount == 40.0
        assert txn.remaining_amount == 60.0

    def test_to_dict_serializes_status_and_timestamps(self):
        now = ts.datetime.now(ts.UTC)
        txn = ts.Transaction(
            id="t-1", buyer_id="b", seller_id="s", amount=10.0, currency="USD",
            status=TransactionStatus.PENDING, created_at=now, updated_at=now,
        )

        data = txn.to_dict()

        assert data["status"] == "pending"
        assert data["created_at"] == now.isoformat()
        assert set(data) >= {
            "id", "buyer_id", "seller_id", "amount", "currency", "status",
            "created_at", "updated_at", "description", "metadata", "refunds",
            "refunded_amount", "remaining_amount",
        }

    @pytest.mark.parametrize(
        ("exc_cls", "parent"),
        [
            (TransactionNotFoundError, ts.TransactionError),
            (TransactionValidationError, ts.TransactionError),
            (TransactionStateError, ts.TransactionError),
        ],
    )
    def test_error_hierarchy(self, exc_cls, parent):
        assert issubclass(exc_cls, parent)