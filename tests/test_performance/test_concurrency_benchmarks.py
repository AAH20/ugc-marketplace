"""Concurrent request handling benchmarks for UGC Marketplace.

Measures system behavior under concurrent load for:
- API endpoint concurrent access
- Content service concurrent operations
- Agent concurrent execution
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.test_performance.conftest import BenchmarkSuite, TimingResult


def run_concurrent_sync(
    func: Callable[..., Any],
    args_list: list[tuple],
    max_workers: int = 10,
) -> TimingResult:
    """Run a synchronous function concurrently using ThreadPoolExecutor.

    Args:
        func: Function to execute.
        args_list: List of argument tuples, one per concurrent call.
        max_workers: Maximum number of worker threads.

    Returns:
        TimingResult with aggregate timing data.
    """
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(func, *args) for args in args_list]
        for f in futures:
            f.result()  # Wait for all to complete
    end = time.perf_counter()

    total_ms = (end - start) * 1000
    return TimingResult(
        name=f"concurrent_{func.__name__}",
        duration_ms=total_ms,
        iterations=len(args_list),
        metadata={
            "max_workers": max_workers,
            "total_calls": len(args_list),
            "throughput_rps": round(len(args_list) / (total_ms / 1000), 2),
        },
    )


async def run_concurrent_async(
    func: Callable[..., Any],
    args_list: list[tuple],
    concurrency: int = 10,
) -> TimingResult:
    """Run an async function concurrently using asyncio semaphore.

    Args:
        func: Async function to execute.
        args_list: List of argument tuples, one per concurrent call.
        concurrency: Maximum number of concurrent executions.

    Returns:
        TimingResult with aggregate timing data.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded_call(*args: Any) -> None:
        async with semaphore:
            await func(*args)

    start = time.perf_counter()
    tasks = [bounded_call(*args) for args in args_list]
    await asyncio.gather(*tasks)
    end = time.perf_counter()

    total_ms = (end - start) * 1000
    return TimingResult(
        name=f"concurrent_async_{func.__name__}",
        duration_ms=total_ms,
        iterations=len(args_list),
        metadata={
            "concurrency": concurrency,
            "total_calls": len(args_list),
            "throughput_rps": round(len(args_list) / (total_ms / 1000), 2),
        },
    )


class TestConcurrentAPIBenchmarks:
    """Benchmark concurrent API request handling."""

    def test_concurrent_health_checks(self, api_client: TestClient, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark concurrent health check requests."""
        args_list = [("/api/v1/health",) for _ in range(100)]
        result = run_concurrent_sync(api_client.get, args_list, max_workers=20)
        result.name = "concurrent_health_100"
        benchmark_suite.add(result)
        assert result.duration_ms < 5000, f"Concurrent health checks too slow: {result.duration_ms:.2f}ms"

    def test_concurrent_content_list(self, api_client: TestClient, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark concurrent content list requests."""
        args_list = [("/api/v1/content",) for _ in range(50)]
        result = run_concurrent_sync(api_client.get, args_list, max_workers=10)
        result.name = "concurrent_content_list_50"
        benchmark_suite.add(result)
        assert result.duration_ms < 10000, f"Concurrent content list too slow: {result.duration_ms:.2f}ms"

    def test_concurrent_content_creation(
        self, api_client: TestClient, benchmark_suite: BenchmarkSuite
    ) -> None:
        """Benchmark concurrent content creation."""
        def create_content(i: int) -> None:
            api_client.post(
                "/api/v1/content",
                json={
                    "title": f"Concurrent Content {i}",
                    "type": "image",
                    "author_id": f"user_concurrent_{i}",
                    "description": f"Content created concurrently #{i}",
                },
            )

        args_list = [(i,) for i in range(30)]
        result = run_concurrent_sync(create_content, args_list, max_workers=10)
        result.name = "concurrent_content_create_30"
        benchmark_suite.add(result)
        assert result.duration_ms < 15000, f"Concurrent content creation too slow: {result.duration_ms:.2f}ms"

    def test_concurrent_mixed_operations(self, api_client: TestClient, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark concurrent mixed API operations."""
        def mixed_operation(i: int) -> None:
            # Mix of read and write operations
            if i % 3 == 0:
                api_client.get("/api/v1/content")
            elif i % 3 == 1:
                api_client.get("/api/v1/health")
            else:
                api_client.get("/api/v1/listings")

        args_list = [(i,) for i in range(60)]
        result = run_concurrent_sync(mixed_operation, args_list, max_workers=15)
        result.name = "concurrent_mixed_60"
        benchmark_suite.add(result)
        assert result.duration_ms < 10000, f"Concurrent mixed operations too slow: {result.duration_ms:.2f}ms"


class TestConcurrentServiceBenchmarks:
    """Benchmark concurrent service operations."""

    def test_concurrent_content_creation_service(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark concurrent content creation via service layer."""
        from ugc_marketplace.services.content_service import create_content

        def create_item(i: int = 0) -> None:
            create_content({
                "title": f"Concurrent Service Content {i}",
                "description": f"Description {i}",
                "content_type": "image",
                "creator_id": f"creator_concurrent_{i % 10}",
            })

        args_list = [(i,) for i in range(50)]
        result = run_concurrent_sync(create_item, args_list, max_workers=10)
        result.name = "concurrent_service_create_50"
        benchmark_suite.add(result)
        assert result.duration_ms < 5000, f"Concurrent service creation too slow: {result.duration_ms:.2f}ms"

    def test_concurrent_quality_scoring(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark concurrent quality scoring."""
        from ugc_marketplace.agents.quality_scoring import score_content

        content_ids = ["vid_001", "vid_002", "img_001", "txt_001", "aud_001"]
        args_list = [(content_ids[i % 5],) for i in range(50)]
        result = run_concurrent_sync(score_content, args_list, max_workers=10)
        result.name = "concurrent_quality_score_50"
        benchmark_suite.add(result)
        assert result.duration_ms < 5000, f"Concurrent quality scoring too slow: {result.duration_ms:.2f}ms"

    def test_concurrent_listing_creation_service(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark concurrent listing creation via service layer."""
        from ugc_marketplace.services.listing_service import create_listing

        def create_item(i: int = 0) -> None:
            create_listing({
                "seller_id": f"seller_concurrent_{i % 10}",
                "title": f"Concurrent Listing {i}",
                "description": f"Description for concurrent listing {i}. " * 3,
                "category": "digital_art",
                "price": {"amount_cents": 4999, "currency": "USD"},
            })

        args_list = [(i,) for i in range(30)]
        result = run_concurrent_sync(create_item, args_list, max_workers=10)
        result.name = "concurrent_listing_create_30"
        benchmark_suite.add(result)
        assert result.duration_ms < 5000, f"Concurrent listing creation too slow: {result.duration_ms:.2f}ms"


class TestConcurrentAsyncBenchmarks:
    """Benchmark concurrent async operations."""

    @pytest.mark.asyncio
    async def test_concurrent_async_content_scoring(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark concurrent async content scoring operations."""
        from ugc_marketplace.agents.quality_scoring import score_content

        # Wrap sync function for async execution
        async def async_score(content_id: str) -> None:
            score_content(content_id)

        content_ids = ["vid_001", "vid_002", "img_001", "txt_001", "aud_001"]
        args_list = [(content_ids[i % 5],) for i in range(30)]
        result = await run_concurrent_async(async_score, args_list, concurrency=10)
        result.name = "concurrent_async_scoring_30"
        benchmark_suite.add(result)
        assert result.duration_ms < 5000, f"Concurrent async scoring too slow: {result.duration_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_concurrent_async_health_checks(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark concurrent async health check simulations."""
        async def async_health_check(_: int) -> None:
            # Simulate async health check
            await asyncio.sleep(0.001)  # 1ms simulated latency

        args_list = [(i,) for i in range(100)]
        result = await run_concurrent_async(async_health_check, args_list, concurrency=20)
        result.name = "concurrent_async_health_100"
        benchmark_suite.add(result)
        assert result.duration_ms < 5000, f"Concurrent async health checks too slow: {result.duration_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_concurrent_async_mixed_workload(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark concurrent async mixed workload."""
        from ugc_marketplace.agents.quality_scoring import score_content

        async def mixed_async_work(i: int) -> None:
            if i % 3 == 0:
                score_content("vid_001")
            elif i % 3 == 1:
                await asyncio.sleep(0.001)
            else:
                score_content("img_001")

        args_list = [(i,) for i in range(60)]
        result = await run_concurrent_async(mixed_async_work, args_list, concurrency=15)
        result.name = "concurrent_async_mixed_60"
        benchmark_suite.add(result)
        assert result.duration_ms < 10000, f"Concurrent async mixed workload too slow: {result.duration_ms:.2f}ms"


class TestConcurrencyBenchmarkSummary:
    """Summary test that prints all concurrency benchmark results."""

    def test_print_concurrency_benchmark_summary(self, benchmark_suite: BenchmarkSuite) -> None:
        """Print summary of concurrency benchmarks."""
        print("\n" + "=" * 70)
        print("CONCURRENCY BENCHMARK SUMMARY")
        print("=" * 70)
        print(f"Total benchmarks: {len(benchmark_suite.results)}")
        for r in benchmark_suite.results:
            throughput = r.metadata.get("throughput_rps", "N/A")
            print(f"  {r.name}: {r.duration_ms:.2f}ms total, {r.iterations} calls, {throughput} req/s")
        print("=" * 70)
