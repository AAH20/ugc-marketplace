"""Integration tests for multi-provider routing with fallback."""
import pytest

from app import models  # noqa: F401
from app.main import app  # noqa: F401
from app.services.provider_router import (
    ProviderConfig,
    ProviderRouter,
    ProviderStatus,
    VideoProvider,
)


class TestProviderSelection:
    """Tests for provider selection logic."""

    def test_default_providers_loaded(self):
        """Default providers are loaded on init."""
        router = ProviderRouter()
        assert len(router.providers) == 4
        assert "veo" in router.providers
        assert "seedance" in router.providers
        assert "runway" in router.providers
        assert "magnific" in router.providers

    def test_select_preferred_provider(self):
        """Preferred provider is selected when available."""
        router = ProviderRouter()
        selected = router.select_provider(task="video_produce", preferred="runway")
        assert selected == "runway"

    def test_select_highest_priority_when_no_preference(self):
        """Highest priority provider is selected by default."""
        router = ProviderRouter()
        selected = router.select_provider(task="video_produce")
        assert selected == "veo"  # priority 1

    def test_select_with_capability_filter(self):
        """Provider is filtered by required capabilities."""
        router = ProviderRouter()
        selected = router.select_provider(
            task="video_produce",
            required_capabilities={"text_to_video"},
        )
        assert selected in ("veo", "seedance", "runway")

    def test_select_with_unavailable_preferred_falls_back(self):
        """Falls back when preferred provider is unavailable."""
        router = ProviderRouter()
        router.providers["veo"].status = ProviderStatus.UNAVAILABLE
        selected = router.select_provider(task="video_produce", preferred="veo")
        assert selected == "seedance"  # next priority

    def test_no_available_providers_raises(self):
        """Raises RuntimeError when no providers are available."""
        router = ProviderRouter()
        for p in router.providers.values():
            p.status = ProviderStatus.UNAVAILABLE
        with pytest.raises(RuntimeError, match="No available providers"):
            router.select_provider()

    def test_capability_filter_excludes_mismatched(self):
        """Providers without required capabilities are excluded."""
        router = ProviderRouter()
        selected = router.select_provider(
            task="video_produce",
            required_capabilities={"motion_brush"},
        )
        assert selected == "runway"  # only runway has motion_brush


class TestFallbackChain:
    """Tests for fallback chain generation."""

    def test_fallback_chain_ordered_by_priority(self):
        """Fallback chain is ordered by priority."""
        router = ProviderRouter()
        chain = router.get_fallback_chain(task="video_produce")
        assert chain == ["veo", "seedance", "runway", "magnific"]

    def test_fallback_chain_with_preferred_first(self):
        """Preferred provider is moved to front of chain."""
        router = ProviderRouter()
        chain = router.get_fallback_chain(task="video_produce", preferred="runway")
        assert chain[0] == "runway"
        assert len(chain) == 4

    def test_fallback_chain_excludes_unavailable(self):
        """Unavailable providers are excluded from chain."""
        router = ProviderRouter()
        router.providers["veo"].status = ProviderStatus.UNAVAILABLE
        chain = router.get_fallback_chain(task="video_produce")
        assert "veo" not in chain
        assert len(chain) == 3

    def test_fallback_chain_with_capability_filter(self):
        """Chain respects capability requirements."""
        router = ProviderRouter()
        chain = router.get_fallback_chain(
            task="video_produce",
            required_capabilities={"text_to_video"},
        )
        assert "magnific" not in chain  # no text_to_video
        assert len(chain) == 3


class TestProviderHealth:
    """Tests for provider health tracking."""

    def test_report_success_resets_failures(self):
        """Successful call resets consecutive failures."""
        router = ProviderRouter()
        router.providers["veo"].consecutive_failures = 2
        router.report_success("veo")
        assert router.providers["veo"].consecutive_failures == 0

    def test_report_failure_increments_counter(self):
        """Failed call increments consecutive failures."""
        router = ProviderRouter()
        router.report_failure("veo")
        assert router.providers["veo"].consecutive_failures == 1

    def test_provider_marked_unavailable_after_threshold(self):
        """Provider becomes unavailable after threshold failures."""
        router = ProviderRouter()
        for _ in range(3):
            router.report_failure("veo")
        assert router.providers["veo"].status == ProviderStatus.UNAVAILABLE

    def test_provider_marked_degraded_before_threshold(self):
        """Provider becomes degraded before unavailable threshold."""
        router = ProviderRouter()
        router.report_failure("veo")
        router.report_failure("veo")
        assert router.providers["veo"].status == ProviderStatus.DEGRADED

    def test_reset_provider(self):
        """Reset brings provider back to healthy."""
        router = ProviderRouter()
        router.providers["veo"].status = ProviderStatus.UNAVAILABLE
        router.providers["veo"].consecutive_failures = 5
        router.reset_provider("veo")
        assert router.providers["veo"].status == ProviderStatus.HEALTHY
        assert router.providers["veo"].consecutive_failures == 0

    def test_get_provider_status(self):
        """Status report includes all providers."""
        router = ProviderRouter()
        status = router.get_provider_status()
        assert len(status) == 4
        assert "veo" in status
        assert status["veo"]["status"] == "healthy"
        assert status["veo"]["is_available"] is True


class TestCustomProviders:
    """Tests with custom provider configurations."""

    def test_custom_providers_override_defaults(self):
        """Custom providers replace defaults."""
        custom = [
            ProviderConfig(name="custom_ai", priority=1, cost_per_second=0.01),
        ]
        router = ProviderRouter(providers=custom)
        assert len(router.providers) == 1
        assert "custom_ai" in router.providers

    def test_empty_providers_raises_on_select(self):
        """Selecting from empty provider list raises."""
        router = ProviderRouter(providers=[])
        with pytest.raises(RuntimeError):
            router.select_provider()


class TestProviderCapabilities:
    """Tests for provider capability matching."""

    def test_veo_capabilities(self):
        """Veo has expected capabilities."""
        router = ProviderRouter()
        veo = router.providers["veo"]
        assert "text_to_video" in veo.capabilities
        assert "image_to_video" in veo.capabilities
        assert "upscale" in veo.capabilities

    def test_magnific_limited_capabilities(self):
        """Magnific only has upscale/enhance."""
        router = ProviderRouter()
        magnific = router.providers["magnific"]
        assert "upscale" in magnific.capabilities
        assert "enhance" in magnific.capabilities
        assert "text_to_video" not in magnific.capabilities

    def test_runway_motion_brush(self):
        """Runway has motion_brush capability."""
        router = ProviderRouter()
        runway = router.providers["runway"]
        assert "motion_brush" in runway.capabilities
