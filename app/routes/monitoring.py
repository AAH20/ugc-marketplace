"""Campaign monitoring REST API routes."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_metric import CampaignMetric
from app.models.alert import Alert, AlertType, AlertSeverity
from app.models.recommendation import Recommendation, RecommendationCategory
from app.services.metrics import MetricsService
from app.services.alerting import AlertingService
from app.services.recommendations import RecommendationEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["monitoring"])

# Service singletons
metrics_svc = MetricsService()
alerting_svc = AlertingService()
rec_engine = RecommendationEngine()


# ── Pydantic Schemas ───────────────────────────────────────────────────

class MetricIngestRequest(BaseModel):
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    revenue: float = 0.0
    timestamp: datetime | None = None


class MetricResponse(BaseModel):
    id: int
    campaign_id: int
    timestamp: datetime
    impressions: int
    clicks: int
    conversions: int
    spend: float
    revenue: float

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    id: int
    campaign_id: int
    alert_type: str
    severity: str
    message: str
    metric_value: float
    threshold: float
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RecommendationResponse(BaseModel):
    id: int
    campaign_id: int
    category: str
    priority: int
    title: str
    description: str
    expected_impact: float
    is_applied: bool

    class Config:
        from_attributes = True


class DashboardSummary(BaseModel):
    total_campaigns: int
    active_campaigns: int
    total_spend: float
    total_revenue: float
    avg_roas: float
    alerts_count: int


# ── Helper: compute campaign summary ──────────────────────────────────

def _campaign_summary(db: Session, campaign: Campaign) -> dict:
    row = db.query(
        func.sum(CampaignMetric.impressions),
        func.sum(CampaignMetric.clicks),
        func.sum(CampaignMetric.conversions),
        func.sum(CampaignMetric.spend),
        func.sum(CampaignMetric.revenue),
    ).filter(CampaignMetric.campaign_id == campaign.id).one_or_none()

    if row and row[0] is not None:
        agg = metrics_svc.aggregate([{
            "impressions": row[0] or 0,
            "clicks": row[1] or 0,
            "conversions": row[2] or 0,
            "spend": float(row[3] or 0),
            "revenue": float(row[4] or 0),
        }])
    else:
        agg = {
            "total_impressions": 0, "total_clicks": 0, "total_conversions": 0,
            "total_spend": 0.0, "total_revenue": 0.0,
            "ctr": 0.0, "roas": 0.0, "cpc": 0.0, "cpm": 0.0, "conversion_rate": 0.0,
        }
    return {
        "id": campaign.id,
        "name": campaign.name,
        "status": campaign.status.value if isinstance(campaign.status, CampaignStatus) else campaign.status,
        "budget": float(campaign.budget),
        "spent": float(campaign.spent),
        "target_roas": float(campaign.target_roas),
        "target_ctr": float(campaign.target_ctr),
        **agg,
    }


# ── Helper: detect anomalies and persist alerts ───────────────────────

def _detect_and_alert(db: Session, campaign: Campaign, latest: CampaignMetric) -> list[Alert]:
    history = (
        db.query(CampaignMetric)
        .filter(
            CampaignMetric.campaign_id == campaign.id,
            CampaignMetric.id != latest.id,
        )
        .order_by(CampaignMetric.timestamp.desc())
        .limit(24)
        .all()
    )

    if not history:
        return []

    avg_spend = sum(float(m.spend) for m in history) / len(history)
    avg_ctr = metrics_svc.compute_ctr(
        sum(m.clicks for m in history), sum(m.impressions for m in history)
    )
    current_ctr = metrics_svc.compute_ctr(latest.clicks, latest.impressions)
    current_roas = metrics_svc.compute_roas(float(latest.revenue), float(latest.spend))

    alerts_data = alerting_svc.detect_all(
        campaign_id=campaign.id,
        current_spend=float(latest.spend),
        avg_spend=avg_spend,
        current_ctr=current_ctr,
        baseline_ctr=avg_ctr,
        current_roas=current_roas,
        target_roas=float(campaign.target_roas),
    )

    alerts = []
    for ad in alerts_data:
        alert = Alert(
            campaign_id=ad["campaign_id"],
            alert_type=ad["alert_type"],
            severity=ad["severity"],
            message=ad["message"],
            metric_value=ad["metric_value"],
            threshold=ad["threshold"],
        )
        db.add(alert)
        alerts.append(alert)

    if alerts:
        db.commit()
        for alert in alerts:
            db.refresh(alert)
    return alerts


# ── Helper: generate and persist recommendations ──────────────────────

def _generate_recommendations(db: Session, campaign: Campaign) -> list[Recommendation]:
    metrics = (
        db.query(CampaignMetric)
        .filter(CampaignMetric.campaign_id == campaign.id)
        .order_by(CampaignMetric.timestamp.desc())
        .limit(24)
        .all()
    )
    if not metrics:
        return []

    agg = metrics_svc.aggregate([{
        "impressions": m.impressions,
        "clicks": m.clicks,
        "conversions": m.conversions,
        "spend": float(m.spend),
        "revenue": float(m.revenue),
    } for m in metrics])

    # Determine spend trend
    if len(metrics) >= 2:
        recent = sum(float(m.spend) for m in metrics[:6])
        older = sum(float(m.spend) for m in metrics[6:12]) if len(metrics) >= 12 else recent
        if older > 0 and recent / older > 1.5:
            spend_trend = "spike"
        elif older > 0 and recent / older < 0.5:
            spend_trend = "drop"
        else:
            spend_trend = "stable"
    else:
        spend_trend = "stable"

    recs_data = rec_engine.generate(
        campaign_id=campaign.id,
        current_roas=agg["roas"],
        target_roas=float(campaign.target_roas),
        current_ctr=agg["ctr"],
        target_ctr=float(campaign.target_ctr),
        spend_trend=spend_trend,
    )

    recs = []
    for rd in recs_data:
        rec = Recommendation(
            campaign_id=rd["campaign_id"],
            category=rd["category"],
            priority=rd["priority"],
            title=rd["title"],
            description=rd["description"],
            expected_impact=rd["expected_impact"],
        )
        db.add(rec)
        recs.append(rec)

    if recs:
        db.commit()
        for rec in recs:
            db.refresh(rec)
    return recs


# ── REST Endpoints ────────────────────────────────────────────────────

@router.get("/campaigns", response_model=list[dict])
def list_campaigns(db: Session = Depends(get_db)):
    campaigns = db.query(Campaign).order_by(Campaign.id).all()
    return [_campaign_summary(db, c) for c in campaigns]


@router.get("/campaigns/{campaign_id}", response_model=dict)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign_summary(db, campaign)


@router.get("/campaigns/{campaign_id}/metrics", response_model=list[MetricResponse])
def get_campaign_metrics(
    campaign_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return (
        db.query(CampaignMetric)
        .filter(CampaignMetric.campaign_id == campaign_id)
        .order_by(CampaignMetric.timestamp.desc())
        .limit(limit)
        .all()
    )


@router.post("/campaigns/{campaign_id}/metrics", response_model=MetricResponse, status_code=201)
def ingest_metric(campaign_id: int, req: MetricIngestRequest, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    metric = CampaignMetric(
        campaign_id=campaign_id,
        impressions=req.impressions,
        clicks=req.clicks,
        conversions=req.conversions,
        spend=req.spend,
        revenue=req.revenue,
        timestamp=req.timestamp or datetime.now(timezone.utc),
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)

    # Update campaign spent
    campaign.spent = float(campaign.spent) + req.spend
    db.commit()

    # Detect anomalies
    _detect_and_alert(db, campaign, metric)

    # Generate recommendations
    _generate_recommendations(db, campaign)

    return metric


@router.get("/campaigns/{campaign_id}/alerts", response_model=list[AlertResponse])
def get_campaign_alerts(
    campaign_id: int,
    include_resolved: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    query = db.query(Alert).filter(Alert.campaign_id == campaign_id)
    if not include_resolved:
        query = query.filter(Alert.is_resolved == False)
    return query.order_by(Alert.created_at.desc()).all()


@router.get("/campaigns/{campaign_id}/recommendations", response_model=list[RecommendationResponse])
def get_campaign_recommendations(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return (
        db.query(Recommendation)
        .filter(Recommendation.campaign_id == campaign_id)
        .order_by(Recommendation.priority)
        .all()
    )


@router.post("/alerts/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    total_campaigns = db.query(func.count(Campaign.id)).scalar() or 0
    active_campaigns = (
        db.query(func.count(Campaign.id))
        .filter(Campaign.status == CampaignStatus.ACTIVE)
        .scalar()
        or 0
    )

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

    return DashboardSummary(
        total_campaigns=total_campaigns,
        active_campaigns=active_campaigns,
        total_spend=round(total_spend, 2),
        total_revenue=round(total_revenue, 2),
        avg_roas=round(avg_roas, 4),
        alerts_count=alerts_count,
    )
