"""Payout API routes."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.broker_payout import BrokerPayout, PayoutStatus
from app.schemas.payout import (
    PayoutCreate,
    PayoutUpdate,
    PayoutResponse,
    PayoutSummaryResponse,
)

router = APIRouter(prefix="/api/v1/payouts", tags=["payouts"])


@router.post("", response_model=PayoutResponse, status_code=status.HTTP_201_CREATED)
def create_payout(payout: PayoutCreate, db: Session = Depends(get_db)):
    """Create a new payout."""
    db_payout = BrokerPayout(**payout.model_dump())
    db.add(db_payout)
    db.commit()
    db.refresh(db_payout)
    return db_payout


@router.get("", response_model=list[PayoutResponse])
def list_payouts(broker_id: int | None = None, db: Session = Depends(get_db)):
    """List payouts, optionally filtered by broker."""
    query = db.query(BrokerPayout)
    if broker_id:
        query = query.filter(BrokerPayout.broker_id == broker_id)
    return query.all()


@router.get("/summary", response_model=PayoutSummaryResponse)
def get_payout_summary(broker_id: int, db: Session = Depends(get_db)):
    """Get payout summary for a broker."""
    result = (
        db.query(
            func.sum(BrokerPayout.amount).label("total_amount"),
            func.count(BrokerPayout.id).label("count"),
        )
        .filter(BrokerPayout.broker_id == broker_id)
        .first()
    )

    # Get currency from broker's payouts
    payout = db.query(BrokerPayout).filter(BrokerPayout.broker_id == broker_id).first()
    currency = payout.currency if payout else "AED"

    return PayoutSummaryResponse(
        broker_id=broker_id,
        total_amount=Decimal(str(result.total_amount or 0)),
        currency=currency,
        count=result.count or 0,
    )


@router.patch("/{payout_id}/status", response_model=PayoutResponse)
def update_payout_status(payout_id: int, update: PayoutUpdate, db: Session = Depends(get_db)):
    """Update payout status."""
    db_payout = db.query(BrokerPayout).filter(BrokerPayout.id == payout_id).first()
    if not db_payout:
        raise HTTPException(status_code=404, detail="Payout not found")

    db_payout.status = PayoutStatus(update.status)
    if update.completed_date:
        db_payout.completed_date = update.completed_date

    db.commit()
    db.refresh(db_payout)
    return db_payout
