"""Integration tests for VideoClaw CLI client with mocked subprocess."""
import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from app import models  # noqa: F401
from app.main import app  # noqa: F401
from app.services.videoclaw_cli import (
    VideoClawCLIClient,
    VideoClawCLIError,
    ExitCode,
)


def make_completed_process(returncode=0, stdout="", stderr=""):
    """Helper to create a mock CompletedProcess."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


class TestVideoCLICreate:
    """Tests for vclaw video create command."""

    @patch("subprocess.run")
    def test_create_success(self, mock_run):
        """Successful video create returns parsed JSON."""
        mock_run.return_value = make_completed_process(
            returncode=0,
            stdout=json.dumps({"project_id": "proj_123", "status": "created"}),
        )
        client = VideoClawCLIClient()
        result = client.video_create("My Project")

        assert result["project_id"] == "proj_123"
        assert result["status"] == "created"
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "vclaw"
        assert args[1] == "video"
        assert args[2] == "create"
        assert "My Project" in args

    @patch("subprocess.run")
    def test_create_with_custom_cli_path(self, mock_run):
        """Custom CLI path is used in subprocess call."""
        mock_run.return_value = make_completed_process(
            returncode=0,
            stdout=json.dumps({"project_id": "proj_123"}),
        )
        client = VideoClawCLIClient(cli_path="/usr/local/bin/vclaw")
        client.video_create("Test")

        args = mock_run.call_args[0][0]
        assert args[0] == "/usr/local/bin/vclaw"

    @patch("subprocess.run")
    def test_create_bad_input_exit_code_1(self, mock_run):
        """Exit code 1 raises VideoClawCLIError with bad input details."""
        mock_run.return_value = make_completed_process(
            returncode=1,
            stdout="",
            stderr="Invalid project name",
        )
        client = VideoClawCLIClient()
        with pytest.raises(VideoClawCLIError) as exc_info:
            client.video_create("")

        assert exc_info.value.exit_code == 1
        assert "Invalid project name" in str(exc_info.value)

    @patch("subprocess.run")
    def test_create_system_error_exit_code_2(self, mock_run):
        """Exit code 2 raises VideoClawCLIError with system error."""
        mock_run.return_value = make_completed_process(
            returncode=2,
            stdout="",
            stderr="Disk full",
        )
        client = VideoClawCLIClient()
        with pytest.raises(VideoClawCLIError) as exc_info:
            client.video_create("Test")

        assert exc_info.value.exit_code == 2

    @patch("subprocess.run")
    def test_create_gated_exit_code_3(self, mock_run):
        """Exit code 3 raises VideoClawCLIError with gated message."""
        mock_run.return_value = make_completed_process(
            returncode=3,
            stdout="",
            stderr="Content gated",
        )
        client = VideoClawCLIClient()
        with pytest.raises(VideoClawCLIError) as exc_info:
            client.video_create("Test")

        assert exc_info.value.exit_code == 3

    @patch("subprocess.run")
    def test_create_with_extra_kwargs(self, mock_run):
        """Extra kwargs are passed as CLI arguments."""
        mock_run.return_value = make_completed_process(
            returncode=0,
            stdout=json.dumps({"project_id": "proj_123"}),
        )
        client = VideoClawCLIClient()
        client.video_create("Test", resolution="1080p", duration=30)

        args = mock_run.call_args[0][0]
        assert "--resolution" in args
        assert "1080p" in args
        assert "--duration" in args
        assert "30" in args


class TestVideoCLIProduce:
    """Tests for vclaw video produce command."""

    @patch("subprocess.run")
    def test_produce_success(self, mock_run):
        """Successful video produce returns parsed JSON."""
        mock_run.return_value = make_completed_process(
            returncode=0,
            stdout=json.dumps({"job_id": "job_456", "status": "processing"}),
        )
        client = VideoClawCLIClient()
        result = client.video_produce("proj_123")

        assert result["job_id"] == "job_456"
        assert result["status"] == "processing"
        args = mock_run.call_args[0][0]
        assert args[0] == "vclaw"
        assert args[1] == "video"
        assert args[2] == "produce"
        assert "proj_123" in args

    @patch("subprocess.run")
    def test_produce_with_provider(self, mock_run):
        """Provider flag is passed to CLI."""
        mock_run.return_value = make_completed_process(
            returncode=0,
            stdout=json.dumps({"job_id": "job_456"}),
        )
        client = VideoClawCLIClient()
        client.video_produce("proj_123", provider="veo")

        args = mock_run.call_args[0][0]
        assert "--provider" in args
        assert "veo" in args

    @patch("subprocess.run")
    def test_produce_bad_input(self, mock_run):
        """Exit code 1 on produce raises error."""
        mock_run.return_value = make_completed_process(
            returncode=1,
            stdout="",
            stderr="Project not found",
        )
        client = VideoClawCLIClient()
        with pytest.raises(VideoClawCLIError) as exc_info:
            client.video_produce("nonexistent")

        assert exc_info.value.exit_code == 1


class TestVideoCLIAssemble:
    """Tests for vclaw video assemble command."""

    @patch("subprocess.run")
    def test_assemble_success(self, mock_run):
        """Successful video assemble returns parsed JSON."""
        mock_run.return_value = make_completed_process(
            returncode=0,
            stdout=json.dumps({"video_url": "https://cdn.example.com/video.mp4", "status": "ready"}),
        )
        client = VideoClawCLIClient()
        result = client.video_assemble("proj_123")

        assert result["video_url"] == "https://cdn.example.com/video.mp4"
        assert result["status"] == "ready"
        args = mock_run.call_args[0][0]
        assert args[0] == "vclaw"
        assert args[1] == "video"
        assert args[2] == "assemble"
        assert "proj_123" in args

    @patch("subprocess.run")
    def test_assemble_system_error(self, mock_run):
        """Exit code 2 on assemble raises error."""
        mock_run.return_value = make_completed_process(
            returncode=2,
            stdout="",
            stderr="Encoding failed",
        )
        client = VideoClawCLIClient()
        with pytest.raises(VideoClawCLIError) as exc_info:
            client.video_assemble("proj_123")

        assert exc_info.value.exit_code == 2


class TestVideoCLITimeout:
    """Tests for CLI timeout handling."""

    @patch("subprocess.run")
    def test_timeout_raises_error(self, mock_run):
        """Subprocess timeout raises VideoClawCLIError."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="vclaw", timeout=300)
        client = VideoClawCLIClient(timeout=300)
        with pytest.raises(VideoClawCLIError) as exc_info:
            client.video_create("Test")

        assert "timed out" in str(exc_info.value).lower()


class TestVideoCLIRobustness:
    """Tests for CLI robustness and edge cases."""

    @patch("subprocess.run")
    def test_invalid_json_output_raises_error(self, mock_run):
        """Non-JSON stdout raises VideoClawCLIError."""
        mock_run.return_value = make_completed_process(
            returncode=0,
            stdout="not valid json",
        )
        client = VideoClawCLIClient()
        with pytest.raises(VideoClawCLIError):
            client.video_create("Test")

    @patch("subprocess.run")
    def test_custom_timeout(self, mock_run):
        """Custom timeout is passed to subprocess."""
        mock_run.return_value = make_completed_process(
            returncode=0,
            stdout=json.dumps({"project_id": "proj_123"}),
        )
        client = VideoClawCLIClient(timeout=600)
        client.video_create("Test")

        assert mock_run.call_args[1]["timeout"] == 600

    @patch("subprocess.run")
    def test_empty_project_name_still_calls_cli(self, mock_run):
        """Empty project name is passed through (CLI validates)."""
        mock_run.return_value = make_completed_process(
            returncode=1,
            stdout="",
            stderr="Name required",
        )
        client = VideoClawCLIClient()
        with pytest.raises(VideoClawCLIError):
            client.video_create("")

        mock_run.assert_called_once()
