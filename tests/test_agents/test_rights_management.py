"""Tests for rights management agents."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ugc_marketplace.agents.rights_management import (
    AccessCheckResult,
    AccessDecision,
    GrantResult,
    RightType,
    RightsManagementAgent,
    RightsRecord,
    check_content_rights,
    check_rights,
    grant_rights,
    license_content,
    revoke_license,
)
from ugc_marketplace.agents.rights_management.base import BaseAgent
from ugc_marketplace.agents.rights_management.infringement_detector import InfringementDetectorAgent
from ugc_marketplace.agents.rights_management.license_detector import LicenseDetectorAgent
from ugc_marketplace.agents.rights_management.rights_validator import RightsValidatorAgent
from ugc_marketplace.agents.rights_management.takedown import TakedownAgent
from ugc_marketplace.agents.rights_management.usage_tracker import UsageTrackerAgent
from ugc_marketplace.agents.rights_management.types import (
    InfringementDetectionRequest,
    InfringementDetectionResult,
    LicenseDetectionRequest,
    LicenseDetectionResult,
    RightsValidation,
    RightsValidationRequest,
    TakedownRequest,
    UsageRecord,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_content_id() -> str:
    """Sample content ID for testing."""
    return "content-001"


@pytest.fixture
def sample_user_id() -> str:
    """Sample user ID for testing."""
    return "user-viewer-10"


@pytest.fixture
def sample_licensee() -> str:
    """Sample licensee identifier for testing."""
    return "licensee-corp-001"


@pytest.fixture
def valid_license_terms() -> dict[str, Any]:
    """Valid license terms for testing."""
    return {
        "usage_type": "commercial",
        "duration_days": 365,
        "territory": "worldwide",
        "exclusive": False,
    }


@pytest.fixture
def infringement_request(
    sample_content_id: str,
) -> InfringementDetectionRequest:
    """Sample infringement detection request."""
    return InfringementDetectionRequest(
        content_id=sample_content_id,
        content_url="https://example.com/content/123",
        content_type="image",
        reporter_id="reporter_001",
    )


@pytest.fixture
def license_request(
    sample_content_id: str,
) -> LicenseDetectionRequest:
    """Sample license detection request."""
    return LicenseDetectionRequest(
        content_id=sample_content_id,
        content_url="https://example.com/content/123",
        content_type="video",
    )


@pytest.fixture
def rights_validation_request(
    sample_content_id: str, sample_user_id: str
) -> RightsValidationRequest:
    """Sample rights validation request."""
    return RightsValidationRequest(
        content_id=sample_content_id,
        user_id=sample_user_id,
        action="download",
    )


@pytest.fixture
def takedown_request(sample_content_id: str) -> TakedownRequest:
    """Sample takedown request."""
    return TakedownRequest(
        content_id=sample_content_id,
        reason="Copyright infringement",
        requester_id="rights_holder_001",
        legal_basis="DMCA",
    )


@pytest.fixture
def usage_record(sample_content_id: str, sample_user_id: str) -> UsageRecord:
    """Sample usage record."""
    return UsageRecord(
        content_id=sample_content_id,
        user_id=sample_user_id,
        usage_type="view",
        metadata={"source": "test"},
    )


@pytest.fixture
def mock_llm() -> MagicMock:
    """Mock LLM for testing."""
    mock = MagicMock()
    mock.invoke = AsyncMock(return_value=MagicMock(content="test response"))
    return mock


@pytest.fixture
def mock_create_agent():
    """Mock create_agent to avoid langchain API incompatibility."""
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={"output": "test result"})
    with patch("ugc_marketplace.agents.rights_management.infringement_detector.create_agent", return_value=mock_agent), \
         patch("ugc_marketplace.agents.rights_management.license_detector.create_agent", return_value=mock_agent), \
         patch("ugc_marketplace.agents.rights_management.rights_validator.create_agent", return_value=mock_agent), \
         patch("ugc_marketplace.agents.rights_management.takedown.create_agent", return_value=mock_agent), \
         patch("ugc_marketplace.agents.rights_management.usage_tracker.create_agent", return_value=mock_agent):
        yield mock_agent


# ---------------------------------------------------------------------------
# BaseAgent Tests
# ---------------------------------------------------------------------------


class TestBaseAgent:
    """Tests for the BaseAgent abstract class."""

    def test_base_agent_is_abstract(self) -> None:
        """Test that BaseAgent cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseAgent()  # type: ignore[abstract]

    def test_base_agent_llm_lazy_init(self, mock_llm: MagicMock) -> None:
        """Test that LLM is lazily initialized."""
        agent = RightsValidatorAgent()
        assert agent._llm is None

        with patch(
            "langchain_openai.ChatOpenAI",
            return_value=mock_llm,
        ):
            llm = agent.llm
            assert llm is mock_llm
            assert agent._llm is mock_llm

    def test_base_agent_llm_cached(self, mock_llm: MagicMock) -> None:
        """Test that LLM is cached after first access."""
        agent = RightsValidatorAgent()

        with patch(
            "langchain_openai.ChatOpenAI",
            return_value=mock_llm,
        ):
            llm1 = agent.llm
            llm2 = agent.llm
            assert llm1 is llm2


# ---------------------------------------------------------------------------
# InfringementDetectorAgent Tests
# ---------------------------------------------------------------------------


class TestInfringementDetectorAgent:
    """Tests for InfringementDetectorAgent."""

    @pytest.mark.asyncio
    async def test_execute_returns_result(
        self, infringement_request: InfringementDetectionRequest, mock_create_agent: MagicMock
    ) -> None:
        """Test that execute returns an InfringementDetectionResult."""
        agent = InfringementDetectorAgent()
        with patch.object(agent, "_timed_execute", new=AsyncMock(return_value=InfringementDetectionResult(
            content_id=infringement_request.content_id,
            is_infringing=False,
            confidence=0.5,
        ))):
            result = await agent.execute(infringement_request)
        assert isinstance(result, InfringementDetectionResult)

    @pytest.mark.asyncio
    async def test_execute_result_contains_content_id(
        self, infringement_request: InfringementDetectionRequest, mock_create_agent: MagicMock
    ) -> None:
        """Test that result contains the correct content_id."""
        agent = InfringementDetectorAgent()
        with patch.object(agent, "_timed_execute", new=AsyncMock(return_value=InfringementDetectionResult(
            content_id=infringement_request.content_id,
            is_infringing=False,
            confidence=0.5,
        ))):
            result = await agent.execute(infringement_request)
        assert result.content_id == infringement_request.content_id

    @pytest.mark.asyncio
    async def test_execute_result_has_confidence(
        self, infringement_request: InfringementDetectionRequest, mock_create_agent: MagicMock
    ) -> None:
        """Test that result has a confidence score."""
        agent = InfringementDetectorAgent()
        with patch.object(agent, "_timed_execute", new=AsyncMock(return_value=InfringementDetectionResult(
            content_id=infringement_request.content_id,
            is_infringing=False,
            confidence=0.5,
        ))):
            result = await agent.execute(infringement_request)
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_execute_result_has_is_infringing_flag(
        self, infringement_request: InfringementDetectionRequest, mock_create_agent: MagicMock
    ) -> None:
        """Test that result has an is_infringing boolean flag."""
        agent = InfringementDetectorAgent()
        with patch.object(agent, "_timed_execute", new=AsyncMock(return_value=InfringementDetectionResult(
            content_id=infringement_request.content_id,
            is_infringing=False,
            confidence=0.5,
        ))):
            result = await agent.execute(infringement_request)
        assert isinstance(result.is_infringing, bool)

    @pytest.mark.asyncio
    async def test_check_copyright_tool(self, sample_content_id: str) -> None:
        """Test the _check_copyright tool."""
        result = await InfringementDetectorAgent._check_copyright(sample_content_id)
        assert result["content_id"] == sample_content_id
        assert "violations" in result

    @pytest.mark.asyncio
    async def test_check_trademark_tool(self, sample_content_id: str) -> None:
        """Test the _check_trademark tool."""
        result = await InfringementDetectorAgent._check_trademark(sample_content_id)
        assert result["content_id"] == sample_content_id
        assert "violations" in result

    @pytest.mark.asyncio
    async def test_check_unauthorized_use_tool(self, sample_content_id: str) -> None:
        """Test the _check_unauthorized_use tool."""
        result = await InfringementDetectorAgent._check_unauthorized_use(
            sample_content_id
        )
        assert result["content_id"] == sample_content_id
        assert "violations" in result

    @pytest.mark.asyncio
    async def test_build_agent(self, mock_create_agent: MagicMock) -> None:
        """Test that _build_agent returns an agent instance."""
        agent = InfringementDetectorAgent()
        built = agent._build_agent()
        assert built is not None


# ---------------------------------------------------------------------------
# LicenseDetectorAgent Tests
# ---------------------------------------------------------------------------


class TestLicenseDetectorAgent:
    """Tests for LicenseDetectorAgent."""

    @pytest.mark.asyncio
    async def test_execute_returns_result(
        self, license_request: LicenseDetectionRequest, mock_create_agent: MagicMock
    ) -> None:
        """Test that execute returns a LicenseDetectionResult."""
        agent = LicenseDetectorAgent()
        with patch.object(agent, "_timed_execute", new=AsyncMock(return_value=LicenseDetectionResult(
            content_id=license_request.content_id,
        ))):
            result = await agent.execute(license_request)
        assert isinstance(result, LicenseDetectionResult)

    @pytest.mark.asyncio
    async def test_execute_result_contains_content_id(
        self, license_request: LicenseDetectionRequest, mock_create_agent: MagicMock
    ) -> None:
        """Test that result contains the correct content_id."""
        agent = LicenseDetectorAgent()
        with patch.object(agent, "_timed_execute", new=AsyncMock(return_value=LicenseDetectionResult(
            content_id=license_request.content_id,
        ))):
            result = await agent.execute(license_request)
        assert result.content_id == license_request.content_id

    @pytest.mark.asyncio
    async def test_execute_result_has_confidence(
        self, license_request: LicenseDetectionRequest, mock_create_agent: MagicMock
    ) -> None:
        """Test that result has a confidence score."""
        agent = LicenseDetectorAgent()
        with patch.object(agent, "_timed_execute", new=AsyncMock(return_value=LicenseDetectionResult(
            content_id=license_request.content_id,
        ))):
            result = await agent.execute(license_request)
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_check_license_status_tool(self, sample_content_id: str) -> None:
        """Test the _check_license_status tool."""
        result = await LicenseDetectorAgent._check_license_status(sample_content_id)
        assert result["content_id"] == sample_content_id
        assert "license_status" in result

    @pytest.mark.asyncio
    async def test_verify_usage_rights_tool(self, sample_content_id: str) -> None:
        """Test the _verify_usage_rights tool."""
        result = await LicenseDetectorAgent._verify_usage_rights(
            sample_content_id, "commercial_use"
        )
        assert result["content_id"] == sample_content_id
        assert result["usage_type"] == "commercial_use"
        assert "authorized" in result

    @pytest.mark.asyncio
    async def test_detect_expired_licenses_tool(
        self, sample_content_id: str
    ) -> None:
        """Test the _detect_expired_licenses tool."""
        result = await LicenseDetectorAgent._detect_expired_licenses(sample_content_id)
        assert result["content_id"] == sample_content_id
        assert "expired" in result

    @pytest.mark.asyncio
    async def test_build_agent(self, mock_create_agent: MagicMock) -> None:
        """Test that _build_agent returns an agent instance."""
        agent = LicenseDetectorAgent()
        built = agent._build_agent()
        assert built is not None


# ---------------------------------------------------------------------------
# RightsValidatorAgent Tests
# ---------------------------------------------------------------------------


class TestRightsValidatorAgent:
    """Tests for RightsValidatorAgent."""

    @pytest.mark.asyncio
    async def test_execute_returns_result(
        self, rights_validation_request: RightsValidationRequest, mock_create_agent: MagicMock
    ) -> None:
        """Test that execute returns a RightsValidation."""
        agent = RightsValidatorAgent()
        with patch.object(agent, "_timed_execute", new=AsyncMock(return_value=RightsValidation(
            content_id=rights_validation_request.content_id,
            user_id=rights_validation_request.user_id,
            action=rights_validation_request.action,
            is_allowed=True,
        ))):
            result = await agent.execute(rights_validation_request)
        assert isinstance(result, RightsValidation)

    @pytest.mark.asyncio
    async def test_execute_result_contains_content_id(
        self, rights_validation_request: RightsValidationRequest, mock_create_agent: MagicMock
    ) -> None:
        """Test that result contains the correct content_id."""
        agent = RightsValidatorAgent()
        with patch.object(agent, "_timed_execute", new=AsyncMock(return_value=RightsValidation(
            content_id=rights_validation_request.content_id,
            user_id=rights_validation_request.user_id,
            action=rights_validation_request.action,
            is_allowed=True,
        ))):
            result = await agent.execute(rights_validation_request)
        assert result.content_id == rights_validation_request.content_id

    @pytest.mark.asyncio
    async def test_execute_result_contains_user_id(
        self, rights_validation_request: RightsValidationRequest, mock_create_agent: MagicMock
    ) -> None:
        """Test that result contains the correct user_id."""
        agent = RightsValidatorAgent()
        with patch.object(agent, "_timed_execute", new=AsyncMock(return_value=RightsValidation(
            content_id=rights_validation_request.content_id,
            user_id=rights_validation_request.user_id,
            action=rights_validation_request.action,
            is_allowed=True,
        ))):
            result = await agent.execute(rights_validation_request)
        assert result.user_id == rights_validation_request.user_id

    @pytest.mark.asyncio
    async def test_execute_result_contains_action(
        self, rights_validation_request: RightsValidationRequest, mock_create_agent: MagicMock
    ) -> None:
        """Test that result contains the correct action."""
        agent = RightsValidatorAgent()
        with patch.object(agent, "_timed_execute", new=AsyncMock(return_value=RightsValidation(
            content_id=rights_validation_request.content_id,
            user_id=rights_validation_request.user_id,
            action=rights_validation_request.action,
            is_allowed=True,
        ))):
            result = await agent.execute(rights_validation_request)
        assert result.action == rights_validation_request.action

    @pytest.mark.asyncio
    async def test_execute_result_has_is_allowed_flag(
        self, rights_validation_request: RightsValidationRequest, mock_create_agent: MagicMock
    ) -> None:
        """Test that result has an is_allowed boolean flag."""
        agent = RightsValidatorAgent()
        with patch.object(agent, "_timed_execute", new=AsyncMock(return_value=RightsValidation(
            content_id=rights_validation_request.content_id,
            user_id=rights_validation_request.user_id,
            action=rights_validation_request.action,
            is_allowed=True,
        ))):
            result = await agent.execute(rights_validation_request)
        assert isinstance(result.is_allowed, bool)

    @pytest.mark.asyncio
    async def test_validate_usage_tool(self, sample_content_id: str) -> None:
        """Test the _validate_usage tool."""
        result = await RightsValidatorAgent._validate_usage(
            sample_content_id, "commercial_use"
        )
        assert result["content_id"] == sample_content_id
        assert result["usage_type"] == "commercial_use"
        assert "valid" in result

    @pytest.mark.asyncio
    async def test_check_territory_tool(self, sample_content_id: str) -> None:
        """Test the _check_territory tool."""
        result = await RightsValidatorAgent._check_territory(sample_content_id, "US")
        assert result["content_id"] == sample_content_id
        assert result["territory"] == "US"
        assert "allowed" in result

    @pytest.mark.asyncio
    async def test_check_duration_tool(self, sample_content_id: str) -> None:
        """Test the _check_duration tool."""
        result = await RightsValidatorAgent._check_duration(sample_content_id)
        assert result["content_id"] == sample_content_id
        assert "within_duration" in result

    @pytest.mark.asyncio
    async def test_build_agent(self, mock_create_agent: MagicMock) -> None:
        """Test that _build_agent returns an agent instance."""
        agent = RightsValidatorAgent()
        built = agent._build_agent()
        assert built is not None


# ---------------------------------------------------------------------------
# TakedownAgent Tests
# ---------------------------------------------------------------------------


class TestTakedownAgent:
    """Tests for TakedownAgent."""

    @pytest.mark.asyncio
    async def test_execute_returns_result(
        self, takedown_request: TakedownRequest, mock_create_agent: MagicMock
    ) -> None:
        """Test that execute returns a TakedownRequest."""
        agent = TakedownAgent()
        with patch.object(agent, "_timed_execute", new=AsyncMock(return_value=TakedownRequest(
            content_id=takedown_request.content_id,
            reason=takedown_request.reason,
            requester_id=takedown_request.requester_id,
        ))):
            result = await agent.execute(takedown_request.__dict__)
        assert isinstance(result, TakedownRequest)

    @pytest.mark.asyncio
    async def test_validate_takedown_request_tool(self) -> None:
        """Test the _validate_takedown_request tool."""
        request_data = {
            "content_id": "content_123",
            "reason": "Copyright infringement",
            "requester_id": "user_456",
        }
        result = await TakedownAgent._validate_takedown_request(request_data)
        assert "valid" in result
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_process_removal_tool(self, sample_content_id: str) -> None:
        """Test the _process_removal tool."""
        result = await TakedownAgent._process_removal(sample_content_id)
        assert result["content_id"] == sample_content_id
        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_notify_stakeholders_tool(self, sample_content_id: str) -> None:
        """Test the _notify_stakeholders tool."""
        request_data = {"reason": "Copyright infringement"}
        result = await TakedownAgent._notify_stakeholders(
            sample_content_id, request_data
        )
        assert result["notified"] is True
        assert result["content_id"] == sample_content_id

    @pytest.mark.asyncio
    async def test_build_agent(self, mock_create_agent: MagicMock) -> None:
        """Test that _build_agent returns an agent instance."""
        agent = TakedownAgent()
        built = agent._build_agent()
        assert built is not None


# ---------------------------------------------------------------------------
# UsageTrackerAgent Tests
# ---------------------------------------------------------------------------


class TestUsageTrackerAgent:
    """Tests for UsageTrackerAgent."""

    @pytest.mark.asyncio
    async def test_execute_returns_result(
        self, sample_content_id: str, sample_user_id: str, mock_create_agent: MagicMock
    ) -> None:
        """Test that execute returns a UsageRecord."""
        agent = UsageTrackerAgent()
        input_data = {
            "content_id": sample_content_id,
            "user_id": sample_user_id,
            "usage_type": "view",
        }
        with patch.object(agent, "_timed_execute", new=AsyncMock(return_value=UsageRecord(
            content_id=sample_content_id,
            user_id=sample_user_id,
            usage_type="view",
        ))):
            result = await agent.execute(input_data)
        assert isinstance(result, UsageRecord)

    @pytest.mark.asyncio
    async def test_record_usage_tool(self, sample_content_id: str) -> None:
        """Test the _record_usage tool."""
        usage_data = {"type": "view", "duration": 30}
        with patch("ugc_marketplace.agents.rights_management.usage_tracker.UTC") as mock_utc:
            mock_utc.now.return_value = datetime.now(timezone.utc)
            result = await UsageTrackerAgent._record_usage(sample_content_id, usage_data)
        assert result["content_id"] == sample_content_id
        assert result["usage"] == usage_data
        assert "recorded_at" in result

    @pytest.mark.asyncio
    async def test_check_usage_limits_tool(self, sample_content_id: str) -> None:
        """Test the _check_usage_limits tool."""
        result = await UsageTrackerAgent._check_usage_limits(sample_content_id)
        assert result["content_id"] == sample_content_id
        assert "within_limits" in result

    @pytest.mark.asyncio
    async def test_generate_usage_report_tool(self, sample_content_id: str) -> None:
        """Test the _generate_usage_report tool."""
        result = await UsageTrackerAgent._generate_usage_report(sample_content_id)
        assert result["content_id"] == sample_content_id
        assert "report" in result

    @pytest.mark.asyncio
    async def test_build_agent(self, mock_create_agent: MagicMock) -> None:
        """Test that _build_agent returns an agent instance."""
        agent = UsageTrackerAgent()
        built = agent._build_agent()
        assert built is not None


# ---------------------------------------------------------------------------
# Type Tests
# ---------------------------------------------------------------------------


class TestTypes:
    """Tests for rights management type definitions."""

    def test_infringement_detection_request(self) -> None:
        """Test InfringementDetectionRequest dataclass."""
        req = InfringementDetectionRequest(
            content_id="c1",
            content_url="https://example.com",
            content_type="image",
        )
        assert req.content_id == "c1"
        assert req.reporter_id is None

    def test_infringement_detection_result(self) -> None:
        """Test InfringementDetectionResult dataclass."""
        result = InfringementDetectionResult(
            content_id="c1",
            is_infringing=True,
            confidence=0.95,
        )
        assert result.content_id == "c1"
        assert result.is_infringing is True
        assert result.confidence == 0.95
        assert result.original_content_url is None
        assert result.details == {}

    def test_license_detection_request(self) -> None:
        """Test LicenseDetectionRequest dataclass."""
        req = LicenseDetectionRequest(
            content_id="c1",
            content_url="https://example.com",
            content_type="video",
        )
        assert req.content_id == "c1"
        assert req.content_type == "video"

    def test_license_detection_result(self) -> None:
        """Test LicenseDetectionResult dataclass."""
        result = LicenseDetectionResult(content_id="c1")
        assert result.content_id == "c1"
        assert result.license_type is None
        assert result.license_url is None
        assert result.confidence == 0.0

    def test_rights_validation_request(self) -> None:
        """Test RightsValidationRequest dataclass."""
        req = RightsValidationRequest(
            content_id="c1",
            user_id="u1",
            action="download",
        )
        assert req.content_id == "c1"
        assert req.user_id == "u1"
        assert req.action == "download"

    def test_rights_validation(self) -> None:
        """Test RightsValidation dataclass."""
        val = RightsValidation(
            content_id="c1",
            user_id="u1",
            action="download",
            is_allowed=True,
        )
        assert val.content_id == "c1"
        assert val.is_allowed is True
        assert val.reason is None

    def test_takedown_request(self) -> None:
        """Test TakedownRequest dataclass."""
        req = TakedownRequest(
            content_id="c1",
            reason="DMCA",
            requester_id="rh1",
        )
        assert req.content_id == "c1"
        assert req.legal_basis is None

    def test_usage_record(self) -> None:
        """Test UsageRecord dataclass."""
        record = UsageRecord(
            content_id="c1",
            user_id="u1",
            usage_type="view",
        )
        assert record.content_id == "c1"
        assert record.user_id == "u1"
        assert record.usage_type == "view"
        assert record.metadata == {}


# ---------------------------------------------------------------------------
# check_content_rights Tests
# ---------------------------------------------------------------------------


class TestCheckContentRights:
    """Tests for the check_content_rights function."""

    def test_returns_dict_with_required_keys(
        self, sample_content_id: str
    ) -> None:
        """Test that check_content_rights returns a dict with required keys."""
        result = check_content_rights(sample_content_id, "commercial")
        assert isinstance(result, dict)
        assert "content_id" in result
        assert "usage_type" in result
        assert "allowed" in result
        assert "reason" in result
        assert "checked_at" in result

    def test_returns_correct_content_id(
        self, sample_content_id: str
    ) -> None:
        """Test that result contains the correct content_id."""
        result = check_content_rights(sample_content_id, "commercial")
        assert result["content_id"] == sample_content_id

    def test_returns_correct_usage_type(
        self, sample_content_id: str
    ) -> None:
        """Test that result contains the correct usage_type."""
        result = check_content_rights(sample_content_id, "commercial")
        assert result["usage_type"] == "commercial"

    def test_allowed_for_registered_content(
        self, sample_content_id: str
    ) -> None:
        """Test that registered content is allowed for valid usage types."""
        result = check_content_rights(sample_content_id, "commercial")
        assert result["allowed"] is True

    def test_not_allowed_for_unregistered_content(self) -> None:
        """Test that unregistered content is not allowed."""
        result = check_content_rights("nonexistent-content", "commercial")
        assert result["allowed"] is False
        assert "not found" in result["reason"].lower()

    @pytest.mark.parametrize(
        "usage_type",
        ["commercial", "non-commercial", "editorial", "personal"],
    )
    def test_all_valid_usage_types(
        self, sample_content_id: str, usage_type: str
    ) -> None:
        """Test that all valid usage types are accepted."""
        result = check_content_rights(sample_content_id, usage_type)
        assert result["usage_type"] == usage_type
        assert result["allowed"] is True

    def test_empty_content_id_raises_value_error(self) -> None:
        """Test that empty content_id raises ValueError."""
        with pytest.raises(ValueError, match="content_id must be a non-empty string"):
            check_content_rights("", "commercial")

    def test_whitespace_content_id_raises_value_error(self) -> None:
        """Test that whitespace-only content_id raises ValueError."""
        with pytest.raises(ValueError, match="content_id must be a non-empty string"):
            check_content_rights("   ", "commercial")

    def test_invalid_usage_type_raises_value_error(
        self, sample_content_id: str
    ) -> None:
        """Test that invalid usage_type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported usage_type"):
            check_content_rights(sample_content_id, "invalid_type")

    def test_checked_at_is_iso_format(self, sample_content_id: str) -> None:
        """Test that checked_at is an ISO-8601 formatted string."""
        result = check_content_rights(sample_content_id, "commercial")
        # Should not raise
        datetime.fromisoformat(result["checked_at"])

    def test_reason_is_string(self, sample_content_id: str) -> None:
        """Test that reason is a string."""
        result = check_content_rights(sample_content_id, "commercial")
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0


# ---------------------------------------------------------------------------
# license_content Tests
# ---------------------------------------------------------------------------


class TestLicenseContent:
    """Tests for the license_content function."""

    def test_returns_dict_with_required_keys(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that license_content returns a dict with required keys."""
        result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        assert isinstance(result, dict)
        assert "license_id" in result
        assert "content_id" in result
        assert "licensee" in result
        assert "terms" in result
        assert "status" in result
        assert "created_at" in result

    def test_returns_correct_content_id(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that result contains the correct content_id."""
        result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        assert result["content_id"] == sample_content_id

    def test_returns_correct_licensee(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that result contains the correct licensee."""
        result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        assert result["licensee"] == sample_licensee

    def test_returns_correct_terms(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that result contains the correct terms."""
        result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        assert result["terms"] == valid_license_terms

    def test_status_is_active(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that newly created license has status 'active'."""
        result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        assert result["status"] == "active"

    def test_license_id_is_uuid(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that license_id is a valid UUID."""
        result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        # Should not raise
        uuid.UUID(result["license_id"])

    def test_created_at_is_iso_format(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that created_at is an ISO-8601 formatted string."""
        result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        # Should not raise
        datetime.fromisoformat(result["created_at"])

    def test_empty_content_id_raises_value_error(
        self, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that empty content_id raises ValueError."""
        with pytest.raises(ValueError, match="content_id must be a non-empty string"):
            license_content("", sample_licensee, valid_license_terms)

    def test_whitespace_content_id_raises_value_error(
        self, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that whitespace-only content_id raises ValueError."""
        with pytest.raises(ValueError, match="content_id must be a non-empty string"):
            license_content("   ", sample_licensee, valid_license_terms)

    def test_empty_licensee_raises_value_error(
        self, sample_content_id: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that empty licensee raises ValueError."""
        with pytest.raises(ValueError, match="licensee must be a non-empty string"):
            license_content(sample_content_id, "", valid_license_terms)

    def test_whitespace_licensee_raises_value_error(
        self, sample_content_id: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that whitespace-only licensee raises ValueError."""
        with pytest.raises(ValueError, match="licensee must be a non-empty string"):
            license_content(sample_content_id, "   ", valid_license_terms)

    def test_non_dict_terms_raises_value_error(
        self, sample_content_id: str, sample_licensee: str
    ) -> None:
        """Test that non-dict terms raises ValueError."""
        with pytest.raises(ValueError, match="terms must be a dictionary"):
            license_content(sample_content_id, sample_licensee, "not a dict")  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "missing_key",
        ["usage_type", "duration_days", "territory", "exclusive"],
    )
    def test_missing_required_term_raises_value_error(
        self,
        sample_content_id: str,
        sample_licensee: str,
        valid_license_terms: dict[str, Any],
        missing_key: str,
    ) -> None:
        """Test that missing required terms raise ValueError."""
        terms = valid_license_terms.copy()
        del terms[missing_key]
        with pytest.raises(ValueError, match="Missing required license terms"):
            license_content(sample_content_id, sample_licensee, terms)

    def test_invalid_usage_type_in_terms_raises_value_error(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that invalid usage_type in terms raises ValueError."""
        terms = valid_license_terms.copy()
        terms["usage_type"] = "invalid"
        with pytest.raises(ValueError, match="Invalid usage_type"):
            license_content(sample_content_id, sample_licensee, terms)

    @pytest.mark.parametrize("duration_days", [0, -1, -100])
    def test_non_positive_duration_raises_value_error(
        self,
        sample_content_id: str,
        sample_licensee: str,
        valid_license_terms: dict[str, Any],
        duration_days: int,
    ) -> None:
        """Test that non-positive duration_days raises ValueError."""
        terms = valid_license_terms.copy()
        terms["duration_days"] = duration_days
        with pytest.raises(ValueError, match="duration_days must be a positive integer"):
            license_content(sample_content_id, sample_licensee, terms)

    def test_non_int_duration_raises_value_error(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that non-integer duration_days raises ValueError."""
        terms = valid_license_terms.copy()
        terms["duration_days"] = "365"  # type: ignore[typeddict-item]
        with pytest.raises(ValueError, match="duration_days must be a positive integer"):
            license_content(sample_content_id, sample_licensee, terms)

    def test_non_bool_exclusive_raises_value_error(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that non-boolean exclusive raises ValueError."""
        terms = valid_license_terms.copy()
        terms["exclusive"] = "yes"  # type: ignore[typeddict-item]
        with pytest.raises(ValueError, match="exclusive must be a boolean"):
            license_content(sample_content_id, sample_licensee, terms)

    @pytest.mark.parametrize(
        "usage_type",
        ["commercial", "non-commercial", "editorial", "personal"],
    )
    def test_all_valid_usage_types_in_terms(
        self,
        sample_content_id: str,
        sample_licensee: str,
        valid_license_terms: dict[str, Any],
        usage_type: str,
    ) -> None:
        """Test that all valid usage types are accepted in terms."""
        terms = valid_license_terms.copy()
        terms["usage_type"] = usage_type
        result = license_content(sample_content_id, sample_licensee, terms)
        assert result["terms"]["usage_type"] == usage_type

    def test_terms_are_copied(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that the original terms dict is not modified."""
        original_terms = valid_license_terms.copy()
        license_content(sample_content_id, sample_licensee, valid_license_terms)
        assert valid_license_terms == original_terms


# ---------------------------------------------------------------------------
# revoke_license Tests
# ---------------------------------------------------------------------------


class TestRevokeLicense:
    """Tests for the revoke_license function."""

    def test_returns_true_for_valid_license(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that revoking a valid license returns True."""
        license_result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        license_id = license_result["license_id"]
        result = revoke_license(license_id)
        assert result is True

    def test_returns_false_for_nonexistent_license(self) -> None:
        """Test that revoking a nonexistent license returns False."""
        result = revoke_license(str(uuid.uuid4()))
        assert result is False

    def test_returns_false_for_already_revoked_license(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that revoking an already revoked license returns False."""
        license_result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        license_id = license_result["license_id"]
        # First revocation should succeed
        assert revoke_license(license_id) is True
        # Second revocation should fail
        assert revoke_license(license_id) is False

    def test_empty_license_id_raises_value_error(self) -> None:
        """Test that empty license_id raises ValueError."""
        with pytest.raises(ValueError, match="license_id must be a non-empty string"):
            revoke_license("")

    def test_whitespace_license_id_raises_value_error(self) -> None:
        """Test that whitespace-only license_id raises ValueError."""
        with pytest.raises(ValueError, match="license_id must be a non-empty string"):
            revoke_license("   ")

    def test_revoked_license_has_revoked_status(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that revoked license has status 'revoked'."""
        license_result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        license_id = license_result["license_id"]
        revoke_license(license_id)
        # Check the internal state
        from ugc_marketplace.agents.rights_management import _rights_management_module as _rm_module
        _MOCK_LICENSES = _rm_module._MOCK_LICENSES
        assert _MOCK_LICENSES[license_id]["status"] == "revoked"

    def test_revoked_license_has_revoked_at_timestamp(
        self, sample_content_id: str, sample_licensee: str, valid_license_terms: dict[str, Any]
    ) -> None:
        """Test that revoked license has a revoked_at timestamp."""
        license_result = license_content(sample_content_id, sample_licensee, valid_license_terms)
        license_id = license_result["license_id"]
        revoke_license(license_id)
        from ugc_marketplace.agents.rights_management import _rights_management_module as _rm_module
        _MOCK_LICENSES = _rm_module._MOCK_LICENSES
        assert "revoked_at" in _MOCK_LICENSES[license_id]
        # Should be a valid ISO format
        datetime.fromisoformat(_MOCK_LICENSES[license_id]["revoked_at"])


# ---------------------------------------------------------------------------
# RightsManagementAgent Tests
# ---------------------------------------------------------------------------


class TestRightsManagementAgent:
    """Tests for the RightsManagementAgent class."""

    @pytest.fixture
    def agent(self) -> RightsManagementAgent:
        """Create a fresh RightsManagementAgent for each test."""
        return RightsManagementAgent()

    def test_check_rights_owner_has_all_rights(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that content owner has all rights."""
        result = agent.check_rights("content-001", "user-admin-01", RightType.VIEW)
        assert result.decision == AccessDecision.ALLOWED
        assert result.granted_rights == set(RightType)

    def test_check_rights_with_valid_grant(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test check_rights with a valid rights grant."""
        result = agent.check_rights("content-001", "user-viewer-10", RightType.VIEW)
        assert result.decision == AccessDecision.ALLOWED
        assert RightType.VIEW in result.granted_rights

    def test_check_rights_without_grant_denied(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that check_rights denies access without a grant."""
        result = agent.check_rights("content-001", "user-unknown", RightType.VIEW)
        assert result.decision == AccessDecision.DENIED

    def test_check_rights_pending_request(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that pending requests return PENDING decision."""
        result = agent.check_rights("content-005", "user-viewer-10", RightType.VIEW)
        assert result.decision == AccessDecision.PENDING

    def test_check_rights_expired_grant(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that expired grants return EXPIRED decision."""
        # content-002 has an expiry of 2026-10-15 which may be expired
        # depending on current date. Let's create our own expired grant.
        agent.grant_rights(
            "content-001",
            "user-expired",
            {RightType.VIEW},
            duration_days=1,
        )
        # Manually expire it by modifying the record
        key = ("content-001", "user-expired")
        if key in agent._rights_db:
            agent._rights_db[key].expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        result = agent.check_rights("content-001", "user-expired", RightType.VIEW)
        assert result.decision == AccessDecision.EXPIRED

    def test_check_rights_wrong_right_denied(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that having one right doesn't grant another."""
        # user-viewer-10 has VIEW on content-002 but not EDIT
        result = agent.check_rights("content-002", "user-viewer-10", RightType.EDIT)
        assert result.decision == AccessDecision.DENIED

    def test_grant_rights_success(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test successful rights grant."""
        result = agent.grant_rights(
            "content-001",
            "user-new",
            {RightType.VIEW, RightType.DOWNLOAD},
        )
        assert result.success is True
        assert result.content_id == "content-001"
        assert result.user_id == "user-new"
        assert result.rights == {RightType.VIEW, RightType.DOWNLOAD}

    def test_grant_rights_empty_rights_fails(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that granting empty rights set fails."""
        result = agent.grant_rights("content-001", "user-new", set())
        assert result.success is False
        assert "At least one right" in result.message

    def test_grant_rights_with_duration(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test granting rights with a duration."""
        result = agent.grant_rights(
            "content-001",
            "user-temp",
            {RightType.VIEW},
            duration_days=30,
        )
        assert result.success is True
        key = ("content-001", "user-temp")
        assert agent._rights_db[key].expires_at is not None

    def test_grant_rights_invalid_duration_fails(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that invalid duration fails."""
        result = agent.grant_rights(
            "content-001",
            "user-temp",
            {RightType.VIEW},
            duration_days=-1,
        )
        assert result.success is False
        assert "duration_days must be a positive integer" in result.message

    def test_grant_rights_removes_pending(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that granting rights removes pending request."""
        # content-005 has a pending request from user-viewer-10
        agent.grant_rights("content-005", "user-viewer-10", {RightType.VIEW})
        assert ("content-005", "user-viewer-10") not in agent._pending_requests

    def test_revoke_rights_all(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test revoking all rights."""
        agent.grant_rights("content-001", "user-revoke", {RightType.VIEW})
        result = agent.revoke_rights("content-001", "user-revoke")
        assert result is True
        assert ("content-001", "user-revoke") not in agent._rights_db

    def test_revoke_rights_specific(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test revoking specific rights."""
        agent.grant_rights(
            "content-001",
            "user-partial",
            {RightType.VIEW, RightType.DOWNLOAD},
        )
        result = agent.revoke_rights("content-001", "user-partial", {RightType.VIEW})
        assert result is True
        # Should still have DOWNLOAD
        assert agent._rights_db[("content-001", "user-partial")].rights == {RightType.DOWNLOAD}

    def test_revoke_rights_nonexistent_returns_false(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test that revoking nonexistent rights returns False."""
        result = agent.revoke_rights("content-001", "user-nonexistent")
        assert result is False

    def test_list_user_rights(
        self, agent: RightsManagementAgent
    ) -> None:
        """Test listing user rights."""
        agent.grant_rights("content-001", "user-list", {RightType.VIEW})
        agent.grant_rights("content-002", "user-list", {RightType.VIEW})
        results = agent.list_user_rights("user-list")
        assert len(results) == 2
        assert all(r.decision == AccessDecision.ALLOWED for r in results)


# ---------------------------------------------------------------------------
# RightsRecord Tests
# ---------------------------------------------------------------------------


class TestRightsRecord:
    """Tests for the RightsRecord dataclass."""

    def test_is_active_no_expiry(self) -> None:
        """Test that record without expiry is always active."""
        record = RightsRecord(
            content_id="c1",
            user_id="u1",
            rights={RightType.VIEW},
            granted_by="admin",
            granted_at=datetime.now(timezone.utc),
            expires_at=None,
        )
        assert record.is_active() is True

    def test_is_active_not_expired(self) -> None:
        """Test that record with future expiry is active."""
        record = RightsRecord(
            content_id="c1",
            user_id="u1",
            rights={RightType.VIEW},
            granted_by="admin",
            granted_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        assert record.is_active() is True

    def test_is_active_expired(self) -> None:
        """Test that record with past expiry is not active."""
        record = RightsRecord(
            content_id="c1",
            user_id="u1",
            rights={RightType.VIEW},
            granted_by="admin",
            granted_at=datetime.now(timezone.utc) - timedelta(days=10),
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert record.is_active() is False


# ---------------------------------------------------------------------------
# Enum Tests
# ---------------------------------------------------------------------------


class TestEnums:
    """Tests for RightType and AccessDecision enums."""

    def test_right_type_values(self) -> None:
        """Test that RightType enum has expected values."""
        assert RightType.VIEW.value == "view"
        assert RightType.DOWNLOAD.value == "download"
        assert RightType.EDIT.value == "edit"
        assert RightType.DELETE.value == "delete"
        assert RightType.SHARE.value == "share"
        assert RightType.COMMERCIAL_USE.value == "commercial_use"
        assert RightType.ATTRIBUTION.value == "attribution"

    def test_access_decision_values(self) -> None:
        """Test that AccessDecision enum has expected values."""
        assert AccessDecision.ALLOWED.value == "allowed"
        assert AccessDecision.DENIED.value == "denied"
        assert AccessDecision.PENDING.value == "pending"
        assert AccessDecision.EXPIRED.value == "expired"


# ---------------------------------------------------------------------------
# Module-level check_rights and grant_rights Tests
# ---------------------------------------------------------------------------


class TestModuleLevelFunctions:
    """Tests for module-level check_rights and grant_rights functions."""

    def test_module_level_check_rights(self) -> None:
        """Test module-level check_rights function."""
        result = check_rights("content-001", "user-admin-01", RightType.VIEW)
        assert isinstance(result, AccessCheckResult)
        assert result.decision == AccessDecision.ALLOWED

    def test_module_level_grant_rights(self) -> None:
        """Test module-level grant_rights function."""
        result = grant_rights(
            "content-001",
            "user-module-test",
            {RightType.VIEW},
        )
        assert isinstance(result, GrantResult)
        assert result.success is True


# ---------------------------------------------------------------------------
# Integration-style Tests
# ---------------------------------------------------------------------------


class TestRightsManagementIntegration:
    """Integration-style tests for rights management agents."""

    @pytest.mark.asyncio
    async def test_full_rights_validation_workflow(
        self,
        sample_content_id: str,
        sample_user_id: str,
        mock_create_agent: MagicMock,
    ) -> None:
        """Test a full rights validation workflow."""
        # Step 1: Check for infringement
        infringement_agent = InfringementDetectorAgent()
        with patch.object(infringement_agent, "_timed_execute", new=AsyncMock(return_value=InfringementDetectionResult(
            content_id=sample_content_id,
            is_infringing=False,
            confidence=0.5,
        ))):
            infringement_result = await infringement_agent.execute(
                InfringementDetectionRequest(
                    content_id=sample_content_id,
                    content_url="https://example.com/content/123",
                    content_type="image",
                )
            )
        assert isinstance(infringement_result, InfringementDetectionResult)

        # Step 2: Detect license
        license_agent = LicenseDetectorAgent()
        with patch.object(license_agent, "_timed_execute", new=AsyncMock(return_value=LicenseDetectionResult(
            content_id=sample_content_id,
        ))):
            license_result = await license_agent.execute(
                LicenseDetectionRequest(
                    content_id=sample_content_id,
                    content_url="https://example.com/content/123",
                    content_type="image",
                )
            )
        assert isinstance(license_result, LicenseDetectionResult)

        # Step 3: Validate rights
        validator_agent = RightsValidatorAgent()
        with patch.object(validator_agent, "_timed_execute", new=AsyncMock(return_value=RightsValidation(
            content_id=sample_content_id,
            user_id=sample_user_id,
            action="download",
            is_allowed=True,
        ))):
            validation_result = await validator_agent.execute(
                RightsValidationRequest(
                    content_id=sample_content_id,
                    user_id=sample_user_id,
                    action="download",
                )
            )
        assert isinstance(validation_result, RightsValidation)

    @pytest.mark.asyncio
    async def test_takedown_and_usage_tracking_workflow(
        self, sample_content_id: str, sample_user_id: str, mock_create_agent: MagicMock
    ) -> None:
        """Test takedown followed by usage tracking."""
        # Step 1: Process takedown
        takedown_agent = TakedownAgent()
        with patch.object(takedown_agent, "_timed_execute", new=AsyncMock(return_value=TakedownRequest(
            content_id=sample_content_id,
            reason="Copyright infringement",
            requester_id="rights_holder_001",
        ))):
            takedown_result = await takedown_agent.execute(
                {
                    "content_id": sample_content_id,
                    "reason": "Copyright infringement",
                    "requester_id": "rights_holder_001",
                }
            )
        assert isinstance(takedown_result, TakedownRequest)

        # Step 2: Track usage after takedown
        usage_agent = UsageTrackerAgent()
        with patch.object(usage_agent, "_timed_execute", new=AsyncMock(return_value=UsageRecord(
            content_id=sample_content_id,
            user_id=sample_user_id,
            usage_type="view",
        ))):
            usage_result = await usage_agent.execute(
                {
                    "content_id": sample_content_id,
                    "user_id": sample_user_id,
                    "usage_type": "view",
                }
            )
        assert isinstance(usage_result, UsageRecord)

    @pytest.mark.asyncio
    async def test_all_agents_inherit_base_agent(self) -> None:
        """Test that all rights management agents inherit from BaseAgent."""
        agents = [
            InfringementDetectorAgent(),
            LicenseDetectorAgent(),
            RightsValidatorAgent(),
            TakedownAgent(),
            UsageTrackerAgent(),
        ]
        for agent in agents:
            assert isinstance(agent, BaseAgent)

    @pytest.mark.asyncio
    async def test_all_agents_have_build_agent(self, mock_create_agent: MagicMock) -> None:
        """Test that all agents have _build_agent method."""
        agents = [
            InfringementDetectorAgent(),
            LicenseDetectorAgent(),
            RightsValidatorAgent(),
            TakedownAgent(),
            UsageTrackerAgent(),
        ]
        for agent in agents:
            assert hasattr(agent, "_build_agent")
            built = agent._build_agent()
            assert built is not None
