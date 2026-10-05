"""Integration tests for the model routing system."""
import pytest

from app import models  # noqa: F401
from app.main import app  # noqa: F401
from src.model_router import (
    CostTracker,
    ContextCache,
    ModelConfig,
    ModelRouter,
    TaskType,
)


class TestModelSelection:
    """Router selects the cheapest model for each task type."""

    def test_orchestration_selects_free_model(self):
        router = ModelRouter()
        model = router.route(TaskType.ORCHESTRATION)
        assert model.tier == "free"
        assert model.cost_per_input_token == 0.0
        assert model.cost_per_output_token == 0.0

    def test_code_selects_paid_model(self):
        router = ModelRouter()
        model = router.route(TaskType.CODE)
        assert model.tier == "paid"
        assert model.cost_per_input_token > 0

    def test_research_selects_budget_model(self):
        router = ModelRouter()
        model = router.route(TaskType.RESEARCH)
        assert model.tier == "budget"
        assert 0 < model.cost_per_input_token < 0.001

    def test_orchestration_prefers_cheapest_free_model(self):
        router = ModelRouter()
        model = router.route(TaskType.ORCHESTRATION)
        # All free models cost 0, so any is acceptable
        assert model.cost_per_input_token == 0.0


class TestFallbackChain:
    """Fallback chain activates when primary model fails."""

    def test_fallback_on_failure(self):
        router = ModelRouter()
        # Force primary to fail by using a model that doesn't exist
        calls = []

        def failing_provider(prompt, model):
            calls.append(model.name)
            if model.name == "gpt-oss-20b":
                raise Exception("Model unavailable")
            return f"response from {model.name}"

        router.set_provider(failing_provider)
        result = router.execute("test prompt", TaskType.ORCHESTRATION)
        assert result == "response from llama-3.3-70b"
        assert len(calls) == 2

    def test_fallback_chain_exhausted_raises(self):
        router = ModelRouter()

        def always_fail(prompt, model):
            raise Exception("All models down")

        router.set_provider(always_fail)
        with pytest.raises(Exception, match="All models down"):
            router.execute("test", TaskType.ORCHESTRATION)

    def test_fallback_tries_models_in_order(self):
        router = ModelRouter()
        attempted = []

        def track_attempts(prompt, model):
            attempted.append(model.name)
            if len(attempted) < 3:
                raise Exception("fail")
            return "success"

        router.set_provider(track_attempts)
        result = router.execute("test", TaskType.ORCHESTRATION)
        assert result == "success"
        assert len(attempted) == 3


class TestCostTracking:
    """Cost is tracked per request."""

    def test_cost_tracked_for_request(self):
        router = ModelRouter()
        tracker = CostTracker()
        router.set_cost_tracker(tracker)

        def mock_provider(prompt, model):
            return "response"

        router.set_provider(mock_provider)
        router.execute("test prompt", TaskType.RESEARCH)

        summary = tracker.get_summary()
        assert summary["total_requests"] == 1
        assert summary["total_cost"] > 0

    def test_cost_zero_for_free_models(self):
        router = ModelRouter()
        tracker = CostTracker()
        router.set_cost_tracker(tracker)

        def mock_provider(prompt, model):
            return "response"

        router.set_provider(mock_provider)
        router.execute("test", TaskType.ORCHESTRATION)

        summary = tracker.get_summary()
        assert summary["total_cost"] == 0.0

    def test_multiple_requests_accumulate_cost(self):
        router = ModelRouter()
        tracker = CostTracker()
        router.set_cost_tracker(tracker)

        def mock_provider(prompt, model):
            return "response"

        router.set_provider(mock_provider)
        router.execute("test1", TaskType.RESEARCH)
        router.execute("test2", TaskType.RESEARCH)
        router.execute("test3", TaskType.RESEARCH)

        summary = tracker.get_summary()
        assert summary["total_requests"] == 3
        assert summary["total_cost"] > 0


class TestContextCaching:
    """Repeated prompts are cached to avoid redundant API calls."""

    def test_cached_prompt_not_fetched_again(self):
        router = ModelRouter()
        cache = ContextCache()
        router.set_cache(cache)

        call_count = 0

        def counting_provider(prompt, model):
            nonlocal call_count
            call_count += 1
            return f"response-{call_count}"

        router.set_provider(counting_provider)
        result1 = router.execute("same prompt", TaskType.ORCHESTRATION)
        result2 = router.execute("same prompt", TaskType.ORCHESTRATION)

        assert result1 == result2
        assert call_count == 1

    def test_different_prompts_not_cached(self):
        router = ModelRouter()
        cache = ContextCache()
        router.set_cache(cache)

        call_count = 0

        def counting_provider(prompt, model):
            nonlocal call_count
            call_count += 1
            return f"response-{call_count}"

        router.set_provider(counting_provider)
        router.execute("prompt A", TaskType.ORCHESTRATION)
        router.execute("prompt B", TaskType.ORCHESTRATION)

        assert call_count == 2

    def test_cache_can_be_disabled(self):
        router = ModelRouter()
        cache = ContextCache()
        router.set_cache(cache)
        router.enable_cache(False)

        call_count = 0

        def counting_provider(prompt, model):
            nonlocal call_count
            call_count += 1
            return f"response-{call_count}"

        router.set_provider(counting_provider)
        router.execute("same prompt", TaskType.ORCHESTRATION)
        router.execute("same prompt", TaskType.ORCHESTRATION)

        assert call_count == 2


class TestIntegration:
    """End-to-end integration tests."""

    def test_full_pipeline_with_caching_and_cost(self):
        router = ModelRouter()
        tracker = CostTracker()
        cache = ContextCache()
        router.set_cost_tracker(tracker)
        router.set_cache(cache)

        def mock_provider(prompt, model):
            return f"processed: {prompt}"

        router.set_provider(mock_provider)

        # First call hits the model
        r1 = router.execute("hello", TaskType.ORCHESTRATION)
        assert r1 == "processed: hello"

        # Second call is cached
        r2 = router.execute("hello", TaskType.ORCHESTRATION)
        assert r2 == "processed: hello"

        summary = tracker.get_summary()
        assert summary["total_requests"] == 1  # cached request not counted

    def test_fallback_with_cost_tracking(self):
        router = ModelRouter()
        tracker = CostTracker()
        router.set_cost_tracker(tracker)

        attempt = 0

        def flaky_provider(prompt, model):
            nonlocal attempt
            attempt += 1
            if attempt == 1:
                raise Exception("Primary failed")
            return "fallback response"

        router.set_provider(flaky_provider)
        result = router.execute("test", TaskType.CODE)
        assert result == "fallback response"

        summary = tracker.get_summary()
        assert summary["total_requests"] == 1

    def test_research_uses_budget_tier(self):
        router = ModelRouter()
        tracker = CostTracker()
        router.set_cost_tracker(tracker)

        def mock_provider(prompt, model):
            return "research result"

        router.set_provider(mock_provider)
        router.execute("research query", TaskType.RESEARCH)

        summary = tracker.get_summary()
        assert summary["total_cost"] > 0
        assert summary["total_cost"] < 0.01  # budget tier is cheap
