"""Shared fixtures for UGC Marketplace test suite."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app import models  # noqa: F401 - ensures all models are registered with Base
from app.models.base import Base
from app.main import app
from app.database import get_db


@pytest.fixture
def db_session():
    """Create a fresh in-memory database session."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    """Create a test client with overridden DB dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_broker_data():
    """Sample broker data for testing."""
    return {
        "name": "Test Broker",
        "name_ar": "بروكر تجريبي",
        "country": "AE",
        "currency": "AED",
        "commission_rate": 0.05,
        "contact_email": "broker@example.com",
        "contact_phone": "+971501234567",
        "is_active": True,
    }


@pytest.fixture
def sample_broker(client, sample_broker_data):
    """Create a broker via API and return the response."""
    resp = client.post("/api/v1/brokers", json=sample_broker_data)
    return resp.json()


@pytest.fixture
def sample_commission_data(sample_broker):
    """Sample commission data for testing."""
    return {
        "broker_id": sample_broker["id"],
        "deal_id": "DEAL-001",
        "deal_description": "Test deal",
        "deal_amount": 10000.00,
        "commission_rate": 0.05,
        "commission_amount": 500.00,
        "currency": "AED",
        "deal_date": "2024-01-15",
    }


@pytest.fixture
def sample_payout_data(sample_broker):
    """Sample payout data for testing."""
    return {
        "broker_id": sample_broker["id"],
        "amount": 5000.00,
        "currency": "AED",
        "payout_method": "bank_transfer",
        "reference_number": "PAY-001",
        "bank_name": "Emirates NBD",
        "bank_account_last4": "1234",
        "iban": "AE070331234567890123456",
        "scheduled_date": "2024-03-01",
    }


@pytest.fixture
def sample_campaign_data():
    """Sample campaign data for testing."""
    return {
        "name": "Test Campaign",
        "description": "A test campaign",
        "status": "active",
        "budget": 10000.00,
        "spent": 5000.00,
        "target_roas": 2.0,
        "target_ctr": 0.01,
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "is_active": True,
    }
