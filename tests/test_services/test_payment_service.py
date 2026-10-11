"""Coverage-gap tests for :mod:`ugc_marketplace.services.payment_service`.

``payment_service`` had zero references anywhere under ``tests/``.  It keeps
payments and balances in module-global stores, reset around each test.
"""

from __future__ import annotations

import pytest

from ugc_marketplace.services import payment_service as ps
from ugc_marketplace.services.payment_service import (
    InsufficientFundsError,
    InvalidPaymentDataError,
    PaymentNotFoundError,
    PaymentService,
)


@pytest.fixture(autouse=True)
def _clean_stores():
    ps._payments_store.clear()
    ps._user_balances.clear()
    yield
    ps._payments_store.clear()
    ps._user_balances.clear()


def _payment(**overrides):
    data = {
        "user_id": "user-1",
        "amount": 25.0,
        "currency": "usd",
        "payment_method": "card",
    }
    data.update(overrides)
    return data


def test_process_payment_completes_and_updates_balance():
    record = ps.process_payment(_payment())

    assert record["status"] == "completed"
    assert record["currency"] == "USD"  # normalised to upper case
    assert ps._user_balances["user-1"] == 25.0
    assert ps.get_payment(record["payment_id"])["payment_id"] == record["payment_id"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": 0},
        {"amount": -5},
        {"currency": "us"},
        {"user_id": ""},
        {"payment_method": ""},
    ],
)
def test_process_payment_validation(overrides):
    with pytest.raises(InvalidPaymentDataError):
        ps.process_payment(_payment(**overrides))


def test_process_payment_missing_fields():
    with pytest.raises(InvalidPaymentDataError):
        ps.process_payment({"user_id": "u"})


def test_initiate_payout_success_and_insufficient_funds():
    ps.process_payment(_payment(user_id="creator-1", amount=100.0))

    payout = ps.initiate_payout("creator-1", 40.0)
    assert payout["status"] == "initiated"
    assert ps._user_balances["creator-1"] == 60.0

    with pytest.raises(InsufficientFundsError):
        ps.initiate_payout("creator-1", 1000.0)


def test_initiate_payout_validation():
    with pytest.raises(InvalidPaymentDataError):
        ps.initiate_payout("", 10.0)
    with pytest.raises(InvalidPaymentDataError):
        ps.initiate_payout("creator-1", 0)


def test_payment_history_includes_payments_and_payouts():
    ps.process_payment(_payment(user_id="creator-1", amount=50.0))
    ps.initiate_payout("creator-1", 10.0)

    history = ps.get_payment_history("creator-1")
    assert len(history) == 2
    with pytest.raises(InvalidPaymentDataError):
        ps.get_payment_history("")


def test_get_payment_missing_raises():
    with pytest.raises(PaymentNotFoundError):
        ps.get_payment("nope")


def test_list_payments_filters_and_paginates():
    ps.create_payment(_payment(user_id="a", amount=1.0))
    ps.create_payment(_payment(user_id="b", amount=2.0))

    assert len(ps.list_payments({}, 1, 10)) == 2
    assert len(ps.list_payments({"user_id": "a"}, 1, 10)) == 1
    with pytest.raises(InvalidPaymentDataError):
        ps.list_payments({}, 0, 10)


def test_update_payment_status_validates_and_updates():
    record = ps.create_payment(_payment())

    updated = ps.update_payment_status(record["payment_id"], "completed")
    assert updated["status"] == "completed"
    with pytest.raises(InvalidPaymentDataError):
        ps.update_payment_status(record["payment_id"], "bogus")
    with pytest.raises(PaymentNotFoundError):
        ps.update_payment_status("missing", "completed")


def test_delete_payment_removes_record():
    record = ps.create_payment(_payment())

    assert ps.delete_payment(record["payment_id"]) is True
    with pytest.raises(PaymentNotFoundError):
        ps.delete_payment(record["payment_id"])


def test_payment_service_class_delegates():
    service = PaymentService(db=None)
    record = service.create_payment(_payment())

    assert service.get_payment(record["payment_id"])["payment_id"] == record["payment_id"]
    assert len(service.list_payments()) == 1
    assert service.delete_payment(record["payment_id"]) is True
