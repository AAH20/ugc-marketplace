"""Multi-provider routing with fallback for video generation."""
import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    """Health status of a provider."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class VideoProvider(Enum):
    """Supported video generation providers."""
    VEO = "veo"
    SEEDANCE = "seedance"
    RUNWAY = "runway"
    MAGNIFIC = "magnific"


@dataclass
class ProviderConfig:
    """Configuration for a video provider."""
    name: str
    priority: int = 0
    max_retries: int = 2
    timeout_seconds: int = 120
    cost_per_second: float = 0.0
    capabilities: Set[str] = field(default_factory=set)
    status: ProviderStatus = ProviderStatus.HEALTHY
    consecutive_failures: int = 0

    @property
    def is_available(self) -> bool:
        """Check if provider is available for use."""
        return self.status != ProviderStatus.UNAVAILABLE


class ProviderRouter:
    """Routes video generation requests across multiple providers with fallback.

    Providers are tried in priority order. If a provider fails,
    the next available provider is used.
    """

    DEFAULT_PROVIDERS = [
        ProviderConfig(
            name=VideoProvider.VEO.value,
            priority=1,
            cost_per_second=0.05,
            capabilities={"text_to_video", "image_to_video", "upscale"},
        ),
        ProviderConfig(
            name=VideoProvider.SEEDANCE.value,
            priority=2,
            cost_per_second=0.03,
            capabilities={"text_to_video", "image_to_video"},
        ),
        ProviderConfig(
            name=VideoProvider.RUNWAY.value,
            priority=3,
            cost_per_second=0.08,
            capabilities={"text_to_video", "image_to_video", "motion_brush"},
        ),
        ProviderConfig(
            name=VideoProvider.MAGNIFIC.value,
            priority=4,
            cost_per_second=0.02,
            capabilities={"upscale", "enhance"},
        ),
    ]

    def __init__(self, providers: Optional[List[ProviderConfig]] = None):
        self.providers: Dict[str, ProviderConfig] = {}
        for p in (self.DEFAULT_PROVIDERS if providers is None else providers):
            # Deep copy to avoid shared state between tests
            self.providers[p.name] = ProviderConfig(
                name=p.name,
                priority=p.priority,
                max_retries=p.max_retries,
                timeout_seconds=p.timeout_seconds,
                cost_per_second=p.cost_per_second,
                capabilities=set(p.capabilities),
                status=p.status,
                consecutive_failures=p.consecutive_failures,
            )
        self._fallback_history: List[Dict[str, Any]] = []

    def select_provider(
        self,
        task: str = "video_produce",
        preferred: Optional[str] = None,
        required_capabilities: Optional[Set[str]] = None,
    ) -> str:
        """Select the best available provider for a task.

        Args:
            task: The task type (e.g., video_produce, video_assemble).
            preferred: Preferred provider name.
            required_capabilities: Capabilities the provider must have.

        Returns:
            Selected provider name.

        Raises:
            RuntimeError: If no suitable provider is available.
        """
        if not self.providers:
            raise RuntimeError("No providers configured")

        candidates = self._get_candidates(required_capabilities)

        if not candidates:
            raise RuntimeError("No available providers match requirements")

        # Try preferred first
        if preferred and preferred in [p.name for p in candidates]:
            return preferred

        # Sort by priority
        candidates.sort(key=lambda p: p.priority)
        return candidates[0].name

    def get_fallback_chain(
        self,
        task: str = "video_produce",
        preferred: Optional[str] = None,
        required_capabilities: Optional[Set[str]] = None,
    ) -> List[str]:
        """Get the full fallback chain for a task.

        Returns:
            Ordered list of provider names to try.
        """
        if not self.providers:
            return []

        candidates = self._get_candidates(required_capabilities)
        candidates.sort(key=lambda p: p.priority)

        chain = [p.name for p in candidates]

        # Move preferred to front
        if preferred and preferred in chain:
            chain.remove(preferred)
            chain.insert(0, preferred)

        return chain

    def report_success(self, provider_name: str):
        """Report a successful call to a provider."""
        if provider_name in self.providers:
            self.providers[provider_name].consecutive_failures = 0
            if self.providers[provider_name].status == ProviderStatus.DEGRADED:
                self.providers[provider_name].status = ProviderStatus.HEALTHY

    def report_failure(self, provider_name: str, threshold: int = 3):
        """Report a failed call to a provider.

        After `threshold` consecutive failures, the provider is marked
        as unavailable. Before that, it is marked as degraded.
        """
        if provider_name in self.providers:
            p = self.providers[provider_name]
            p.consecutive_failures += 1
            if p.consecutive_failures >= threshold:
                p.status = ProviderStatus.UNAVAILABLE
                logger.warning(
                    "Provider %s marked unavailable after %d failures",
                    provider_name,
                    p.consecutive_failures,
                )
            elif p.consecutive_failures >= threshold // 2:
                p.status = ProviderStatus.DEGRADED

    def reset_provider(self, provider_name: str):
        """Reset a provider to healthy state."""
        if provider_name in self.providers:
            p = self.providers[provider_name]
            p.status = ProviderStatus.HEALTHY
            p.consecutive_failures = 0

    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all providers."""
        return {
            name: {
                "status": p.status.value,
                "priority": p.priority,
                "consecutive_failures": p.consecutive_failures,
                "is_available": p.is_available,
            }
            for name, p in self.providers.items()
        }

    def _get_candidates(
        self,
        required_capabilities: Optional[Set[str]] = None,
    ) -> List[ProviderConfig]:
        """Get available providers matching requirements."""
        candidates = []
        for p in self.providers.values():
            if not p.is_available:
                continue
            if required_capabilities and not required_capabilities.issubset(p.capabilities):
                continue
            candidates.append(p)
        return candidates
