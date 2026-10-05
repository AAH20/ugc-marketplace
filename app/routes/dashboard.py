"""Dashboard API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.broker import Broker
from app.models.commission_tracking import CommissionTracking, CommissionStatus
from app.models.broker_payout import BrokerPayout, PayoutStatus
from app.models.broker_partner import BrokerPartner
from app.models.campaign import Campaign, CampaignStatus
from app.models.alert import Alert, AlertSeverity

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Get dashboard summary statistics."""
    total_brokers = db.query(Broker).count()
    active_brokers = db.query(Broker).filter(Broker.is_active == True).count()
    total_commissions = db.query(CommissionTracking).count()
    pending_commissions = (
        db.query(CommissionTracking)
        .filter(CommissionTracking.status == CommissionStatus.PENDING)
        .count()
    )
    total_payouts = db.query(BrokerPayout).count()
    scheduled_payouts = (
        db.query(BrokerPayout).filter(BrokerPayout.status == PayoutStatus.SCHEDULED).count()
    )
    total_campaigns = db.query(Campaign).count()
    active_campaigns = db.query(Campaign).filter(Campaign.status == CampaignStatus.ACTIVE).count()
    unresolved_alerts = db.query(Alert).filter(Alert.is_resolved == False).count()
    return {
        "brokers": {
            "total": total_brokers,
            "active": active_brokers,
        },
        "commissions": {
            "total": total_commissions,
            "pending": pending_commissions,
        },
        "payouts": {
            "total": total_payouts,
            "scheduled": scheduled_payouts,
        },
        "campaigns": {
            "total": total_campaigns,
            "active": active_campaigns,
        },
        "alerts": {
            "unresolved": unresolved_alerts,
        },
    }


@router.get("/broker/{broker_id}")
def get_broker_dashboard(broker_id: int, db: Session = Depends(get_db)):
    """Get dashboard data for a specific broker."""
    broker = db.query(Broker).filter(Broker.id == broker_id).first()
    if not broker:
        raise HTTPException(status_code=404, detail="Broker not found")
    commissions = (
        db.query(CommissionTracking).filter(CommissionTracking.broker_id == broker_id).all()
    )
    payouts = db.query(BrokerPayout).filter(BrokerPayout.broker_id == broker_id).all()
    partners = db.query(BrokerPartner).filter(BrokerPartner.broker_id == broker_id).all()
    total_commission = sum(float(c.commission_amount) for c in commissions)
    total_payout = sum(float(p.amount) for p in payouts)
    return {
        "broker": {
            "id": broker.id,
            "name": broker.name,
            "country": broker.country,
            "currency": broker.currency,
        },
        "commissions": {
            "total_count": len(commissions),
            "total_amount": total_commission,
            "by_status": {
                status.value: len([c for c in commissions if c.status == status])
                for status in CommissionStatus
            },
        },
        "payouts": {
            "total_count": len(payouts),
            "total_amount": total_payout,
            "by_status": {
                status.value: len([p for p in payouts if p.status == status])
                for status in PayoutStatus
            },
        },
        "partners": {
            "total_count": len(partners),
            "active_count": len([p for p in partners if p.is_active]),
        },
    }


@router.get("/campaigns/{campaign_id}/performance")
def get_campaign_performance(campaign_id: int, db: Session = Depends(get_db)):
    """Get performance metrics for a campaign."""
    from app.models.campaign_metric import CampaignMetric

    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    metrics = db.query(CampaignMetric).filter(CampaignMetric.campaign_id == campaign_id).all()
    total_impressions = sum(m.impressions for m in metrics)
    total_clicks = sum(m.clicks for m in metrics)
    total_conversions = sum(m.conversions for m in metrics)
    total_spend = sum(float(m.spend) for m in metrics)
    total_revenue = sum(float(m.revenue) for m in metrics)
    ctr = total_clicks / total_impressions if total_impressions > 0 else 0
    roas = total_revenue / total_spend if total_spend > 0 else 0
    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.name,
        "status": campaign.status.value,
        "metrics": {
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "total_spend": total_spend,
            "total_revenue": total_revenue,
            "ctr": round(ctr, 6),
            "roas": round(roas, 4),
        },
    }


@router.get("/alerts")
def get_alerts(
    severity: str | None = None,
    resolved: bool | None = None,
    db: Session = Depends(get_db),
):
    """Get alerts with optional filtering."""
    query = db.query(Alert)
    if severity:
        query = query.filter(Alert.severity == severity)
    if resolved is not None:
        query = query.filter(Alert.is_resolved == resolved)
    alerts = query.all()
    return [
        {
            "id": a.id,
            "campaign_id": a.campaign_id,
            "alert_type": a.alert_type.value,
            "severity": a.severity.value,
            "message": a.message,
            "is_resolved": a.is_resolved,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]
