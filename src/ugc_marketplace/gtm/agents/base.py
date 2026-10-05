"""Base GTM agent with common functionality."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from ugc_marketplace.config import get_settings

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class AgentResult(BaseModel, Generic[T]):
    """Generic agent result wrapper."""

    success: bool = True
    data: T | None = None
    error: str | None = None
    reasoning: str = ""
    execution_time_ms: float = 0.0


class BaseGTMAgent(ABC, Generic[T]):
    """Abstract base class for GTM agents.

    Provides common functionality for LLM initialization, execution timing,
    and result construction. Subclasses must implement the _execute method.
    """

    def __init__(self, model: BaseChatModel | None = None) -> None:
        """Initialize the GTM agent.

        Args:
            model: Optional pre-configured chat model. If not provided,
                   creates a default OpenAI model from settings.
        """
        self.settings = get_settings()
        self._model = model
        self._trace: dict[str, Any] = {}

    @property
    def model(self) -> BaseChatModel:
        """Lazy-initialize the language model.

        Returns:
            The configured language model instance.
        """
        if self._model is None:
            self._model = ChatOpenAI(
                model=self.settings.llm_model,
                temperature=self.settings.llm_temperature,
                api_key=self.settings.openai_api_key or None,
            )
        return self._model

    @abstractmethod
    async def _execute(self, input_data: T) -> dict[str, Any]:
        """Execute the agent's primary task.

        Args:
            input_data: Input data for the agent task.

        Returns:
            Execution result dictionary.
        """
        ...

    async def execute(self, input_data: T) -> AgentResult[dict[str, Any]]:
        """Execute the agent and return structured result.

        Args:
            input_data: Input data for the agent task.

        Returns:
            Structured agent result.
        """
        start_time = time.monotonic()

        logger.info(
            "Starting GTM agent execution",
            agent=self.__class__.__name__,
        )

        try:
            result = await self._execute(input_data)
            processing_time = (time.monotonic() - start_time) * 1000

            logger.info(
                "GTM agent execution complete",
                agent=self.__class__.__name__,
                processing_time_ms=processing_time,
            )

            return AgentResult(
                success=True,
                data=result,
                execution_time_ms=processing_time,
            )

        except Exception as exc:
            processing_time = (time.monotonic() - start_time) * 1000
            logger.error(
                "GTM agent execution failed",
                agent=self.__class__.__name__,
                error=str(exc),
                processing_time_ms=processing_time,
            )
            return AgentResult(
                success=False,
                error=str(exc),
                execution_time_ms=processing_time,
            )
