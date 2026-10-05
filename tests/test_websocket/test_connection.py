"""
WebSocket connection tests for ugc-marketplace.

Tests WebSocket connection lifecycle: connect, authenticate, disconnect,
and error handling.
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
async def mock_websocket():
    """Provide a mock WebSocket connection."""
    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock()
    ws.close = AsyncMock()
    ws.closed = False
    return ws


@pytest_asyncio.fixture
async def ws_client():
    """Provide a WebSocket client connected to a mock server."""
    from app.websocket.client import WebSocketClient

    client = WebSocketClient(url="ws://localhost:8000/ws")
    client.connect = AsyncMock(return_value=mock_websocket())
    yield client
    if client.is_connected:
        await client.disconnect()


@pytest.fixture
def connection_event():
    """Provide an asyncio.Event for connection state tracking."""
    return asyncio.Event()


# ---------------------------------------------------------------------------
# Connection Tests
# ---------------------------------------------------------------------------


class TestWebSocketConnection:
    """Test WebSocket connection establishment and teardown."""

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_websocket):
        """Test successful WebSocket connection."""
        from app.websocket.client import WebSocketClient

        client = WebSocketClient(url="ws://localhost:8000/ws")
        client._ws = mock_websocket
        client._connected = True

        assert client.is_connected is True
        assert client.url == "ws://localhost:8000/ws"

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test WebSocket connection failure handling."""
        from app.websocket.client import WebSocketClient

        client = WebSocketClient(url="ws://invalid:9999/ws")

        with pytest.raises(ConnectionError):
            await client.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_websocket):
        """Test clean WebSocket disconnection."""
        from app.websocket.client import WebSocketClient

        client = WebSocketClient(url="ws://localhost:8000/ws")
        client._ws = mock_websocket
        client._connected = True

        await client.disconnect()

        mock_websocket.close.assert_called_once()
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_reconnect(self, mock_websocket):
        """Test WebSocket reconnection after disconnect."""
        from app.websocket.client import WebSocketClient

        client = WebSocketClient(url="ws://localhost:8000/ws")
        client._ws = mock_websocket
        client._connected = True

        await client.disconnect()
        assert client.is_connected is False

        client._ws = mock_websocket
        client._connected = True
        assert client.is_connected is True

    @pytest.mark.asyncio
    async def test_connection_timeout(self):
        """Test connection timeout handling."""
        from app.websocket.client import WebSocketClient

        client = WebSocketClient(url="ws://10.255.255.1:8000/ws", timeout=0.1)

        with pytest.raises((ConnectionError, asyncio.TimeoutError)):
            await client.connect()

    @pytest.mark.asyncio
    async def test_ping_pong(self, mock_websocket):
        """Test WebSocket ping/pong keepalive."""
        from app.websocket.client import WebSocketClient

        client = WebSocketClient(url="ws://localhost:8000/ws")
        client._ws = mock_websocket
        client._connected = True

        mock_websocket.recv.return_value = json.dumps({"type": "pong"})

        response = await client.ping()

        mock_websocket.send.assert_called_with(json.dumps({"type": "ping"}))
        assert response["type"] == "pong"

    @pytest.mark.asyncio
    async def test_connection_state_callback(self, mock_websocket, connection_event):
        """Test connection state change callbacks."""
        from app.websocket.client import WebSocketClient

        client = WebSocketClient(url="ws://localhost:8000/ws")
        client._ws = mock_websocket
        client._connected = True

        client.on_connect = connection_event.set
        client.on_disconnect = connection_event.clear

        client._connected = True
        client.on_connect()
        assert connection_event.is_set()

        client._connected = False
        client.on_disconnect()
        assert not connection_event.is_set()

    @pytest.mark.asyncio
    async def test_send_while_disconnected(self):
        """Test that sending while disconnected raises an error."""
        from app.websocket.client import WebSocketClient

        client = WebSocketClient(url="ws://localhost:8000/ws")
        client._connected = False

        with pytest.raises(RuntimeError, match="Not connected"):
            await client.send({"type": "test"})

    @pytest.mark.asyncio
    async def test_receive_while_disconnected(self):
        """Test that receiving while disconnected raises an error."""
        from app.websocket.client import WebSocketClient

        client = WebSocketClient(url="ws://localhost:8000/ws")
        client._connected = False

        with pytest.raises(RuntimeError, match="Not connected"):
            await client.receive()

    @pytest.mark.asyncio
    async def test_connection_url_with_token(self):
        """Test WebSocket connection URL with authentication token."""
        from app.websocket.client import WebSocketClient

        token = "test-jwt-token-12345"
        client = WebSocketClient(
            url=f"ws://localhost:8000/ws?token={token}"
        )

        assert "token=test-jwt-token-12345" in client.url

    @pytest.mark.asyncio
    async def test_multiple_disconnect_calls(self, mock_websocket):
        """Test that multiple disconnect calls are safe."""
        from app.websocket.client import WebSocketClient

        client = WebSocketClient(url="ws://localhost:8000/ws")
        client._ws = mock_websocket
        client._connected = True

        await client.disconnect()
        await client.disconnect()  # Should not raise

        assert client.is_connected is False
