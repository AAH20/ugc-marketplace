"""Tests for VideoClaw CLI wrapper with mocked subprocess."""
import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from videoclaw import VideoClawClient, VideoClawError, app


def make_result(returncode=0, stdout="", stderr=""):
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


class TestVideoClawClient:
    """Tests for VideoClawClient subprocess wrapper."""

    @patch("subprocess.run")
    def test_create_project_success(self, mock_run):
        mock_run.return_value = make_result(
            stdout=json.dumps({"project_id": "proj_123", "status": "created"})
        )
        client = VideoClawClient()
        result = client.create_project("My Video")
        assert result["project_id"] == "proj_123"
        assert result["status"] == "created"

    @patch("subprocess.run")
    def test_create_project_failure(self, mock_run):
        mock_run.return_value = make_result(returncode=1, stderr="Invalid name")
        client = VideoClawClient()
        with pytest.raises(VideoClawError):
            client.create_project("")

    @patch("subprocess.run")
    def test_get_status_success(self, mock_run):
        mock_run.return_value = make_result(
            stdout=json.dumps({"project_id": "proj_123", "status": "processing"})
        )
        client = VideoClawClient()
        result = client.get_status("proj_123")
        assert result["status"] == "processing"

    @patch("subprocess.run")
    def test_assemble_success(self, mock_run):
        mock_run.return_value = make_result(
            stdout=json.dumps({"video_url": "https://cdn.example.com/v.mp4", "status": "ready"})
        )
        client = VideoClawClient()
        result = client.assemble("proj_123")
        assert result["video_url"] == "https://cdn.example.com/v.mp4"

    @patch("subprocess.run")
    def test_timeout_raises_error(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="vclaw", timeout=30)
        client = VideoClawClient(timeout=30)
        with pytest.raises(VideoClawError):
            client.create_project("Test")


class TestVideoClawEndpoint:
    """Tests for the /api/v1/videoclaw/create endpoint."""

    @patch("subprocess.run")
    def test_create_endpoint_success(self, mock_run):
        mock_run.return_value = make_result(
            stdout=json.dumps({"project_id": "proj_123", "status": "created"})
        )
        client = TestClient(app)
        resp = client.post("/api/v1/videoclaw/create", json={"name": "My Video"})
        assert resp.status_code == 200
        assert resp.json()["project_id"] == "proj_123"

    @patch("subprocess.run")
    def test_create_endpoint_failure(self, mock_run):
        mock_run.return_value = make_result(returncode=1, stderr="Bad input")
        client = TestClient(app)
        resp = client.post("/api/v1/videoclaw/create", json={"name": ""})
        assert resp.status_code == 400
