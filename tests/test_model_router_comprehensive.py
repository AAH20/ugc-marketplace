"""Comprehensive tests for the model routing system."""
import pytest
from model_router import (
    CostTracker,
    ContextCache,
    ModelConfig,
    ModelRouter,
    TaskType,
    FREE_MODELS,
    BUDGET_MODELS,
    PAID_MODELS,
    TASK_ROUTES,
)


class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_model_config_creation(self):
        """ModelConfig can be created with all fields."""
        config = ModelConfig("test-model", "free", 0.0, 0.0, max_tokens=4096)
        assert config.name == "test-model"
        assert config.tier == "free"
        assert config.cost_per_input_token == 0.0
        assert config.cost_per_output_token == 0.0
        assert config.max_tokens == 4096

    def test_model_config_default_max_tokens(self):
        """ModelConfig has default max_tokens."""
        config = ModelConfig("test", "free", 0.0, 0.0)
        assert config.max_tokens == 4096

    def test_model_config_frozen(self):
        """ModelConfig is frozen (immutable)."""
        config = ModelConfig("test", "free", 0.0, 0.0)
        with pytest.raises(AttributeError):
            config.name = "new-name"


class TestModelRegistry:
    """Tests for model registry constants."""

    def test_free_models_exist(self):
        """Free models are defined."""
        assert len(FREE_MODELS) > 0
        for model in FREE_MODELS:
            assert model.tier == "free"
            assert model.cost_per_input_token == 0.0
            assert model.cost_per_output_token == 0.0

    def test_budget_models_exist(self):
        """Budget models are defined."""
        assert len(BUDGET_MODELS) > 0
        for model in BUDGET_MODELS:
            assert model.tier == "budget"
            assert model.cost_per_input_token > 0

    def test_paid_models_exist(self):
        """Paid models are defined."""
        assert len(PAID_MODELS) > 0
        for model in PAID_MODELS:
            assert model.tier == "paid"
            assert model.cost_per_input_token > 0

    def test_task_routes_cover_all_types(self):
        """All task types have routes."""
        for task_type in TaskType:
            assert task_type in TASK_ROUTES
            assert len(TASK_ROUTES[task_type]) > 0

    def test_orchestration_uses_free_models(self):
        """Orchestration uses free models."""
        for model in TASK_ROUTES[TaskType.ORCHESTRATION]:
            assert model.tier == "free"

    def test_code_uses_paid_models(self):
        """Code uses paid models."""
        for model in TASK_ROUTES[TaskType.CODE]:
            assert model.tier == "paid"

    def test_research_uses_budget_models(self):
        """Research uses budget models."""
        for model in TASK_ROUTES[TaskType.RESEARCH]:
            assert model.tier == "budget"


class TestModelRouterSelection:
    """Tests for model selection logic."""

    def test_route_orchestration(self):
        """Orchestration routes to cheapest free model."""
        router = ModelRouter()
        model = router.route(TaskType.ORCHESTRATION)
        assert model.tier == "free"
        assert model.cost_per_input_token == 0.0

    def test_route_code(self):
        """Code routes to cheapest paid model."""
        router = ModelRouter()
        model = router.route(TaskType.CODE)
        assert model.tier == "paid"

    def test_route_research(self):
        """Research routes to cheapest budget model."""
        router = ModelRouter()
        model = router.route(TaskType.RESEARCH)
        assert model.tier == "budget"

    def test_route_unknown_task_type(self):
        """Unknown task type raises ValueError."""
        router = ModelRouter()
        with pytest.raises(ValueError, match="Unknown task type"):
            router.route("unknown")

    def test_route_returns_first_in_chain(self):
        """Route returns the first (cheapest) model in chain."""
        router = ModelRouter()
        model = router.route(TaskType.ORCHESTRATION)
        assert model == TASK_ROUTES[TaskType.ORCHESTRATION][0]


class TestModelRouterExecution:
    """Tests for model execution with fallback."""

    def test_execute_success(self):
        """Execute returns provider response."""
        router = ModelRouter()
        router.set_provider(lambda prompt, model: "response")
        result = router.execute("test", TaskType.ORCHESTRATION)
        assert result == "response"

    def test_execute_no_provider(self):
        """Execute raises RuntimeError when no provider set."""
        router = ModelRouter()
        with pytest.raises(RuntimeError, match="No provider configured"):
            router.execute("test", TaskType.ORCHESTRATION)

    def test_execute_unknown_task_type(self):
        """Execute raises ValueError for unknown task type."""
        router = ModelRouter()
        router.set_provider(lambda prompt, model: "response")
        with pytest.raises(ValueError, match="Unknown task type"):
            router.execute("test", "unknown")

    def test_fallback_on_failure(self):
        """Fallback to next model when primary fails."""
        router = ModelRouter()
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

    def test_fallback_chain_exhausted(self):
        """Raises when all models in chain fail."""
        router = ModelRouter()

        def always_fail(prompt, model):
            raise Exception("All models down")

        router.set_provider(always_fail)
        with pytest.raises(Exception, match="All models down"):
            router.execute("test", TaskType.ORCHESTRATION)

    def test_fallback_tries_models_in_order(self):
        """Fallback tries models in chain order."""
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

    def test_fallback_with_cost_tracking(self):
        """Cost is tracked for successful fallback."""
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


class TestCostTracker:
    """Tests for CostTracker."""

    def test_record_single_request(self):
        """Record a single request."""
        tracker = CostTracker()
        tracker.record("gpt-4o", 100, 50, 0.005)
        summary = tracker.get_summary()
        assert summary["total_requests"] == 1
        assert summary["total_cost"] == 0.005
        assert summary["total_input_tokens"] == 100
        assert summary["total_output_tokens"] == 50

    def test_record_multiple_requests(self):
        """Record multiple requests."""
        tracker = CostTracker()
        tracker.record("gpt-4o", 100, 50, 0.005)
        tracker.record("gpt-4o", 200, 100, 0.01)
        summary = tracker.get_summary()
        assert summary["total_requests"] == 2
        assert summary["total_cost"] == 0.015
        assert summary["total_input_tokens"] == 300
        assert summary["total_output_tokens"] == 150

    def test_get_records(self):
        """Get all records."""
        tracker = CostTracker()
        tracker.record("gpt-4o", 100, 50, 0.005)
        records = tracker.get_records()
        assert len(records) == 1
        assert records[0]["model"] == "gpt-4o"
        assert records[0]["input_tokens"] == 100

    def test_empty_tracker(self):
        """Empty tracker returns zero summary."""
        tracker = CostTracker()
        summary = tracker.get_summary()
        assert summary["total_requests"] == 0
        assert summary["total_cost"] == 0.0
        assert summary["total_input_tokens"] == 0
        assert summary["total_output_tokens"] == 0

    def test_cost_rounding(self):
        """Cost is rounded to 6 decimal places."""
        tracker = CostTracker()
        tracker.record("gpt-4o", 100, 50, 0.0000001)
        summary = tracker.get_summary()
        assert summary["total_cost"] == 0.0


class TestContextCache:
    """Tests for ContextCache."""

    def test_put_and_get(self):
        """Put and get a cached value."""
        cache = ContextCache()
        cache.put("key", "value")
        assert cache.get("key") == "value"

    def test_get_missing_key(self):
        """Get returns None for missing key."""
        cache = ContextCache()
        assert cache.get("missing") is None

    def test_clear(self):
        """Clear removes all entries."""
        cache = ContextCache()
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_disable(self):
        """Disabled cache returns None."""
        cache = ContextCache()
        cache.put("key", "value")
        cache.disable()
        assert cache.get("key") is None

    def test_enable(self):
        """Enabled cache returns values."""
        cache = ContextCache()
        cache.put("key", "value")
        cache.disable()
        cache.enable()
        assert cache.get("key") == "value"

    def test_enabled_property(self):
        """Enabled property reflects state."""
        cache = ContextCache()
        assert cache.enabled is True
        cache.disable()
        assert cache.enabled is False
        cache.enable()
        assert cache.enabled is True

    def test_put_when_disabled(self):
        """Put does nothing when disabled."""
        cache = ContextCache()
        cache.disable()
        cache.put("key", "value")
        assert cache.get("key") is None

    def test_make_key_deterministic(self):
        """Same prompt and model produce same key."""
        cache = ContextCache()
        key1 = cache._make_key("prompt", "model")
        key2 = cache._make_key("prompt", "model")
        assert key1 == key2

    def test_make_key_different_prompts(self):
        """Different prompts produce different keys."""
        cache = ContextCache()
        key1 = cache._make_key("prompt1", "model")
        key2 = cache._make_key("prompt2", "model")
        assert key1 != key2

    def test_make_key_different_models(self):
        """Different models produce different keys."""
        cache = ContextCache()
        key1 = cache._make_key("prompt", "model1")
        key2 = cache._make_key("prompt", "model2")
        assert key1 != key2


class TestRouterIntegration:
    """Integration tests for the full routing pipeline."""

    def test_full_pipeline_with_caching(self):
        """Full pipeline with caching and cost tracking."""
        router = ModelRouter()
        tracker = CostTracker()
        cache = ContextCache()
        router.set_cost_tracker(tracker)
        router.set_cache(cache)

        def mock_provider(prompt, model):
            return f"processed: {prompt}"

        router.set_provider(mock_provider)
        r1 = router.execute("hello", TaskType.ORCHESTRATION)
        assert r1 == "processed: hello"
        r2 = router.execute("hello", TaskType.ORCHESTRATION)
        assert r2 == "processed: hello"
        summary = tracker.get_summary()
        assert summary["total_requests"] == 1

    def test_cache_hit_avoids_provider_call(self):
        """Cache hit avoids calling provider."""
        router = ModelRouter()
        cache = ContextCache()
        router.set_cache(cache)
        call_count = 0

        def counting_provider(prompt, model):
            nonlocal call_count
            call_count += 1
            return f"response-{call_count}"

        router.set_provider(counting_provider)
        router.execute("same prompt", TaskType.ORCHESTRATION)
        router.execute("same prompt", TaskType.ORCHESTRATION)
        assert call_count == 1

    def test_different_task_types_different_models(self):
        """Different task types use different models."""
        router = ModelRouter()
        models_used = []

        def tracking_provider(prompt, model):
            models_used.append(model.name)
            return "response"

        router.set_provider(tracking_provider)
        router.execute("test", TaskType.ORCHESTRATION)
        router.execute("test", TaskType.CODE)
        router.execute("test", TaskType.RESEARCH)
        assert len(models_used) == 3
        assert models_used[0] != models_used[1] != models_used[2]

    def test_cost_tracking_with_free_models(self):
        """Free models have zero cost."""
        router = ModelRouter()
        tracker = CostTracker()
        router.set_cost_tracker(tracker)
        router.set_provider(lambda prompt, model: "response")
        router.execute("test", TaskType.ORCHESTRATION)
        summary = tracker.get_summary()
        assert summary["total_cost"] == 0.0

    def test_cost_tracking_with_paid_models(self):
        """Paid models have non-zero cost."""
        router = ModelRouter()
        tracker = CostTracker()
        router.set_cost_tracker(tracker)
        router.set_provider(lambda prompt, model: "response")
        router.execute("test", TaskType.CODE)
        summary = tracker.get_summary()
        assert summary["total_cost"] > 0

    def test_estimate_tokens_empty_string(self):
        """Empty string estimates to 1 token."""
        router = ModelRouter()
        assert router._estimate_tokens("") == 1

    def test_estimate_tokens_short_text(self):
        """Short text estimates correctly."""
        router = ModelRouter()
        assert router._estimate_tokens("hello") == 1

    def test_estimate_tokens_long_text(self):
        """Long text estimates correctly."""
        router = ModelRouter()
        text = "a" * 400
        assert router._estimate_tokens(text) == 100

    def test_compute_cost_zero(self):
        """Zero tokens means zero cost."""
        router = ModelRouter()
        model = ModelConfig("test", "free", 0.0, 0.0)
        assert router._compute_cost(model, 0, 0) == 0.0

    def test_compute_cost_nonzero(self):
        """Non-zero tokens produce non-zero cost."""
        router = ModelRouter()
        model = ModelConfig("test", "paid", 0.0025, 0.01)
        cost = router._compute_cost(model, 100, 50)
        assert cost > 0
