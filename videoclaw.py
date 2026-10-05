"""VideoClaw CLI wrapper — minimal subprocess-based client and API endpoint."""
import json
import subprocess
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class CreateRequest(BaseModel):
    name: str


class VideoClawError(Exception):
    """Raised when vclaw CLI fails."""


class VideoClawClient:
    """Wraps subprocess calls to the vclaw CLI."""

    def __init__(self, cli_path: str = "vclaw", timeout: int = 300):
        self.cli_path = cli_path
        self.timeout = timeout

    def _run(self, args: list[str]) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                [self.cli_path] + args,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise VideoClawError(f"CLI timed out after {self.timeout}s") from e
        except FileNotFoundError as e:
            raise VideoClawError(f"CLI not found: {self.cli_path}") from e

        if result.returncode != 0:
            raise VideoClawError(
                f"CLI exited {result.returncode}: {result.stderr.strip()}"
            )

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise VideoClawError(f"Invalid JSON: {result.stdout[:200]}") from e

    def create_project(self, name: str) -> Dict[str, Any]:
        """Create a new video project."""
        return self._run(["video", "create", name])

    def get_status(self, project: str) -> Dict[str, Any]:
        """Get project status."""
        return self._run(["video", "status", project])

    def assemble(self, project: str) -> Dict[str, Any]:
        """Assemble final video."""
        return self._run(["video", "assemble", project])


@app.post("/api/v1/videoclaw/create")
def create_videoclaw_project(req: CreateRequest):
    """Create a VideoClaw project via CLI."""
    client = VideoClawClient()
    try:
        return client.create_project(req.name)
    except VideoClawError as e:
        raise HTTPException(status_code=400, detail=str(e))
