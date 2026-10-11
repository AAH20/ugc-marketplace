"""Coverage-gap tests for :mod:`ugc_marketplace.services.notification_service`
and :mod:`ugc_marketplace.services.analytics_service`.

Both were zero-reference under ``tests/``.  NotificationService's in-memory
path and the analytics helpers are deterministic and need no infrastructure.
"""

from __future__ import annotations

import pytest

from ugc_marketplace.services import analytics_service as an
from ugc_marketplace.services.analytics_service import (
    AnalyticsService,
    get_content_analytics,
    get_creator_analytics,
    get_marketplace_metrics,
    get_revenue_analytics,
)
from ugc_marketplace.services.notification_service import (
    NotificationService,
)


# ---------------------------------------------------------------------------
# NotificationService (in-memory)
# ---------------------------------------------------------------------------


def test_send_and_fetch_notification():
    service = NotificationService()
    sent = service.send_notification("user-1", "hello")

    assert sent["read"] is False
    assert service.get_notifications("user-1")[0]["message"] == "hello"


def test_send_notification_requires_fields():
    service = NotificationService()
    with pytest.raises(ValueError):
        service.send_notification("", "hi")
    with pytest.raises(ValueError):
        service.send_notification("user", "")


def test_get_notifications_empty_and_requires_user():
    service = NotificationService()
    assert service.get_notifications("nobody") == []
    with pytest.raises(ValueError):
        service.get_notifications("")


def test_mark_as_read_updates_status():
    service = NotificationService()
    sent = service.send_notification("user-1", "hi")

    updated = service.mark_as_read(sent["id"])
    assert updated["read"] is True


def test_mark_as_read_missing_and_requires_id():
    service = NotificationService()
    with pytest.raises(ValueError):
        service.mark_as_read("")
    with pytest.raises(ValueError):
        service.mark_as_read("does-not-exist")


# ---------------------------------------------------------------------------
# AnalyticsService helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("time_range", ["7d", "30d", "90d", "12m", "all"])
def test_all_time_ranges_are_accepted(time_range):
    for fn in (
        get_marketplace_metrics,
        get_creator_analytics,
        get_content_analytics,
        get_revenue_analytics,
    ):
        result = fn(time_range)
        assert result["time_range"] == time_range
        assert result["period_start"] <= result["period_end"]


def test_invalid_time_range_raises_value_error():
    with pytest.raises(ValueError):
        get_marketplace_metrics("42y")


def test_all_range_starts_at_epoch():
    metrics = get_marketplace_metrics("all")
    assert metrics["period_start"].startswith("1970-01-01")


async def test_analytics_service_wraps_functions():
    service = AnalyticsService(db=None)
    assert (await service.get_marketplace_metrics("7d"))["time_range"] == "7d"
    assert (await service.get_creator_analytics("30d"))["time_range"] == "30d"
    assert (await service.get_content_analytics("90d"))["time_range"] == "90d"
    assert (await service.get_revenue_analytics("12m"))["time_range"] == "12m"
