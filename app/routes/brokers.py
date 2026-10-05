"""Broker API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.broker import Broker
from app.schemas.broker import BrokerCreate, BrokerUpdate, BrokerResponse

router = APIRouter(prefix="/api/v1/brokers", tags=["brokers"])


@router.post("", response_model=BrokerResponse, status_code=status.HTTP_201_CREATED)
def create_broker(broker: BrokerCreate, db: Session = Depends(get_db)):
    """Create a new broker."""
    db_broker = Broker(**broker.model_dump())
    db.add(db_broker)
    db.commit()
    db.refresh(db_broker)
    return db_broker


@router.get("", response_model=list[BrokerResponse])
def list_brokers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all brokers."""
    return db.query(Broker).offset(skip).limit(limit).all()


@router.get("/{broker_id}", response_model=BrokerResponse)
def get_broker(broker_id: int, db: Session = Depends(get_db)):
    """Get a specific broker by ID."""
    broker = db.query(Broker).filter(Broker.id == broker_id).first()
    if not broker:
        raise HTTPException(status_code=404, detail="Broker not found")
    return broker


@router.put("/{broker_id}", response_model=BrokerResponse)
def update_broker(broker_id: int, broker_update: BrokerUpdate, db: Session = Depends(get_db)):
    """Update a broker."""
    db_broker = db.query(Broker).filter(Broker.id == broker_id).first()
    if not db_broker:
        raise HTTPException(status_code=404, detail="Broker not found")

    for field, value in broker_update.model_dump(exclude_unset=True).items():
        setattr(db_broker, field, value)

    db.commit()
    db.refresh(db_broker)
    return db_broker


@router.delete("/{broker_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_broker(broker_id: int, db: Session = Depends(get_db)):
    """Delete a broker."""
    db_broker = db.query(Broker).filter(Broker.id == broker_id).first()
    if not db_broker:
        raise HTTPException(status_code=404, detail="Broker not found")

    db.delete(db_broker)
    db.commit()
