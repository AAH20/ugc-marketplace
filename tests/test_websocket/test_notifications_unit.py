"""
Real-time notification tests for ugc-marketplace.

Tests WebSocket notification delivery, subscription management,
and notification filtering.
"""

import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def notification_client():
    """Provide a WebSocket client configured for notifications."""
    from app.websocket.client import WebSocketClient

    client = WebSocketClient(url="ws://localhost:8000/ws")
    client._ws = AsyncMock()
    client._ws.send = AsyncMock()
    client._ws.recv = AsyncMock()
    client._connected = True
    yield client
    if client.is_connected:
        await client.disconnect()


@pytest.fixture
def sample_notification():
    """Provide a sample notification payload."""
    return {
        "id": "notif-001",
        "type": "notification",
        "category": "order",
        "title": "New Order",
        "message": "You have a new order #12345",
        "data": {"order_id": "12345", "amount": 99.99},
        "timestamp": "2026-10-03T12:00:00Z",
        "read": False,
    }


@pytest.fixture
def sample_notifications_batch():
    """Provide a batch of sample notifications."""
    return [
        {
            "id": f"notif-{i:03d}",
            "type": "notification",
            "category": cat,
            "title": f"Notification {i}",
            "message": f"Message {i}",
            "data": {},
            "timestamp": "2026-10-03T12:00:00Z",
            "read": False,
        }
        for i, cat in enumerate(["order", "message", "system", "payment", "review"])
    ]


# ---------------------------------------------------------------------------
# Notification Delivery Tests
# ---------------------------------------------------------------------------


class TestNotificationDelivery:
    """Test real-time notification delivery over WebSocket."""

    @pytest.mark.asyncio
    async def test_receive_notification(self, notification_client, sample_notification):
        """Test receiving a single notification."""
        notification_client._ws.recv.return_value = json.dumps(sample_notification)

        message = await notification_client.receive()

        assert message["type"] == "notification"
        assert message["category"] == "order"
        assert message["title"] == "New Order"
        assert message["data"]["order_id"] == "12345"

    @pytest.mark.asyncio
    async def test_receive_notification_batch(
        self, notification_client, sample_notifications_batch
    ):
        """Test receiving a batch of notifications."""
        notification_client._ws.recv.return_value = json.dumps(
            {"type": "notification_batch", "notifications": sample_notifications_batch}
        )

        message = await notification_client.receive()

        assert message["type"] == "notification_batch"
        assert len(message["notifications"]) == 5

    @pytest.mark.asyncio
    async def test_notification_order(self, notification_client):
        """Test that notifications are delivered in order."""
        notifications = [
            {"id": f"notif-{i:03d}", "seq": i, "type": "notification"}
            for i in range(10)
        ]

        async def mock_recv():
            for notif in notifications:
                yield json.dumps(notif)

        recv_gen = mock_recv()
        notification_client._ws.recv = lambda: recv_gen.__anext__()

        received = []
        for _ in range(10):
            msg = await notification_client.receive()
            received.append(msg)

        assert len(received) == 10
        for i, msg in enumerate(received):
            assert msg["seq"] == i

    @pytest.mark.asyncio
    async def test_notification_with_invalid_json(self, notification_client):
        """Test handling of invalid JSON in notification."""
        notification_client._ws.recv.return_value = "not valid json{{{{"

        with pytest.raises(json.JSONDecodeError):
            await notification_client.receive()

    @pytest.mark.asyncio
    async def test_notification_missing_fields(self, notification_client):
        """Test handling of notification with missing required fields."""
        incomplete = {"type": "notification"}  # missing id, title, etc.

        notification_client._ws.recv.return_value = json.dumps(incomplete)

        message = await notification_client.receive()

        assert message["type"] == "notification"
        assert "id" not in message

    @pytest.mark.asyncio
    async def test_notification_ack(self, notification_client, sample_notification):
        """Test acknowledging a notification."""
        await notification_client.acknowledge(sample_notification["id"])

        notification_client._ws.send.assert_called_with(
            json.dumps({"type": "ack", "notification_id": "notif-001"})
        )

    @pytest.mark.asyncio
    async def test_notification_read_receipt(self, notification_client):
        """Test sending read receipt for multiple notifications."""
        ids = ["notif-001", "notif-002", "notif-003"]
        await notification_client.mark_as_read(ids)

        notification_client._ws.send.assert_called_with(
            json.dumps({"type": "read_receipt", "notification_ids": ids})
        )


# ---------------------------------------------------------------------------
# Notification Subscription Tests
# ---------------------------------------------------------------------------


class TestNotificationSubscription:
    """Test notification subscription management."""

    @pytest.mark.asyncio
    async def test_subscribe_to_category(self, notification_client):
        """Test subscribing to a notification category."""
        await notification_client.subscribe("order")

        notification_client._ws.send.assert_called_with(
            json.dumps({"type": "subscribe", "category": "order"})
        )

    @pytest.mark.asyncio
    async def test_unsubscribe_from_category(self, notification_client):
        """Test unsubscribing from a notification category."""
        await notification_client.unsubscribe("order")

        notification_client._ws.send.assert_called_with(
            json.dumps({"type": "unsubscribe", "category": "order"})
        )

    @pytest.mark.asyncio
    async def test_subscribe_to_multiple_categories(self, notification_client):
        """Test subscribing to multiple categories at once."""
        categories = ["order", "message", "payment"]
        await notification_client.subscribe(categories)

        notification_client._ws.send.assert_called_with(
            json.dumps({"type": "subscribe", "categories": categories})
        )

    @pytest.mark.asyncio
    async def test_subscribe_to_all(self, notification_client):
        """Test subscribing to all notification categories."""
        await notification_client.subscribe_all()

        notification_client._ws.send.assert_called_with(
            json.dumps({"type": "subscribe", "category": "*"})
        )

    @pytest.mark.asyncio
    async def test_unsubscribe_from_all(self, notification_client):
        """Test unsubscribing from all notification categories."""
        await notification_client.unsubscribe_all()

        notification_client._ws.send.assert_called_with(
            json.dumps({"type": "unsubscribe", "category": "*"})
        )

    @pytest.mark.asyncio
    async def test_subscribe_invalid_category(self, notification_client):
        """Test subscribing to an invalid category."""
        with pytest.raises(ValueError, match="Invalid category"):
            await notification_client.subscribe("invalid_category")

    @pytest.mark.asyncio
    async def test_get_subscriptions(self, notification_client):
        """Test retrieving current subscriptions."""
        notification_client._subscriptions = {"order", "message"}

        subs = notification_client.get_subscriptions()

        assert "order" in subs
        assert "message" in subs


# ---------------------------------------------------------------------------
# Notification Filtering Tests
# ---------------------------------------------------------------------------


class TestNotificationFiltering:
    """Test notification filtering and routing."""

    @pytest.mark.asyncio
    async def test_filter_by_category(self, sample_notifications_batch):
        """Test filtering notifications by category."""
        from app.websocket.notifications import NotificationFilter

        filter_obj = NotificationFilter(categories=["order", "payment"])
        filtered = filter_obj.apply(sample_notifications_batch)

        assert len(filtered) == 2
        categories = {n["category"] for n in filtered}
        assert categories == {"order", "payment"}

    @pytest.mark.asyncio
    async def test_filter_unread_only(self, sample_notifications_batch):
        """Test filtering for unread notifications only."""
        from app.websocket.notifications import NotificationFilter

        sample_notifications_batch[0]["read"] = True
        sample_notifications_batch[2]["read"] = True

        filter_obj = NotificationFilter(unread_only=True)
        filtered = filter_obj.apply(sample_notifications_batch)

        assert len(filtered) == 3
        assert all(not n["read"] for n in filtered)

    @pytest.mark.asyncio
    async def test_filter_by_date_range(self, sample_notifications_batch):
        """Test filtering notifications by date range."""
        from app.websocket.notifications import NotificationFilter

        sample_notifications_batch[0]["timestamp"] = "2026-10-01T12:00:00Z"
        sample_notifications_batch[1]["timestamp"] = "2026-10-02T12:00:00Z"
        sample_notifications_batch[2]["timestamp"] = "2026-10-03T12:00:00Z"

        filter_obj = NotificationFilter(
            start_date="2026-10-02T00:00:00Z", end_date="2026-10-03T23:59:59Z"
        )
        filtered = filter_obj.apply(sample_notifications_batch)

        assert len(filtered) == 2

    @pytest.mark.asyncio
    async def test_notification_handler_registration(self, notification_client):
        """Test registering a notification handler."""
        handler = AsyncMock()

        notification_client.on_notification("order", handler)

        assert "order" in notification_client._handlers
        assert handler in notification_client._handlers["order"]

    @pytest.mark.asyncio
    async def test_notification_handler_invocation(
        self, notification_client, sample_notification
    ):
        """Test that registered handlers are invoked on notification."""
        handler = AsyncMock()
        notification_client.on_notification("order", handler)

        await notification_client._dispatch(sample_notification)

        handler.assert_called_once_with(sample_notification)

    @pytest.mark.asyncio
    async def test_notification_handler_error_isolation(
        self, notification_client, sample_notification
    ):
        """Test that handler errors don't affect other handlers."""
        handler1 = AsyncMock(side_effect=Exception("Handler 1 error"))
        handler2 = AsyncMock()

        notification_client.on_notification("order", handler1)
        notification_client.on_notification("order", handler2)

        await notification_client._dispatch(sample_notification)

        handler1.assert_called_once()
        handler2.assert_called_once()
