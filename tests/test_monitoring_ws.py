"""Tests for the standalone monitoring module (WebSocket + REST)."""
import pytest
from fastapi.testclient import TestClient

from monitoring import app, manager


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    manager.active.clear()


def test_rest_metrics_snapshot(client):
    """REST endpoint returns a metrics snapshot for a campaign."""
    resp = client.get("/api/v1/monitoring/metrics", params={"campaign_id": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["campaign_id"] == 1
    assert "impressions" in data
    assert "clicks" in data
    assert "conversions" in data


def test_rest_metrics_requires_campaign_id(client):
    """REST endpoint returns 422 when campaign_id is missing."""
    resp = client.get("/api/v1/monitoring/metrics")
    assert resp.status_code == 422


def test_websocket_streams_metrics(client):
    """WebSocket streams mock metrics for a campaign."""
    with client.websocket_connect(
        "/api/v1/monitoring/ws", params={"campaign_id": 1}
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "metrics"
        assert msg["campaign_id"] == 1
        assert "impressions" in msg
        assert "clicks" in msg
        assert "conversions" in msg


def test_websocket_requires_campaign_id(client):
    """WebSocket rejects connection without campaign_id."""
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/monitoring/ws"):
            pass


def test_connection_manager_tracks_connections():
    """ConnectionManager tracks and removes connections."""
    class FakeWS:
        def __init__(self):
            self.accepted = False
        async def accept(self):
            self.accepted = True

    ws = FakeWS()
    import asyncio
    asyncio.run(manager.connect("ch1", ws))
    assert ws in manager.active["ch1"]
    manager.disconnect("ch1", ws)
    assert ws not in manager.active.get("ch1", [])
