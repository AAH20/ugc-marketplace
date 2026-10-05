"""Real-time campaign monitoring: WebSocket streaming + metrics snapshot."""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone

from fastapi import APIRouter, FastAPI, Query, WebSocket, WebSocketDisconnect

app = FastAPI(title="Campaign Monitoring")
router = APIRouter()

# ── Connection manager ────────────────────────────────────────────────

class ConnectionManager:
    """Track active WebSocket connections by channel."""

    def __init__(self) -> None:
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, channel: str, ws: WebSocket) -> None:
        await ws.accept()
        self.active.setdefault(channel, []).append(ws)

    def disconnect(self, channel: str, ws: WebSocket) -> None:
        if channel in self.active:
            self.active[channel] = [w for w in self.active[channel] if w is not ws]
            if not self.active[channel]:
                del self.active[channel]

    async def broadcast(self, channel: str, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self.active.get(channel, []):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(channel, ws)


manager = ConnectionManager()

# ── Mock metrics store ────────────────────────────────────────────────

_metrics: dict[int, dict] = {}


def _next_snapshot(campaign_id: int) -> dict:
    """Advance and return the next mock metric snapshot for a campaign."""
    prev = _metrics.get(campaign_id, {
        "impressions": 1000, "clicks": 20, "conversions": 2,
    })
    snap = {
        "campaign_id": campaign_id,
        "impressions": prev["impressions"] + random.randint(50, 200),
        "clicks": prev["clicks"] + random.randint(1, 10),
        "conversions": prev["conversions"] + random.randint(0, 3),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _metrics[campaign_id] = snap
    return snap


# ── REST endpoint ─────────────────────────────────────────────────────

@router.get("/api/v1/monitoring/metrics")
def get_metrics(campaign_id: int = Query(...)) -> dict:
    """Return the current metrics snapshot for a campaign."""
    return _next_snapshot(campaign_id)


# ── WebSocket endpoint ────────────────────────────────────────────────

@router.websocket("/api/v1/monitoring/ws")
async def ws_metrics(websocket: WebSocket, campaign_id: int = Query(...)) -> None:
    """Stream mock metrics for a campaign every 2 seconds."""
    channel = f"campaign_{campaign_id}"
    await manager.connect(channel, websocket)
    try:
        while True:
            await websocket.send_json({"type": "metrics", **_next_snapshot(campaign_id)})
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(channel, websocket)


app.include_router(router)
