"""Commission API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.broker import Broker
from app.models.commission_tracking import CommissionTracking, CommissionStatus
from app.schemas.commission import (
    CommissionCalculateRequest,
    CommissionCalculateResponse,
    CommissionCreate,
    CommissionUpdate,
    CommissionResponse,
)

router = APIRouter(prefix="/api/v1/commissions", tags=["commissions"])


@router.post("/calculate", response_model=CommissionCalculateResponse)
def calculate_commission(request: CommissionCalculateRequest, db: Session = Depends(get_db)):
    """Calculate commission for a deal."""
    broker = db.query(Broker).filter(Broker.id == request.broker_id).first()
    if not broker:
        raise HTTPException(status_code=404, detail="Broker not found")

    commission_amount = request.deal_amount * broker.commission_rate

    return CommissionCalculateResponse(
        broker_id=request.broker_id,
        deal_amount=request.deal_amount,
        commission_rate=broker.commission_rate,
        commission_amount=commission_amount,
        currency=request.currency,
    )


@router.post("", response_model=CommissionResponse, status_code=status.HTTP_201_CREATED)
def create_commission(commission: CommissionCreate, db: Session = Depends(get_db)):
    """Create a commission tracking record."""
    db_commission = CommissionTracking(**commission.model_dump())
    db.add(db_commission)
    db.commit()
    db.refresh(db_commission)
    return db_commission


@router.get("", response_model=list[CommissionResponse])
def list_commissions(broker_id: int | None = None, db: Session = Depends(get_db)):
    """List commissions, optionally filtered by broker."""
    query = db.query(CommissionTracking)
    if broker_id:
        query = query.filter(CommissionTracking.broker_id == broker_id)
    return query.all()


@router.patch("/{commission_id}/status", response_model=CommissionResponse)
def update_commission_status(
    commission_id: int, update: CommissionUpdate, db: Session = Depends(get_db)
):
    """Update commission status."""
    db_commission = (
        db.query(CommissionTracking).filter(CommissionTracking.id == commission_id).first()
    )
    if not db_commission:
        raise HTTPException(status_code=404, detail="Commission not found")

    db_commission.status = CommissionStatus(update.status)
    db.commit()
    db.refresh(db_commission)
    return db_commission
