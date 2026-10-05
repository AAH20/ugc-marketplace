"""
Live activity stream tests for ugc-marketplace.

Tests WebSocket activity stream: real-time activity feed, presence,
typing indicators, and live updates.
"""

import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def activity_client():
    """Provide a WebSocket client configured for activity stream."""
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
def sample_activity():
    """Provide a sample activity event."""
    return {
        "id": "activity-001",
        "type": "activity",
        "action": "created",
        "entity_type": "post",
        "entity_id": "post-123",
        "user_id": "user-456",
        "user_name": "Alice",
        "timestamp": "2026-10-03T12:00:00Z",
        "metadata": {"title": "My First Post"},
    }


@pytest.fixture
def sample_activities_batch():
    """Provide a batch of sample activity events."""
    actions = ["created", "updated", "deleted", "liked", "commented"]
    entity_types = ["post", "comment", "review", "order", "message"]

    return [
        {
            "id": f"activity-{i:03d}",
            "type": "activity",
            "action": actions[i % len(actions)],
            "entity_type": entity_types[i % len(entity_types)],
            "entity_id": f"entity-{i}",
            "user_id": f"user-{i}",
            "user_name": f"User {i}",
            "timestamp": "2026-10-03T12:00:00Z",
            "metadata": {},
        }
        for i in range(20)
    ]


@pytest.fixture
def sample_presence():
    """Provide sample presence data."""
    return {
        "type": "presence",
        "user_id": "user-456",
        "status": "online",
        "last_seen": "2026-10-03T12:00:00Z",
    }


@pytest.fixture
def sample_typing_indicator():
    """Provide a sample typing indicator event."""
    return {
        "type": "typing",
        "user_id": "user-789",
        "user_name": "Bob",
        "conversation_id": "conv-001",
        "is_typing": True,
        "timestamp": "2026-10-03T12:00:00Z",
    }


# ---------------------------------------------------------------------------
# Activity Stream Tests
# ---------------------------------------------------------------------------


class TestActivityStream:
    """Test live activity stream over WebSocket."""

    @pytest.mark.asyncio
    async def test_receive_activity(self, activity_client, sample_activity):
        """Test receiving a single activity event."""
        activity_client._ws.recv.return_value = json.dumps(sample_activity)

        message = await activity_client.receive()

        assert message["type"] == "activity"
        assert message["action"] == "created"
        assert message["entity_type"] == "post"
        assert message["user_id"] == "user-456"

    @pytest.mark.asyncio
    async def test_receive_activity_batch(
        self, activity_client, sample_activities_batch
    ):
        """Test receiving a batch of activity events."""
        activity_client._ws.recv.return_value = json.dumps(
            {"type": "activity_batch", "activities": sample_activities_batch}
        )

        message = await activity_client.receive()

        assert message["type"] == "activity_batch"
        assert len(message["activities"]) == 20

    @pytest.mark.asyncio
    async def test_activity_stream_ordering(self, activity_client):
        """Test that activity events are delivered in chronological order."""
        activities = [
            {
                "id": f"activity-{i:03d}",
                "type": "activity",
                "timestamp": f"2026-10-03T12:{i:02d}:00Z",
                "seq": i,
            }
            for i in range(15)
        ]

        async def mock_recv():
            for act in activities:
                yield json.dumps(act)

        recv_gen = mock_recv()
        activity_client._ws.recv = lambda: recv_gen.__anext__()

        received = []
        for _ in range(15):
            msg = await activity_client.receive()
            received.append(msg)

        assert len(received) == 15
        for i, msg in enumerate(received):
            assert msg["seq"] == i

    @pytest.mark.asyncio
    async def test_activity_stream_reconnect(self, activity_client):
        """Test activity stream resumes after reconnection."""
        activity_client._ws.recv.side_effect = [
            json.dumps({"type": "activity", "id": "activity-001"}),
            ConnectionError("Connection lost"),
            json.dumps({"type": "activity", "id": "activity-002"}),
        ]

        msg1 = await activity_client.receive()
        assert msg1["id"] == "activity-001"

        with pytest.raises(ConnectionError):
            await activity_client.receive()

        # Simulate reconnect
        activity_client._connected = True
        msg3 = await activity_client.receive()
        assert msg3["id"] == "activity-002"

    @pytest.mark.asyncio
    async def test_activity_stream_pause_resume(self, activity_client):
        """Test pausing and resuming the activity stream."""
        await activity_client.pause_stream()
        assert activity_client._stream_paused is True

        await activity_client.resume_stream()
        assert activity_client._stream_paused is False

    @pytest.mark.asyncio
    async def test_activity_stream_filter(self, activity_client):
        """Test filtering activity stream by action type."""
        from app.websocket.activity import ActivityFilter

        filter_obj = ActivityFilter(actions=["created", "updated"])

        activities = [
            {"action": "created", "id": "1"},
            {"action": "deleted", "id": "2"},
            {"action": "updated", "id": "3"},
            {"action": "liked", "id": "4"},
        ]

        filtered = filter_obj.apply(activities)

        assert len(filtered) == 2
        assert {a["action"] for a in filtered} == {"created", "updated"}

    @pytest.mark.asyncio
    async def test_activity_stream_by_entity(self, activity_client):
        """Test filtering activity stream by entity type."""
        from app.websocket.activity import ActivityFilter

        filter_obj = ActivityFilter(entity_types=["post", "comment"])

        activities = [
            {"entity_type": "post", "id": "1"},
            {"entity_type": "order", "id": "2"},
            {"entity_type": "comment", "id": "3"},
            {"entity_type": "review", "id": "4"},
        ]

        filtered = filter_obj.apply(activities)

        assert len(filtered) == 2
        assert {a["entity_type"] for a in filtered} == {"post", "comment"}

    @pytest.mark.asyncio
    async def test_activity_stream_by_user(self, activity_client):
        """Test filtering activity stream by user."""
        from app.websocket.activity import ActivityFilter

        filter_obj = ActivityFilter(user_ids=["user-456", "user-789"])

        activities = [
            {"user_id": "user-456", "id": "1"},
            {"user_id": "user-111", "id": "2"},
            {"user_id": "user-789", "id": "3"},
            {"user_id": "user-222", "id": "4"},
        ]

        filtered = filter_obj.apply(activities)

        assert len(filtered) == 2
        assert {a["user_id"] for a in filtered} == {"user-456", "user-789"}

    @pytest.mark.asyncio
    async def test_activity_handler_registration(self, activity_client):
        """Test registering an activity handler."""
        handler = AsyncMock()

        activity_client.on_activity("created", handler)

        assert "created" in activity_client._activity_handlers
        assert handler in activity_client._activity_handlers["created"]

    @pytest.mark.asyncio
    async def test_activity_handler_invocation(
        self, activity_client, sample_activity
    ):
        """Test that registered activity handlers are invoked."""
        handler = AsyncMock()
        activity_client.on_activity("created", handler)

        await activity_client._dispatch_activity(sample_activity)

        handler.assert_called_once_with(sample_activity)

    @pytest.mark.asyncio
    async def test_activity_handler_error_isolation(
        self, activity_client, sample_activity
    ):
        """Test that activity handler errors don't affect other handlers."""
        handler1 = AsyncMock(side_effect=Exception("Handler 1 error"))
        handler2 = AsyncMock()

        activity_client.on_activity("created", handler1)
        activity_client.on_activity("created", handler2)

        await activity_client._dispatch_activity(sample_activity)

        handler1.assert_called_once()
        handler2.assert_called_once()


# ---------------------------------------------------------------------------
# Presence Tests
# ---------------------------------------------------------------------------


class TestPresence:
    """Test user presence over WebSocket."""

    @pytest.mark.asyncio
    async def test_presence_update(self, activity_client, sample_presence):
        """Test receiving a presence update."""
        activity_client._ws.recv.return_value = json.dumps(sample_presence)

        message = await activity_client.receive()

        assert message["type"] == "presence"
        assert message["user_id"] == "user-456"
        assert message["status"] == "online"

    @pytest.mark.asyncio
    async def test_presence_status_change(self, activity_client):
        """Test presence status change events."""
        events = [
            {"type": "presence", "user_id": "user-1", "status": "online"},
            {"type": "presence", "user_id": "user-1", "status": "away"},
            {"type": "presence", "user_id": "user-1", "status": "offline"},
        ]

        async def mock_recv():
            for evt in events:
                yield json.dumps(evt)

        recv_gen = mock_recv()
        activity_client._ws.recv = lambda: recv_gen.__anext__()

        statuses = []
        for _ in range(3):
            msg = await activity_client.receive()
            statuses.append(msg["status"])

        assert statuses == ["online", "away", "offline"]

    @pytest.mark.asyncio
    async def test_get_online_users(self, activity_client):
        """Test retrieving list of online users."""
        activity_client._online_users = {"user-1", "user-2", "user-3"}

        online = activity_client.get_online_users()

        assert len(online) == 3
        assert "user-1" in online

    @pytest.mark.asyncio
    async def test_presence_heartbeat(self, activity_client):
        """Test presence heartbeat to maintain online status."""
        await activity_client.send_presence_heartbeat()

        activity_client._ws.send.assert_called_with(
            json.dumps({"type": "presence", "action": "heartbeat"})
        )

    @pytest.mark.asyncio
    async def test_presence_on_disconnect(self, activity_client):
        """Test that presence is set to offline on disconnect."""
        activity_client._ws.recv.return_value = json.dumps(
            {"type": "presence", "user_id": "user-456", "status": "offline"}
        )

        message = await activity_client.receive()

        assert message["status"] == "offline"


# ---------------------------------------------------------------------------
# Typing Indicator Tests
# ---------------------------------------------------------------------------


class TestTypingIndicator:
    """Test typing indicators over WebSocket."""

    @pytest.mark.asyncio
    async def test_typing_start(self, activity_client, sample_typing_indicator):
        """Test receiving typing start indicator."""
        activity_client._ws.recv.return_value = json.dumps(sample_typing_indicator)

        message = await activity_client.receive()

        assert message["type"] == "typing"
        assert message["is_typing"] is True
        assert message["user_id"] == "user-789"

    @pytest.mark.asyncio
    async def test_typing_stop(self, activity_client):
        """Test receiving typing stop indicator."""
        activity_client._ws.recv.return_value = json.dumps(
            {
                "type": "typing",
                "user_id": "user-789",
                "conversation_id": "conv-001",
                "is_typing": False,
            }
        )

        message = await activity_client.receive()

        assert message["type"] == "typing"
        assert message["is_typing"] is False

    @pytest.mark.asyncio
    async def test_send_typing_indicator(self, activity_client):
        """Test sending a typing indicator."""
        await activity_client.send_typing_indicator("conv-001", is_typing=True)

        activity_client._ws.send.assert_called_with(
            json.dumps(
                {
                    "type": "typing",
                    "conversation_id": "conv-001",
                    "is_typing": True,
                }
            )
        )

    @pytest.mark.asyncio
    async def test_typing_indicator_timeout(self, activity_client):
        """Test that typing indicator auto-clears after timeout."""
        activity_client._typing_indicators = {"user-789": asyncio.get_event_loop().time()}

        # Simulate timeout
        await asyncio.sleep(0.1)
        activity_client._typing_indicators.clear()

        assert len(activity_client._typing_indicators) == 0

    @pytest.mark.asyncio
    async def test_typing_indicator_dedup(self, activity_client):
        """Test that duplicate typing indicators are deduplicated."""
        activity_client._typing_indicators = {}

        await activity_client.send_typing_indicator("conv-001", is_typing=True)
        await activity_client.send_typing_indicator("conv-001", is_typing=True)

        # Should only have one entry
        assert len(activity_client._typing_indicators) == 1


# ---------------------------------------------------------------------------
# Live Update Tests
# ---------------------------------------------------------------------------


class TestLiveUpdates:
    """Test live update subscriptions and delivery."""

    @pytest.mark.asyncio
    async def test_subscribe_to_entity(self, activity_client):
        """Test subscribing to updates for a specific entity."""
        await activity_client.subscribe_to_entity("post", "post-123")

        activity_client._ws.send.assert_called_with(
            json.dumps(
                {"type": "subscribe", "entity_type": "post", "entity_id": "post-123"}
            )
        )

    @pytest.mark.asyncio
    async def test_unsubscribe_from_entity(self, activity_client):
        """Test unsubscribing from entity updates."""
        await activity_client.unsubscribe_from_entity("post", "post-123")

        activity_client._ws.send.assert_called_with(
            json.dumps(
                {
                    "type": "unsubscribe",
                    "entity_type": "post",
                    "entity_id": "post-123",
                }
            )
        )

    @pytest.mark.asyncio
    async def test_live_update_delivery(self, activity_client):
        """Test receiving a live update for a subscribed entity."""
        update = {
            "type": "live_update",
            "entity_type": "post",
            "entity_id": "post-123",
            "changes": {"title": "Updated Title"},
            "timestamp": "2026-10-03T12:00:00Z",
        }

        activity_client._ws.recv.return_value = json.dumps(update)

        message = await activity_client.receive()

        assert message["type"] == "live_update"
        assert message["entity_id"] == "post-123"
        assert message["changes"]["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_live_update_handler(self, activity_client):
        """Test registering a handler for live updates."""
        handler = AsyncMock()

        activity_client.on_live_update("post", "post-123", handler)

        assert ("post", "post-123") in activity_client._live_update_handlers

    @pytest.mark.asyncio
    async def test_multiple_entity_subscriptions(self, activity_client):
        """Test subscribing to multiple entities."""
        entities = [("post", "post-1"), ("post", "post-2"), ("comment", "comment-1")]

        for entity_type, entity_id in entities:
            await activity_client.subscribe_to_entity(entity_type, entity_id)

        assert len(activity_client._entity_subscriptions) == 3

    @pytest.mark.asyncio
    async def test_live_update_batch(self, activity_client):
        """Test receiving batched live updates."""
        updates = [
            {
                "type": "live_update",
                "entity_type": "post",
                "entity_id": f"post-{i}",
                "changes": {"views": i * 10},
            }
            for i in range(5)
        ]

        activity_client._ws.recv.return_value = json.dumps(
            {"type": "live_update_batch", "updates": updates}
        )

        message = await activity_client.receive()

        assert message["type"] == "live_update_batch"
        assert len(message["updates"]) == 5
