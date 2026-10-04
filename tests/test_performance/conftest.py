"""Shared fixtures for performance benchmark tests."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pytest


@dataclass
class TimingResult:
    """Result of a single timing measurement."""

    name: str
    duration_ms: float
    iterations: int
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def avg_ms(self) -> float:
        return self.duration_ms / self.iterations if self.iterations > 0 else 0.0


@dataclass
class BenchmarkSuite:
    """Collection of timing results for a benchmark category."""

    name: str
    results: list[TimingResult] = field(default_factory=list)

    def add(self, result: TimingResult) -> None:
        self.results.append(result)

    @property
    def total_ms(self) -> float:
        return sum(r.duration_ms for r in self.results)

    @property
    def avg_ms(self) -> float:
        if not self.results:
            return 0.0
        return self.total_ms / len(self.results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite": self.name,
            "total_ms": round(self.total_ms, 2),
            "avg_ms": round(self.avg_ms, 2),
            "benchmarks": [
                {
                    "name": r.name,
                    "duration_ms": round(r.duration_ms, 2),
                    "iterations": r.iterations,
                    "avg_ms": round(r.avg_ms, 2),
                    "metadata": r.metadata,
                }
                for r in self.results
            ],
        }


def time_function(
    func: Callable[..., Any],
    *args: Any,
    iterations: int = 1,
    warmup: int = 0,
    **kwargs: Any,
) -> TimingResult:
    """Time a function execution with optional warmup and multiple iterations.

    Args:
        func: Function to time.
        *args: Positional arguments for the function.
        iterations: Number of times to run the function.
        warmup: Number of warmup runs (not counted).
        **kwargs: Keyword arguments for the function.

    Returns:
        TimingResult with timing data.
    """
    # Warmup runs
    for _ in range(warmup):
        func(*args, **kwargs)

    # Timed runs
    durations: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        func(*args, **kwargs)
        end = time.perf_counter()
        durations.append((end - start) * 1000)  # Convert to ms

    total_ms = sum(durations)
    return TimingResult(
        name=func.__name__,
        duration_ms=total_ms,
        iterations=iterations,
        metadata={
            "min_ms": round(min(durations), 2),
            "max_ms": round(max(durations), 2),
            "median_ms": round(sorted(durations)[len(durations) // 2], 2),
            "p95_ms": round(sorted(durations)[int(len(durations) * 0.95)], 2) if len(durations) > 1 else round(durations[0], 2),
        },
    )


async def time_async_function(
    func: Callable[..., Any],
    *args: Any,
    iterations: int = 1,
    warmup: int = 0,
    **kwargs: Any,
) -> TimingResult:
    """Time an async function execution with optional warmup and multiple iterations.

    Args:
        func: Async function to time.
        *args: Positional arguments for the function.
        iterations: Number of times to run the function.
        warmup: Number of warmup runs (not counted).
        **kwargs: Keyword arguments for the function.

    Returns:
        TimingResult with timing data.
    """
    # Warmup runs
    for _ in range(warmup):
        await func(*args, **kwargs)

    # Timed runs
    durations: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        await func(*args, **kwargs)
        end = time.perf_counter()
        durations.append((end - start) * 1000)  # Convert to ms

    total_ms = sum(durations)
    return TimingResult(
        name=func.__name__,
        duration_ms=total_ms,
        iterations=iterations,
        metadata={
            "min_ms": round(min(durations), 2),
            "max_ms": round(max(durations), 2),
            "median_ms": round(sorted(durations)[len(durations) // 2], 2),
            "p95_ms": round(sorted(durations)[int(len(durations) * 0.95)], 2) if len(durations) > 1 else round(durations[0], 2),
        },
    )


@pytest.fixture
def benchmark_suite() -> BenchmarkSuite:
    """Create a benchmark suite for collecting results."""
    return BenchmarkSuite(name="performance_benchmarks")


@pytest.fixture
def api_client():
    """Create a FastAPI TestClient for API benchmarking."""
    from fastapi.testclient import TestClient

    from ugc_marketplace.main import app

    return TestClient(app)


@pytest.fixture
def sample_content_payload() -> dict:
    """Return a valid payload for creating content."""
    return {
        "title": "Benchmark Test Content",
        "type": "image",
        "author_id": "user-bench-001",
        "description": "Content created during performance benchmarking.",
        "tags": ["benchmark", "performance", "test"],
        "media_url": "https://cdn.example.com/media/bench.jpg",
    }


@pytest.fixture
def sample_listing_payload() -> dict:
    """Return a valid payload for creating a listing."""
    return {
        "seller_id": "seller-bench-001",
        "title": "Benchmark Listing Item",
        "description": "A listing created during performance benchmarking. " * 5,
        "category": "digital_art",
        "price": {"amount_cents": 4999, "currency": "USD"},
        "tags": ["benchmark", "digital-art"],
        "media_urls": ["https://cdn.example.com/listing/1.jpg"],
    }
