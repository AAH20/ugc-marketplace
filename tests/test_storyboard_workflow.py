"""Integration tests for storyboard workflow with approval gates."""
import json
from unittest.mock import MagicMock, patch

import pytest

from app import models  # noqa: F401
from app.services.storyboard_workflow import (
    ApprovalDecision,
    ApprovalGate,
    Scene,
    Storyboard,
    StoryboardStatus,
    StoryboardWorkflow,
)
from app.services.videoclaw_cli import VideoClawCLIClient


@pytest.fixture
def mock_cli():
    """Create a mock CLI client."""
    cli = MagicMock(spec=VideoClawCLIClient)
    cli.video_create.return_value = {"project_id": "proj_123", "status": "created"}
    cli.video_produce.return_value = {"job_id": "job_456", "status": "processing"}
    cli.video_assemble.return_value = {
        "video_url": "https://cdn.example.com/video.mp4",
        "status": "ready",
    }
    return cli


@pytest.fixture
def workflow(mock_cli):
    """Create a storyboard workflow with mock CLI."""
    return StoryboardWorkflow(cli_client=mock_cli)


class TestStoryboardCreation:
    """Tests for storyboard creation."""

    def test_create_storyboard(self, workflow, mock_cli):
        """Storyboard is created with correct project ID."""
        sb = workflow.create_storyboard("Test Video", "A cat playing piano", scene_count=3)

        assert sb.project_id == "proj_123"
        assert sb.title == "Test Video"
        assert sb.status == StoryboardStatus.DRAFT
        assert sb.scene_count == 3
        assert sb.total_duration == 15.0  # 3 scenes * 5s
        mock_cli.video_create.assert_called_once()

    def test_create_storyboard_with_provider(self, workflow, mock_cli):
        """Provider is passed to CLI on creation."""
        sb = workflow.create_storyboard(
            "Test", "prompt", provider="veo"
        )

        assert sb.provider == "veo"
        call_kwargs = mock_cli.video_create.call_args
        assert call_kwargs[1].get("provider") == "veo" or "veo" in str(call_kwargs)

    def test_storyboard_stored_in_workflow(self, workflow):
        """Created storyboard is retrievable."""
        sb = workflow.create_storyboard("Test", "prompt")
        retrieved = workflow.get_storyboard(sb.project_id)

        assert retrieved is not None
        assert retrieved.project_id == sb.project_id
        assert retrieved.title == "Test"


class TestApprovalGates:
    """Tests for approval gate workflow."""

    def test_submit_for_approval(self, workflow):
        """Submitting for approval creates a gate and changes status."""
        sb = workflow.create_storyboard("Test", "prompt")
        gate = workflow.submit_for_approval(sb.project_id, approver="user_1")

        assert isinstance(gate, ApprovalGate)
        assert gate.approver == "user_1"
        assert gate.decision is None
        assert sb.status == StoryboardStatus.PENDING_APPROVAL

    def test_approve_storyboard(self, workflow):
        """Approving changes status to APPROVED."""
        sb = workflow.create_storyboard("Test", "prompt")
        workflow.submit_for_approval(sb.project_id, "user_1")
        result = workflow.approve_storyboard(sb.project_id, ApprovalDecision.APPROVE)

        assert result.status == StoryboardStatus.APPROVED

    def test_reject_storyboard(self, workflow):
        """Rejecting changes status to REJECTED."""
        sb = workflow.create_storyboard("Test", "prompt")
        workflow.submit_for_approval(sb.project_id, "user_1")
        result = workflow.approve_storyboard(sb.project_id, ApprovalDecision.REJECT)

        assert result.status == StoryboardStatus.REJECTED

    def test_revise_storyboard(self, workflow):
        """Revising sends back to DRAFT."""
        sb = workflow.create_storyboard("Test", "prompt")
        workflow.submit_for_approval(sb.project_id, "user_1")
        result = workflow.approve_storyboard(sb.project_id, ApprovalDecision.REVISE)

        assert result.status == StoryboardStatus.DRAFT

    def test_approval_with_feedback(self, workflow):
        """Feedback is recorded on the gate."""
        sb = workflow.create_storyboard("Test", "prompt")
        workflow.submit_for_approval(sb.project_id, "user_1")
        workflow.approve_storyboard(
            sb.project_id,
            ApprovalDecision.REVISE,
            feedback="Make it more dramatic",
        )

        gates = workflow.get_approval_history(sb.project_id)
        assert len(gates) == 1
        assert gates[0].feedback == "Make it more dramatic"

    def test_approval_callback_triggered(self, workflow):
        """Callback is called when approval is submitted."""
        callback = MagicMock()
        sb = workflow.create_storyboard("Test", "prompt")
        workflow.register_approval_callback(sb.project_id, callback)

        workflow.submit_for_approval(sb.project_id, "user_1")
        callback.assert_called_once()

    def test_approval_history_multiple_gates(self, workflow):
        """Multiple approval rounds create multiple gates."""
        sb = workflow.create_storyboard("Test", "prompt")
        workflow.submit_for_approval(sb.project_id, "user_1")
        workflow.approve_storyboard(sb.project_id, ApprovalDecision.REVISE)
        workflow.submit_for_approval(sb.project_id, "user_1")
        workflow.approve_storyboard(sb.project_id, ApprovalDecision.APPROVE)

        gates = workflow.get_approval_history(sb.project_id)
        assert len(gates) == 2

    def test_approve_without_gate_raises(self, workflow):
        """Approving without a gate raises ValueError."""
        sb = workflow.create_storyboard("Test", "prompt")
        with pytest.raises(ValueError, match="No approval gate"):
            workflow.approve_storyboard(sb.project_id, ApprovalDecision.APPROVE)

    def test_submit_nonexistent_storyboard_raises(self, workflow):
        """Submitting non-existent storyboard raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            workflow.submit_for_approval("nonexistent", "user_1")


class TestVideoProduction:
    """Tests for video production in workflow."""

    def test_produce_requires_approval(self, workflow, mock_cli):
        """Cannot produce video without approval."""
        sb = workflow.create_storyboard("Test", "prompt")
        with pytest.raises(ValueError, match="must be approved"):
            workflow.produce_video(sb.project_id)

    def test_produce_after_approval(self, workflow, mock_cli):
        """Produce works after storyboard is approved."""
        sb = workflow.create_storyboard("Test", "prompt")
        workflow.submit_for_approval(sb.project_id, "user_1")
        workflow.approve_storyboard(sb.project_id, ApprovalDecision.APPROVE)

        result = workflow.produce_video(sb.project_id)

        assert result["job_id"] == "job_456"
        assert sb.status == StoryboardStatus.PRODUCING
        mock_cli.video_produce.assert_called_once()

    def test_produce_with_provider_override(self, workflow, mock_cli):
        """Provider can be overridden at production time."""
        sb = workflow.create_storyboard("Test", "prompt", provider="veo")
        workflow.submit_for_approval(sb.project_id, "user_1")
        workflow.approve_storyboard(sb.project_id, ApprovalDecision.APPROVE)

        workflow.produce_video(sb.project_id, provider="runway")

        call_args = mock_cli.video_produce.call_args
        assert "runway" in str(call_args)

    def test_produce_nonexistent_raises(self, workflow):
        """Producing non-existent storyboard raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            workflow.produce_video("nonexistent")


class TestVideoAssembly:
    """Tests for video assembly in workflow."""

    def test_assemble_video(self, workflow, mock_cli):
        """Assembly returns video URL and marks complete."""
        sb = workflow.create_storyboard("Test", "prompt")
        workflow.submit_for_approval(sb.project_id, "user_1")
        workflow.approve_storyboard(sb.project_id, ApprovalDecision.APPROVE)
        workflow.produce_video(sb.project_id)

        result = workflow.assemble_video(sb.project_id)

        assert result["video_url"] == "https://cdn.example.com/video.mp4"
        assert sb.status == StoryboardStatus.COMPLETE
        mock_cli.video_assemble.assert_called_once()

    def test_assemble_nonexistent_raises(self, workflow):
        """Assembling non-existent storyboard raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            workflow.assemble_video("nonexistent")


class TestFullWorkflow:
    """End-to-end workflow tests."""

    def test_full_approved_workflow(self, workflow, mock_cli):
        """Complete workflow from creation to assembly."""
        # Create
        sb = workflow.create_storyboard("Ad Video", "Product showcase", scene_count=4)
        assert sb.status == StoryboardStatus.DRAFT

        # Submit and approve
        workflow.submit_for_approval(sb.project_id, "manager_1")
        assert sb.status == StoryboardStatus.PENDING_APPROVAL
        workflow.approve_storyboard(sb.project_id, ApprovalDecision.APPROVE)
        assert sb.status == StoryboardStatus.APPROVED

        # Produce
        workflow.produce_video(sb.project_id)
        assert sb.status == StoryboardStatus.PRODUCING

        # Assemble
        result = workflow.assemble_video(sb.project_id)
        assert sb.status == StoryboardStatus.COMPLETE
        assert result["video_url"] == "https://cdn.example.com/video.mp4"

        # Verify all CLI calls
        mock_cli.video_create.assert_called_once()
        mock_cli.video_produce.assert_called_once()
        mock_cli.video_assemble.assert_called_once()

    def test_rejected_workflow_stops(self, workflow, mock_cli):
        """Rejected storyboard cannot proceed to production."""
        sb = workflow.create_storyboard("Test", "prompt")
        workflow.submit_for_approval(sb.project_id, "user_1")
        workflow.approve_storyboard(sb.project_id, ApprovalDecision.REJECT)

        with pytest.raises(ValueError, match="must be approved"):
            workflow.produce_video(sb.project_id)

        mock_cli.video_produce.assert_not_called()
