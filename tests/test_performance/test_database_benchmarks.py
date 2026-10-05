"""Database query performance benchmarks for UGC Marketplace.

Measures query execution time for:
- Content service operations
- Listing service operations
- Search service operations
- Database manager operations
"""

from __future__ import annotations

import pytest

from tests.test_performance.conftest import BenchmarkSuite, time_function


class TestContentServiceBenchmarks:
    """Benchmark content service operations."""

    def test_create_content_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark content creation speed."""
        from ugc_marketplace.services.content_service import create_content

        def create_item() -> None:
            create_content({
                "title": "Benchmark Content",
                "description": "Description for benchmark content. " * 3,
                "content_type": "image",
                "creator_id": "creator_bench",
                "tags": ["benchmark", "test"],
            })

        result = time_function(create_item, iterations=100, warmup=10)
        result.name = "content_service_create"
        benchmark_suite.add(result)
        assert result.avg_ms < 10, f"Content creation too slow: {result.avg_ms:.2f}ms"

    def test_list_content_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark content listing with filters."""
        from ugc_marketplace.services.content_service import (
            ContentFilters,
            ContentType,
            PaginationParams,
            list_content,
        )

        # Pre-populate with some content
        from ugc_marketplace.services.content_service import create_content
        for i in range(50):
            create_content({
                "title": f"List Test Content {i}",
                "description": f"Description {i}",
                "content_type": "image" if i % 2 == 0 else "video",
                "creator_id": f"creator_{i % 5}",
            })

        def list_items() -> None:
            list_content(
                filters=ContentFilters(content_type=ContentType.IMAGE),
                pagination=PaginationParams(page=1, page_size=20),
            )

        result = time_function(list_items, iterations=50, warmup=5)
        result.name = "content_service_list_filtered"
        benchmark_suite.add(result)
        assert result.avg_ms < 50, f"Content listing too slow: {result.avg_ms:.2f}ms"

    def test_list_content_with_search_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark content listing with search query."""
        from ugc_marketplace.services.content_service import (
            ContentFilters,
            PaginationParams,
            list_content,
        )

        def search_items() -> None:
            list_content(
                filters=ContentFilters(search_query="test"),
                pagination=PaginationParams(page=1, page_size=20),
            )

        result = time_function(search_items, iterations=30, warmup=3)
        result.name = "content_service_search"
        benchmark_suite.add(result)
        assert result.avg_ms < 100, f"Content search too slow: {result.avg_ms:.2f}ms"

    def test_update_content_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark content update speed."""
        from ugc_marketplace.services.content_service import create_content, update_content

        content = create_content({
            "title": "Update Test",
            "description": "Original description",
            "content_type": "text",
            "creator_id": "creator_update",
        })

        def update_item() -> None:
            update_content(content.id, {"title": "Updated Title"})

        result = time_function(update_item, iterations=50, warmup=5)
        result.name = "content_service_update"
        benchmark_suite.add(result)
        assert result.avg_ms < 10, f"Content update too slow: {result.avg_ms:.2f}ms"

    def test_delete_content_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark content deletion speed."""
        from ugc_marketplace.services.content_service import create_content, delete_content

        def create_and_delete() -> None:
            content = create_content({
                "title": "Delete Test",
                "description": "To be deleted",
                "content_type": "text",
                "creator_id": "creator_delete",
            })
            delete_content(content.id)

        result = time_function(create_and_delete, iterations=50, warmup=5)
        result.name = "content_service_delete"
        benchmark_suite.add(result)
        assert result.avg_ms < 20, f"Content deletion too slow: {result.avg_ms:.2f}ms"


class TestListingServiceBenchmarks:
    """Benchmark listing service operations."""

    def test_create_listing_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark listing creation speed."""
        from ugc_marketplace.services.listing_service import create_listing

        def create_item() -> None:
            create_listing({
                "seller_id": "seller_bench",
                "title": "Benchmark Listing",
                "description": "Description for listing. " * 5,
                "category": "digital_art",
                "price": {"amount_cents": 4999, "currency": "USD"},
                "tags": ["benchmark", "digital"],
            })

        result = time_function(create_item, iterations=50, warmup=5)
        result.name = "listing_service_create"
        benchmark_suite.add(result)
        assert result.avg_ms < 10, f"Listing creation too slow: {result.avg_ms:.2f}ms"

    def test_search_listings_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark listing search speed."""
        from ugc_marketplace.services.listing_service import list_listings

        def search_listings() -> None:
            list_listings(filters={"category": "digital_art"}, page=1, page_size=20)

        result = time_function(search_listings, iterations=30, warmup=3)
        result.name = "listing_service_search"
        benchmark_suite.add(result)
        assert result.avg_ms < 50, f"Listing search too slow: {result.avg_ms:.2f}ms"

    def test_get_listing_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark single listing retrieval speed."""
        from ugc_marketplace.services.listing_service import create_listing, get_listing

        listing = create_listing({
            "seller_id": "seller_bench",
            "title": "Get Benchmark Listing",
            "description": "Description for get benchmark. " * 5,
            "category": "photography",
            "price": {"amount_cents": 2999, "currency": "USD"},
        })

        result = time_function(get_listing, listing.id, iterations=50, warmup=5)
        result.name = "listing_service_get"
        benchmark_suite.add(result)
        assert result.avg_ms < 10, f"Get listing too slow: {result.avg_ms:.2f}ms"


class TestSearchServiceBenchmarks:
    """Benchmark search service operations."""

    def test_search_content_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark content search speed."""
        from ugc_marketplace.services.search_service import SearchFilters, search_content

        def do_search() -> None:
            search_content("test query", filters=SearchFilters(limit=20))

        result = time_function(do_search, iterations=30, warmup=3)
        result.name = "search_service_content"
        benchmark_suite.add(result)
        assert result.avg_ms < 50, f"Search content too slow: {result.avg_ms:.2f}ms"

    def test_search_creators_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark creator search speed."""
        from ugc_marketplace.services.search_service import search_creators

        def do_search() -> None:
            search_creators("test creator")

        result = time_function(do_search, iterations=30, warmup=3)
        result.name = "search_service_creators"
        benchmark_suite.add(result)
        assert result.avg_ms < 50, f"Search creators too slow: {result.avg_ms:.2f}ms"

    def test_search_suggestions_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark search suggestions speed."""
        from ugc_marketplace.services.search_service import get_search_suggestions

        def get_suggestions() -> None:
            get_search_suggestions("test")

        result = time_function(get_suggestions, iterations=30, warmup=3)
        result.name = "search_service_suggestions"
        benchmark_suite.add(result)
        assert result.avg_ms < 50, f"Search suggestions too slow: {result.avg_ms:.2f}ms"


class TestDatabaseManagerBenchmarks:
    """Benchmark database manager operations."""

    def test_database_manager_initialization(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark DatabaseManager initialization time."""
        from ugc_marketplace.database.manager import DatabaseManager

        def create_manager() -> None:
            # Just test initialization, don't connect
            manager = DatabaseManager.__new__(DatabaseManager)
            manager.pool_size = 20
            manager.max_overflow = 10
            manager.pool_timeout = 30
            manager.pool_recycle = 3600
            manager.query_timeout = 30
            manager.max_retries = 5
            manager.retry_delay = 0.1
            manager.retry_max_delay = 30.0
            manager.retry_jitter = 0.2
            manager.slow_query_threshold_ms = 100
            manager.query_metrics = {}

        result = time_function(create_manager, iterations=100, warmup=10)
        result.name = "db_manager_init"
        benchmark_suite.add(result)
        assert result.avg_ms < 5, f"DB manager init too slow: {result.avg_ms:.2f}ms"

    def test_query_metrics_collection(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark query metrics collection overhead."""
        from ugc_marketplace.database.manager import DatabaseManager

        manager = DatabaseManager.__new__(DatabaseManager)
        manager.query_metrics = {}
        manager.slow_query_threshold_ms = 100

        # Simulate recording metrics
        for i in range(10):
            query_key = f"SELECT * FROM test WHERE id = {i}"
            manager.query_metrics.setdefault(query_key, []).append(150.0 + i)

        def get_metrics() -> None:
            metrics = {}
            for query, durations in manager.query_metrics.items():
                if durations:
                    metrics[query] = {
                        "count": len(durations),
                        "avg_ms": round(sum(durations) / len(durations), 2),
                        "max_ms": round(max(durations), 2),
                    }

        result = time_function(get_metrics, iterations=100, warmup=10)
        result.name = "db_metrics_collection"
        benchmark_suite.add(result)
        assert result.avg_ms < 5, f"Metrics collection too slow: {result.avg_ms:.2f}ms"


class TestDatabaseBenchmarkSummary:
    """Summary test that prints all database benchmark results."""

    def test_print_db_benchmark_summary(self, benchmark_suite: BenchmarkSuite) -> None:
        """Print summary of database benchmarks."""
        print("\n" + "=" * 70)
        print("DATABASE BENCHMARK SUMMARY")
        print("=" * 70)
        print(f"Total benchmarks: {len(benchmark_suite.results)}")
        for r in benchmark_suite.results:
            print(f"  {r.name}: {r.avg_ms:.2f}ms avg ({r.iterations} iterations)")
        print("=" * 70)
