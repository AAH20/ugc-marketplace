"""Tests for broker module."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from broker import BrokerRepository, BrokerCreate, BrokerUpdate, router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture
def repo():
    return BrokerRepository()


def test_create_broker(repo):
    broker = repo.create(BrokerCreate(name="Test", email="t@t.com", country="AE"))
    assert broker.id == 1
    assert broker.name == "Test"
    assert broker.country == "AE"


def test_get_broker(repo):
    repo.create(BrokerCreate(name="Test", email="t@t.com", country="AE"))
    broker = repo.get(1)
    assert broker is not None
    assert broker.email == "t@t.com"


def test_list_brokers(repo):
    repo.create(BrokerCreate(name="A", email="a@t.com", country="AE"))
    repo.create(BrokerCreate(name="B", email="b@t.com", country="SA"))
    assert len(repo.list()) == 2


def test_update_broker(repo):
    repo.create(BrokerCreate(name="Test", email="t@t.com", country="AE"))
    updated = repo.update(1, BrokerUpdate(name="Updated"))
    assert updated.name == "Updated"
    assert updated.email == "t@t.com"


def test_delete_broker(repo):
    repo.create(BrokerCreate(name="Test", email="t@t.com", country="AE"))
    assert repo.delete(1) is True
    assert repo.get(1) is None
