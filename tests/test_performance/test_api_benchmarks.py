"""API response time benchmarks for UGC Marketplace.

Measures HTTP endpoint latency for:
- Health checks
- Content CRUD operations
- Listing operations
- Search operations
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.test_performance.conftest import BenchmarkSuite, time_function


class TestHealthEndpointBenchmarks:
    """Benchmark health check endpoints."""

    def test_health_check_latency(self, api_client: TestClient, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark GET /api/v1/health response time."""
        result = time_function(
            api_client.get,
            "/api/v1/health",
            iterations=100,
            warmup=10,
        )
        benchmark_suite.add(result)
        assert result.avg_ms < 50, f"Health check too slow: {result.avg_ms:.2f}ms"

    def test_readiness_check_latency(self, api_client: TestClient, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark GET /api/v1/health/ready response time."""
        result = time_function(
            api_client.get,
            "/api/v1/health/ready",
            iterations=100,
            warmup=10,
        )
        benchmark_suite.add(result)
        assert result.avg_ms < 50, f"Readiness check too slow: {result.avg_ms:.2f}ms"

    def test_liveness_check_latency(self, api_client: TestClient, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark GET /api/v1/health/live response time."""
        result = time_function(
            api_client.get,
            "/api/v1/health/live",
            iterations=100,
            warmup=10,
        )
        benchmark_suite.add(result)
        assert result.avg_ms < 50, f"Liveness check too slow: {result.avg_ms:.2f}ms"


class TestContentAPIBenchmarks:
    """Benchmark content API endpoints."""

    def test_list_content_latency(self, api_client: TestClient, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark GET /api/v1/content response time."""
        result = time_function(
            api_client.get,
            "/api/v1/content",
            iterations=50,
            warmup=5,
        )
        benchmark_suite.add(result)
        assert result.avg_ms < 100, f"List content too slow: {result.avg_ms:.2f}ms"

    def test_list_content_with_filters_latency(self, api_client: TestClient, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark GET /api/v1/content with type and status filters."""
        def filtered_get() -> None:
            api_client.get("/api/v1/content?type=image&status=published")

        result = time_function(filtered_get, iterations=50, warmup=5)
        result.name = "list_content_filtered"
        benchmark_suite.add(result)
        assert result.avg_ms < 100, f"Filtered list content too slow: {result.avg_ms:.2f}ms"

    def test_create_content_latency(
        self, api_client: TestClient, benchmark_suite: BenchmarkSuite, sample_content_payload: dict
    ) -> None:
        """Benchmark POST /api/v1/content response time."""
        result = time_function(
            api_client.post,
            "/api/v1/content",
            json=sample_content_payload,
            iterations=30,
            warmup=3,
        )
        benchmark_suite.add(result)
        assert result.avg_ms < 200, f"Create content too slow: {result.avg_ms:.2f}ms"

    def test_get_content_by_id_latency(self, api_client: TestClient, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark GET /api/v1/content/{id} response time."""
        # First create content to get a valid ID
        create_resp = api_client.post(
            "/api/v1/content",
            json={
                "title": "Benchmark Get Test",
                "type": "image",
                "author_id": "user-bench-get",
                "description": "Test content for get benchmark",
            },
        )
        content_id = create_resp.json()["id"]

        result = time_function(
            api_client.get,
            f"/api/v1/content/{content_id}",
            iterations=50,
            warmup=5,
        )
        result.name = "get_content_by_id"
        benchmark_suite.add(result)
        assert result.avg_ms < 100, f"Get content by ID too slow: {result.avg_ms:.2f}ms"

    def test_update_content_latency(self, api_client: TestClient, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark PUT /api/v1/content/{id} response time."""
        # Create content first
        create_resp = api_client.post(
            "/api/v1/content",
            json={
                "title": "Benchmark Update Test",
                "type": "image",
                "author_id": "user-bench-update",
                "description": "Test content for update benchmark",
            },
        )
        content_id = create_resp.json()["id"]

        def update_content() -> None:
            api_client.put(
                f"/api/v1/content/{content_id}",
                json={"title": "Updated Benchmark Title"},
            )

        result = time_function(update_content, iterations=30, warmup=3)
        result.name = "update_content"
        benchmark_suite.add(result)
        assert result.avg_ms < 200, f"Update content too slow: {result.avg_ms:.2f}ms"

    def test_delete_content_latency(self, api_client: TestClient, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark DELETE /api/v1/content/{id} response time."""
        # Create content to delete
        create_resp = api_client.post(
            "/api/v1/content",
            json={
                "title": "Benchmark Delete Test",
                "type": "image",
                "author_id": "user-bench-delete",
                "description": "Test content for delete benchmark",
            },
        )
        content_id = create_resp.json()["id"]

        result = time_function(
            api_client.delete,
            f"/api/v1/content/{content_id}",
            iterations=30,
            warmup=3,
        )
        result.name = "delete_content"
        benchmark_suite.add(result)
        assert result.avg_ms < 200, f"Delete content too slow: {result.avg_ms:.2f}ms"


class TestListingAPIBenchmarks:
    """Benchmark listing API endpoints."""

    def test_list_listings_latency(self, api_client: TestClient, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark GET /api/v1/listings response time."""
        result = time_function(
            api_client.get,
            "/api/v1/listings",
            iterations=50,
            warmup=5,
        )
        benchmark_suite.add(result)
        assert result.avg_ms < 100, f"List listings too slow: {result.avg_ms:.2f}ms"

    def test_create_listing_latency(
        self, api_client: TestClient, benchmark_suite: BenchmarkSuite, sample_listing_payload: dict
    ) -> None:
        """Benchmark POST /api/v1/listings response time."""
        result = time_function(
            api_client.post,
            "/api/v1/listings",
            json=sample_listing_payload,
            iterations=30,
            warmup=3,
        )
        benchmark_suite.add(result)
        assert result.avg_ms < 200, f"Create listing too slow: {result.avg_ms:.2f}ms"


class TestSearchAPIBenchmarks:
    """Benchmark search API endpoints."""

    def test_search_content_latency(self, api_client: TestClient, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark GET /api/v1/search response time."""
        result = time_function(
            api_client.get,
            "/api/v1/search?query=test",
            iterations=30,
            warmup=3,
        )
        benchmark_suite.add(result)
        assert result.avg_ms < 200, f"Search content too slow: {result.avg_ms:.2f}ms"

    def test_search_with_filters_latency(self, api_client: TestClient, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark GET /api/v1/search with filters."""
        def filtered_search() -> None:
            api_client.get("/api/v1/search?query=test&category=image&limit=10")

        result = time_function(filtered_search, iterations=30, warmup=3)
        result.name = "search_with_filters"
        benchmark_suite.add(result)
        assert result.avg_ms < 200, f"Filtered search too slow: {result.avg_ms:.2f}ms"


class TestAPIBenchmarkSummary:
    """Summary test that prints all API benchmark results."""

    def test_print_api_benchmark_summary(self, api_client: TestClient, benchmark_suite: BenchmarkSuite) -> None:
        """Run a quick pass of all benchmarks and print summary."""
        # Run a minimal set to populate the suite
        time_function(api_client.get, "/api/v1/health", iterations=10, warmup=2)
        time_function(api_client.get, "/api/v1/content", iterations=10, warmup=2)
        time_function(api_client.get, "/api/v1/listings", iterations=10, warmup=2)

        summary = benchmark_suite.to_dict()
        print("\n" + "=" * 70)
        print("API BENCHMARK SUMMARY")
        print("=" * 70)
        print(f"Total benchmarks: {len(benchmark_suite.results)}")
        for r in benchmark_suite.results:
            print(f"  {r.name}: {r.avg_ms:.2f}ms avg ({r.iterations} iterations)")
        print("=" * 70)
