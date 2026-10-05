"""Basic broker management module."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/brokers", tags=["brokers"])


class Broker(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    country: str
    created_at: datetime


class BrokerCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    country: str


class BrokerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None


class BrokerRepository:
    def __init__(self):
        self._brokers: dict[int, Broker] = {}
        self._next_id = 1

    def create(self, data: BrokerCreate) -> Broker:
        broker = Broker(
            id=self._next_id,
            name=data.name,
            email=data.email,
            phone=data.phone,
            country=data.country,
            created_at=datetime.now(timezone.utc),
        )
        self._brokers[broker.id] = broker
        self._next_id += 1
        return broker

    def get(self, broker_id: int) -> Optional[Broker]:
        return self._brokers.get(broker_id)

    def list(self) -> list[Broker]:
        return list(self._brokers.values())

    def update(self, broker_id: int, data: BrokerUpdate) -> Optional[Broker]:
        broker = self._brokers.get(broker_id)
        if not broker:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(broker, field, value)
        return broker

    def delete(self, broker_id: int) -> bool:
        return self._brokers.pop(broker_id, None) is not None


repo = BrokerRepository()


@router.post("", response_model=Broker, status_code=201)
def create_broker(data: BrokerCreate):
    return repo.create(data)


@router.get("", response_model=list[Broker])
def list_brokers():
    return repo.list()


@router.get("/{broker_id}", response_model=Broker)
def get_broker(broker_id: int):
    broker = repo.get(broker_id)
    if not broker:
        raise HTTPException(status_code=404, detail="Broker not found")
    return broker


@router.put("/{broker_id}", response_model=Broker)
def update_broker(broker_id: int, data: BrokerUpdate):
    broker = repo.update(broker_id, data)
    if not broker:
        raise HTTPException(status_code=404, detail="Broker not found")
    return broker


@router.delete("/{broker_id}", status_code=204)
def delete_broker(broker_id: int):
    if not repo.delete(broker_id):
        raise HTTPException(status_code=404, detail="Broker not found")
