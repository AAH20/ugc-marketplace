"""Cost-optimized model routing system."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class TaskType(str, Enum):
    ORCHESTRATION = "orchestration"
    CODE = "code"
    RESEARCH = "research"


@dataclass(frozen=True)
class ModelConfig:
    name: str
    tier: str  # "free", "budget", "paid"
    cost_per_input_token: float
    cost_per_output_token: float
    max_tokens: int = 4096


# Model registry — cheapest first within each tier
FREE_MODELS = [
    ModelConfig("gpt-oss-20b", "free", 0.0, 0.0),
    ModelConfig("llama-3.3-70b", "free", 0.0, 0.0),
    ModelConfig("deepseek-r1", "free", 0.0, 0.0),
]

BUDGET_MODELS = [
    ModelConfig("gemini-flash-lite", "budget", 0.0001, 0.0004),
    ModelConfig("deepseek-v4-flash", "budget", 0.00014, 0.00028),
]

PAID_MODELS = [
    ModelConfig("gpt-4o", "paid", 0.0025, 0.01),
    ModelConfig("claude-sonnet-4", "paid", 0.003, 0.015),
]

# Task type → ordered fallback chain (cheapest first)
TASK_ROUTES: dict[TaskType, list[ModelConfig]] = {
    TaskType.ORCHESTRATION: FREE_MODELS,
    TaskType.CODE: PAID_MODELS,
    TaskType.RESEARCH: BUDGET_MODELS,
}


class CostTracker:
    """Tracks token usage and cost per request."""

    def __init__(self) -> None:
        self._records: list[dict] = []

    def record(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ) -> None:
        self._records.append({
            "model": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "timestamp": time.time(),
        })

    def get_summary(self) -> dict:
        total_cost = sum(r["cost"] for r in self._records)
        total_input = sum(r["input_tokens"] for r in self._records)
        total_output = sum(r["output_tokens"] for r in self._records)
        return {
            "total_requests": len(self._records),
            "total_cost": round(total_cost, 6),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
        }

    def get_records(self) -> list[dict]:
        return list(self._records)


class ContextCache:
    """Simple in-memory cache for prompt → response."""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}
        self._enabled = True

    def get(self, key: str) -> Optional[str]:
        if not self._enabled:
            return None
        return self._cache.get(key)

    def put(self, key: str, value: str) -> None:
        if self._enabled:
            self._cache[key] = value

    def clear(self) -> None:
        self._cache.clear()

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _make_key(self, prompt: str, model_name: str) -> str:
        raw = f"{model_name}:{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()


Provider = Callable[[str, ModelConfig], str]


class ModelRouter:
    """Routes tasks to the cheapest model with fallback and cost tracking."""

    def __init__(self) -> None:
        self._provider: Optional[Provider] = None
        self._tracker: Optional[CostTracker] = None
        self._cache = ContextCache()

    def set_provider(self, provider: Provider) -> None:
        self._provider = provider

    def set_cost_tracker(self, tracker: CostTracker) -> None:
        self._tracker = tracker

    def set_cache(self, cache: ContextCache) -> None:
        self._cache = cache

    def enable_cache(self, enabled: bool) -> None:
        if enabled:
            self._cache.enable()
        else:
            self._cache.disable()

    def route(self, task_type: TaskType) -> ModelConfig:
        """Return the primary (cheapest) model for a task type."""
        chain = TASK_ROUTES.get(task_type)
        if not chain:
            raise ValueError(f"Unknown task type: {task_type}")
        return chain[0]

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate: ~4 chars per token."""
        return max(1, len(text) // 4)

    def _compute_cost(self, model: ModelConfig, input_tokens: int, output_tokens: int) -> float:
        return (
            model.cost_per_input_token * input_tokens
            + model.cost_per_output_token * output_tokens
        )

    def execute(self, prompt: str, task_type: TaskType) -> str:
        """Execute a prompt through the routing chain with fallback."""
        if self._provider is None:
            raise RuntimeError("No provider configured")

        chain = TASK_ROUTES.get(task_type)
        if not chain:
            raise ValueError(f"Unknown task type: {task_type}")

        # Check cache first
        cache_key = self._cache._make_key(prompt, chain[0].name)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        last_error: Optional[Exception] = None
        for model in chain:
            try:
                response = self._provider(prompt, model)

                # Track cost
                if self._tracker:
                    input_tokens = self._estimate_tokens(prompt)
                    output_tokens = self._estimate_tokens(response)
                    cost = self._compute_cost(model, input_tokens, output_tokens)
                    self._tracker.record(model.name, input_tokens, output_tokens, cost)

                # Cache the response
                self._cache.put(cache_key, response)
                return response

            except Exception as e:
                last_error = e
                continue

        raise Exception(f"All models failed: {last_error}")
