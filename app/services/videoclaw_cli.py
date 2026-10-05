"""VideoClaw CLI client — drives the vclaw CLI via subprocess."""
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class VideoClawCLIError(Exception):
    """Error raised when vclaw CLI returns a non-zero exit code."""

    def __init__(self, message: str, exit_code: int, stderr: str = ""):
        super().__init__(message)
        self.exit_code = exit_code
        self.stderr = stderr


class ExitCode:
    """VideoClaw CLI exit codes."""
    SUCCESS = 0
    BAD_INPUT = 1
    SYSTEM_ERROR = 2
    GATED = 3


class VideoClawCLIClient:
    """Client that drives the VideoClaw CLI via subprocess.

    Supports three commands:
        - vclaw video create <name> [options]
        - vclaw video produce <project_id> [options]
        - vclaw video assemble <project_id> [options]
    """

    def __init__(
        self,
        cli_path: str = "vclaw",
        timeout: int = 300,
        default_provider: Optional[str] = None,
    ):
        self.cli_path = cli_path
        self.timeout = timeout
        self.default_provider = default_provider

    def _run_cli(self, args: List[str]) -> Dict[str, Any]:
        """Execute the vclaw CLI and parse JSON output.

        Args:
            args: CLI arguments (without the binary name).

        Returns:
            Parsed JSON response from the CLI.

        Raises:
            VideoClawCLIError: If the CLI returns a non-zero exit code
                or produces invalid JSON.
        """
        cmd = [self.cli_path] + args
        logger.debug("Running CLI command: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise VideoClawCLIError(
                f"CLI timed out after {self.timeout}s",
                exit_code=-1,
            ) from e
        except FileNotFoundError as e:
            raise VideoClawCLIError(
                f"CLI binary not found: {self.cli_path}",
                exit_code=-1,
            ) from e

        if result.returncode != ExitCode.SUCCESS:
            raise VideoClawCLIError(
                f"CLI exited with code {result.returncode}: {result.stderr.strip()}",
                exit_code=result.returncode,
                stderr=result.stderr.strip(),
            )

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise VideoClawCLIError(
                f"Invalid JSON from CLI: {result.stdout[:200]}",
                exit_code=result.returncode,
            ) from e

    def video_create(self, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new video project.

        Args:
            name: Project name.
            **kwargs: Additional CLI options (e.g., resolution, duration).

        Returns:
            Parsed JSON with project_id and status.
        """
        args = ["video", "create", name]
        args.extend(self._build_options(kwargs))
        return self._run_cli(args)

    def video_produce(self, project_id: str, **kwargs) -> Dict[str, Any]:
        """Start video production for a project.

        Args:
            project_id: The project ID from video_create.
            **kwargs: Additional CLI options (e.g., provider, quality).

        Returns:
            Parsed JSON with job_id and status.
        """
        args = ["video", "produce", project_id]
        args.extend(self._build_options(kwargs))
        return self._run_cli(args)

    def video_assemble(self, project_id: str, **kwargs) -> Dict[str, Any]:
        """Assemble the final video from produced segments.

        Args:
            project_id: The project ID.
            **kwargs: Additional CLI options.

        Returns:
            Parsed JSON with video_url and status.
        """
        args = ["video", "assemble", project_id]
        args.extend(self._build_options(kwargs))
        return self._run_cli(args)

    def _build_options(self, kwargs: Dict[str, Any]) -> List[str]:
        """Convert kwargs dict to CLI flag arguments."""
        args = []
        for key, value in kwargs.items():
            flag = f"--{key.replace('_', '-')}"
            if isinstance(value, bool):
                if value:
                    args.append(flag)
            else:
                args.extend([flag, str(value)])
        return args
