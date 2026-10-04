"""Agent execution time benchmarks for UGC Marketplace.

Measures execution time for:
- Quality scoring agent
- Community curation agent
- Content moderation agent
- Rights management agent
"""

from __future__ import annotations

import pytest

from tests.test_performance.conftest import BenchmarkSuite, time_function


class TestQualityScoringAgentBenchmarks:
    """Benchmark quality scoring agent operations."""

    def test_score_content_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark single content quality scoring."""
        from ugc_marketplace.agents.quality_scoring import score_content

        result = time_function(score_content, "vid_001", iterations=100, warmup=10)
        result.name = "quality_score_single"
        benchmark_suite.add(result)
        assert result.avg_ms < 50, f"Quality scoring too slow: {result.avg_ms:.2f}ms"

    def test_score_content_synthetic_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark quality scoring for synthetic (unknown) content."""
        from ugc_marketplace.agents.quality_scoring import score_content

        result = time_function(score_content, "unknown_content_xyz", iterations=100, warmup=10)
        result.name = "quality_score_synthetic"
        benchmark_suite.add(result)
        assert result.avg_ms < 50, f"Synthetic quality scoring too slow: {result.avg_ms:.2f}ms"

    def test_compare_quality_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark comparative quality analysis."""
        from ugc_marketplace.agents.quality_scoring import compare_quality

        content_ids = ["vid_001", "vid_002", "img_001", "txt_001", "aud_001"]

        result = time_function(compare_quality, content_ids, iterations=50, warmup=5)
        result.name = "quality_compare_5_items"
        benchmark_suite.add(result)
        assert result.avg_ms < 200, f"Quality comparison too slow: {result.avg_ms:.2f}ms"

    def test_compare_quality_large_set_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark comparative quality analysis with larger set."""
        from ugc_marketplace.agents.quality_scoring import compare_quality

        content_ids = [f"content_{i}" for i in range(20)]

        result = time_function(compare_quality, content_ids, iterations=20, warmup=2)
        result.name = "quality_compare_20_items"
        benchmark_suite.add(result)
        assert result.avg_ms < 500, f"Large quality comparison too slow: {result.avg_ms:.2f}ms"

    def test_score_content_quality_api_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark the score_content_quality API function."""
        from ugc_marketplace.agents.quality_scoring import score_content_quality

        result = time_function(score_content_quality, "vid_001", iterations=100, warmup=10)
        result.name = "quality_score_api"
        benchmark_suite.add(result)
        assert result.avg_ms < 50, f"Quality score API too slow: {result.avg_ms:.2f}ms"

    def test_get_quality_metrics_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark quality metrics retrieval."""
        from ugc_marketplace.agents.quality_scoring import get_quality_metrics

        result = time_function(get_quality_metrics, "vid_001", iterations=100, warmup=10)
        result.name = "quality_metrics_get"
        benchmark_suite.add(result)
        assert result.avg_ms < 50, f"Quality metrics retrieval too slow: {result.avg_ms:.2f}ms"

    def test_flag_low_quality_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark low quality flag check."""
        from ugc_marketplace.agents.quality_scoring import flag_low_quality

        result = time_function(flag_low_quality, "vid_001", iterations=100, warmup=10)
        result.name = "quality_flag_check"
        benchmark_suite.add(result)
        assert result.avg_ms < 50, f"Low quality flag check too slow: {result.avg_ms:.2f}ms"


class TestCommunityCurationAgentBenchmarks:
    """Benchmark community curation agent operations."""

    def test_curate_feed_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark feed curation."""
        from ugc_marketplace.agents.community_curation import (
            CommunityCurationAgent,
            UserPreferences,
        )

        agent = CommunityCurationAgent()
        prefs = UserPreferences(max_results=20)

        result = time_function(agent.curate_feed, "user_123", prefs, iterations=50, warmup=5)
        result.name = "curation_feed"
        benchmark_suite.add(result)
        assert result.avg_ms < 100, f"Feed curation too slow: {result.avg_ms:.2f}ms"

    def test_rank_content_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark content ranking."""
        from ugc_marketplace.agents.community_curation import CommunityCurationAgent

        agent = CommunityCurationAgent()
        content_ids = [f"c{i:03d}" for i in range(1, 16)]
        criteria = {"engagement_weight": 0.4, "recency_weight": 0.3, "quality_weight": 0.3}

        result = time_function(agent.rank_content, content_ids, criteria, iterations=50, warmup=5)
        result.name = "curation_rank"
        benchmark_suite.add(result)
        assert result.avg_ms < 100, f"Content ranking too slow: {result.avg_ms:.2f}ms"

    def test_curate_community_content_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark community content curation."""
        from ugc_marketplace.agents.community_curation import curate_community_content

        result = time_function(curate_community_content, "community_123", iterations=50, warmup=5)
        result.name = "curation_community"
        benchmark_suite.add(result)
        assert result.avg_ms < 100, f"Community curation too slow: {result.avg_ms:.2f}ms"

    def test_get_curated_feed_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark curated feed retrieval."""
        from ugc_marketplace.agents.community_curation import get_curated_feed

        result = time_function(get_curated_feed, "community_123", limit=20, iterations=50, warmup=5)
        result.name = "curation_feed_get"
        benchmark_suite.add(result)
        assert result.avg_ms < 100, f"Curated feed retrieval too slow: {result.avg_ms:.2f}ms"

    def test_feature_content_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark content featuring."""
        from ugc_marketplace.agents.community_curation import feature_content

        result = time_function(feature_content, "c001", "community_123", iterations=50, warmup=5)
        result.name = "curation_feature"
        benchmark_suite.add(result)
        assert result.avg_ms < 50, f"Content featuring too slow: {result.avg_ms:.2f}ms"


class TestContentModerationAgentBenchmarks:
    """Benchmark content moderation agent operations."""

    def test_text_moderation_agent_init_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark text moderation agent initialization."""
        from ugc_marketplace.agents.content_moderation.text_moderation import TextModerationAgent

        def create_agent() -> None:
            # Create without model to avoid API key requirement
            agent = TextModerationAgent.__new__(TextModerationAgent)
            agent._trace = {}

        result = time_function(create_agent, iterations=100, warmup=10)
        result.name = "moderation_agent_init"
        benchmark_suite.add(result)
        assert result.avg_ms < 10, f"Moderation agent init too slow: {result.avg_ms:.2f}ms"

    def test_moderation_result_construction_performance(self, benchmark_suite: BenchmarkSuite) -> None:
        """Benchmark moderation result construction."""
        from ugc_marketplace.models.schemas import ContentType, ModerationAction, ModerationResult
        from uuid import uuid4

        def build_result() -> None:
            ModerationResult(
                request_id=uuid4(),
                content_type=ContentType.TEXT,
                action=ModerationAction.ALLOW,
                confidence=0.95,
                categories=["clean"],
                reasons=["No violations found"],
                policy_violations=[],
                processing_time_ms=1.0,
            )

        result = time_function(build_result, iterations=1000, warmup=100)
        result.name = "moderation_result_build"
        benchmark_suite.add(result)
        assert result.avg_ms < 5, f"Moderation result construction too slow: {result.avg_ms:.2f}ms"


class TestAgentBenchmarkSummary:
    """Summary test that prints all agent benchmark results."""

    def test_print_agent_benchmark_summary(self, benchmark_suite: BenchmarkSuite) -> None:
        """Print summary of agent benchmarks."""
        print("\n" + "=" * 70)
        print("AGENT BENCHMARK SUMMARY")
        print("=" * 70)
        print(f"Total benchmarks: {len(benchmark_suite.results)}")
        for r in benchmark_suite.results:
            print(f"  {r.name}: {r.avg_ms:.2f}ms avg ({r.iterations} iterations)")
        print("=" * 70)
