"""Simple performance benchmark tests for UGC Marketplace.

Measures API response times using time.perf_counter().
No external dependencies - just timing measurements.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Create a FastAPI TestClient."""
    from ugc_marketplace.main import app

    return TestClient(app)


def test_health_endpoint_latency(client: TestClient) -> None:
    """Benchmark GET /api/v1/health response time."""
    # Warmup
    for _ in range(5):
        client.get("/api/v1/health")

    # Timed runs
    iterations = 50
    start = time.perf_counter()
    for _ in range(iterations):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
    elapsed_ms = (time.perf_counter() - start) * 1000

    avg_ms = elapsed_ms / iterations
    print(f"\nHealth endpoint: {avg_ms:.2f}ms avg over {iterations} iterations")
    assert avg_ms < 50, f"Health endpoint too slow: {avg_ms:.2f}ms"


def test_crud_endpoint_latency(client: TestClient) -> None:
    """Benchmark GET /api/v1/marketplace/marketplace/listings response time."""
    # Warmup
    for _ in range(3):
        client.get("/api/v1/marketplace/marketplace/listings")

    # Timed runs
    iterations = 30
    start = time.perf_counter()
    for _ in range(iterations):
        resp = client.get("/api/v1/marketplace/marketplace/listings")
        assert resp.status_code == 200
    elapsed_ms = (time.perf_counter() - start) * 1000

    avg_ms = elapsed_ms / iterations
    print(f"\nCRUD endpoint (list listings): {avg_ms:.2f}ms avg over {iterations} iterations")
    assert avg_ms < 100, f"CRUD endpoint too slow: {avg_ms:.2f}ms"


def test_concurrent_health_requests(client: TestClient) -> None:
    """Benchmark concurrent health check requests."""
    num_requests = 50
    max_workers = 10

    # Warmup
    client.get("/api/v1/health")

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(client.get, "/api/v1/health")
            for _ in range(num_requests)
        ]
        for f in futures:
            resp = f.result()
            assert resp.status_code == 200
    elapsed_ms = (time.perf_counter() - start) * 1000

    throughput = num_requests / (elapsed_ms / 1000)
    print(
        f"\nConcurrent health ({num_requests} req, {max_workers} workers): "
        f"{elapsed_ms:.2f}ms total, {throughput:.1f} req/s"
    )
    assert elapsed_ms < 5000, f"Concurrent health too slow: {elapsed_ms:.2f}ms"


def test_concurrent_crud_requests(client: TestClient) -> None:
    """Benchmark concurrent CRUD (list listings) requests."""
    num_requests = 30
    max_workers = 10

    # Warmup
    client.get("/api/v1/marketplace/marketplace/listings")

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(client.get, "/api/v1/marketplace/marketplace/listings")
            for _ in range(num_requests)
        ]
        for f in futures:
            resp = f.result()
            assert resp.status_code == 200
    elapsed_ms = (time.perf_counter() - start) * 1000

    throughput = num_requests / (elapsed_ms / 1000)
    print(
        f"\nConcurrent CRUD ({num_requests} req, {max_workers} workers): "
        f"{elapsed_ms:.2f}ms total, {throughput:.1f} req/s"
    )
    assert elapsed_ms < 10000, f"Concurrent CRUD too slow: {elapsed_ms:.2f}ms"


def test_concurrent_mixed_requests(client: TestClient) -> None:
    """Benchmark concurrent mixed read requests (health + listings)."""
    num_requests = 60
    max_workers = 15

    # Warmup
    client.get("/api/v1/health")
    client.get("/api/v1/marketplace/marketplace/listings")

    def mixed_request(i: int) -> None:
        if i % 2 == 0:
            client.get("/api/v1/health")
        else:
            client.get("/api/v1/marketplace/marketplace/listings")

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(mixed_request, i)
            for i in range(num_requests)
        ]
        for f in futures:
            f.result()
    elapsed_ms = (time.perf_counter() - start) * 1000

    throughput = num_requests / (elapsed_ms / 1000)
    print(
        f"\nConcurrent mixed ({num_requests} req, {max_workers} workers): "
        f"{elapsed_ms:.2f}ms total, {throughput:.1f} req/s"
    )
    assert elapsed_ms < 10000, f"Concurrent mixed too slow: {elapsed_ms:.2f}ms"
