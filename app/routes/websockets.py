"""WebSocket endpoints for real-time campaign monitoring."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.campaign import Campaign
from app.models.campaign_metric import CampaignMetric
from app.models.alert import Alert
from app.services.metrics import MetricsService

logger = logging.getLogger(__name__)

ws_router = APIRouter()

metrics_svc = MetricsService()


class ConnectionManager:
    """Manage WebSocket connections per channel."""

    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, channel: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(channel, []).append(ws)

    def disconnect(self, channel: str, ws: WebSocket):
        if channel in self.active:
            self.active[channel] = [w for w in self.active[channel] if w is not ws]

    async def broadcast(self, channel: str, message: dict):
        dead = []
        for ws in self.active.get(channel, []):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(channel, ws)


manager = ConnectionManager()


def _get_db():
    yield from get_db()


@ws_router.websocket("/ws/campaigns/{campaign_id}/metrics")
async def ws_campaign_metrics(
    websocket: WebSocket, campaign_id: int, db: Session = Depends(get_db)
):
    """Stream live metrics for a campaign."""
    channel = f"campaign_{campaign_id}_metrics"
    await manager.connect(channel, websocket)
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            await websocket.close(code=4004, reason="Campaign not found")
            return

        # Send initial metrics
        metrics = (
            db.query(CampaignMetric)
            .filter(CampaignMetric.campaign_id == campaign_id)
            .order_by(CampaignMetric.timestamp.desc())
            .limit(50)
            .all()
        )
        await websocket.send_json(
            {
                "type": "initial_metrics",
                "metrics": [
                    {
                        "id": m.id,
                        "impressions": m.impressions,
                        "clicks": m.clicks,
                        "conversions": m.conversions,
                        "spend": float(m.spend),
                        "revenue": float(m.revenue),
                        "timestamp": m.timestamp.isoformat(),
                    }
                    for m in reversed(metrics)
                ],
            }
        )

        # Keep connection alive and handle client messages
        while True:
            try:
                data = await websocket.receive_json()
                action = data.get("action", "")
                if action == "ping":
                    await websocket.send_json({"type": "pong"})
                elif action == "get_metrics":
                    metrics = (
                        db.query(CampaignMetric)
                        .filter(CampaignMetric.campaign_id == campaign_id)
                        .order_by(CampaignMetric.timestamp.desc())
                        .limit(50)
                        .all()
                    )
                    await websocket.send_json(
                        {
                            "type": "metrics",
                            "metrics": [
                                {
                                    "id": m.id,
                                    "impressions": m.impressions,
                                    "clicks": m.clicks,
                                    "conversions": m.conversions,
                                    "spend": float(m.spend),
                                    "revenue": float(m.revenue),
                                    "timestamp": m.timestamp.isoformat(),
                                }
                                for m in reversed(metrics)
                            ],
                        }
                    )
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"WebSocket error: {e}")
                break
    finally:
        manager.disconnect(channel, websocket)
        db.close()


@ws_router.websocket("/ws/campaigns/{campaign_id}/alerts")
async def ws_campaign_alerts(websocket: WebSocket, campaign_id: int, db: Session = Depends(get_db)):
    """Stream alerts for a campaign."""
    channel = f"campaign_{campaign_id}_alerts"
    await manager.connect(channel, websocket)
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            await websocket.close(code=4004, reason="Campaign not found")
            return

        alerts = (
            db.query(Alert)
            .filter(Alert.campaign_id == campaign_id)
            .order_by(Alert.created_at.desc())
            .limit(50)
            .all()
        )
        await websocket.send_json(
            {
                "type": "initial_alerts",
                "alerts": [
                    {
                        "id": a.id,
                        "alert_type": a.alert_type.value,
                        "severity": a.severity.value,
                        "message": a.message,
                        "is_resolved": a.is_resolved,
                        "created_at": a.created_at.isoformat(),
                    }
                    for a in reversed(alerts)
                ],
            }
        )

        while True:
            try:
                data = await websocket.receive_json()
                action = data.get("action", "")
                if action == "ping":
                    await websocket.send_json({"type": "pong"})
                elif action == "get_alerts":
                    alerts = (
                        db.query(Alert)
                        .filter(Alert.campaign_id == campaign_id)
                        .order_by(Alert.created_at.desc())
                        .limit(50)
                        .all()
                    )
                    await websocket.send_json(
                        {
                            "type": "alerts",
                            "alerts": [
                                {
                                    "id": a.id,
                                    "alert_type": a.alert_type.value,
                                    "severity": a.severity.value,
                                    "message": a.message,
                                    "is_resolved": a.is_resolved,
                                    "created_at": a.created_at.isoformat(),
                                }
                                for a in reversed(alerts)
                            ],
                        }
                    )
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"WebSocket error: {e}")
                break
    finally:
        manager.disconnect(channel, websocket)
        db.close()


@ws_router.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket, db: Session = Depends(get_db)):
    """Stream dashboard overview."""
    channel = "dashboard"
    await manager.connect(channel, websocket)
    try:
        from sqlalchemy import func

        total_campaigns = db.query(func.count(Campaign.id)).scalar() or 0
        row = db.query(
            func.sum(CampaignMetric.spend),
            func.sum(CampaignMetric.revenue),
        ).one()
        total_spend = float(row[0] or 0)
        total_revenue = float(row[1] or 0)
        avg_roas = metrics_svc.compute_roas(total_revenue, total_spend)

        alerts_count = (
            db.query(func.count(Alert.id)).filter(Alert.is_resolved == False).scalar() or 0
        )

        await websocket.send_json(
            {
                "type": "summary",
                "summary": {
                    "total_campaigns": total_campaigns,
                    "total_spend": round(total_spend, 2),
                    "total_revenue": round(total_revenue, 2),
                    "avg_roas": round(avg_roas, 4),
                    "alerts_count": alerts_count,
                },
            }
        )

        while True:
            try:
                data = await websocket.receive_json()
                action = data.get("action", "")
                if action == "ping":
                    await websocket.send_json({"type": "pong"})
                elif action == "get_summary":
                    total_campaigns = db.query(func.count(Campaign.id)).scalar() or 0
                    row = db.query(
                        func.sum(CampaignMetric.spend),
                        func.sum(CampaignMetric.revenue),
                    ).one()
                    total_spend = float(row[0] or 0)
                    total_revenue = float(row[1] or 0)
                    avg_roas = metrics_svc.compute_roas(total_revenue, total_spend)

                    alerts_count = (
                        db.query(func.count(Alert.id)).filter(Alert.is_resolved == False).scalar()
                        or 0
                    )

                    await websocket.send_json(
                        {
                            "type": "summary",
                            "summary": {
                                "total_campaigns": total_campaigns,
                                "total_spend": round(total_spend, 2),
                                "total_revenue": round(total_revenue, 2),
                                "avg_roas": round(avg_roas, 4),
                                "alerts_count": alerts_count,
                            },
                        }
                    )
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"WebSocket error: {e}")
                break
    finally:
        manager.disconnect(channel, websocket)
        db.close()
