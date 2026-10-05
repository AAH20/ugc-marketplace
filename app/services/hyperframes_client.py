"""HyperFrames cloud rendering API client."""
import json
import math
import time
from pathlib import Path
from typing import Any

import httpx


class HyperFramesError(Exception):
    """Custom exception for HyperFrames API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class RenderStatus:
    """Render status constants."""

    QUEUED = "queued"
    RENDERING = "rendering"
    COMPLETE = "complete"
    FAILED = "failed"


class HyperFramesClient:
    """Client for HyperFrames cloud rendering API.

    Supports:
    - POST /v3/assets (upload zip)
    - POST /v3/hyperframes/renders (submit render)
    - GET /v3/hyperframes/renders/{id} (poll status)
    - GET /v3/hyperframes/renders/{id}/download (download result)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.hyperframes.io",
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def upload_asset(self, zip_path: str) -> dict[str, Any]:
        """Upload a zip file as a render asset.

        Args:
            zip_path: Path to the zip file to upload.

        Returns:
            Asset data including id, filename, size_bytes, status.

        Raises:
            FileNotFoundError: If zip file doesn't exist.
            HyperFramesError: On API or network errors.
        """
        path = Path(zip_path)
        if not path.exists():
            raise FileNotFoundError(f"Zip file not found: {zip_path}")

        try:
            with open(path, "rb") as f:
                files = {"file": (path.name, f, "application/zip")}
                response = self._client.post("/v3/assets", files=files)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise HyperFramesError(
                f"Upload failed: {e.response.status_code} - {e.response.text}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise HyperFramesError(f"Network error during upload: {e}") from e

    def submit_render(
        self,
        asset_id: str,
        variables: dict[str, Any] | list[dict[str, Any]],
        resolution: str = "1080p",
        fps: int = 30,
    ) -> dict[str, Any]:
        """Submit a render job.

        Args:
            asset_id: The asset ID to render.
            variables: Render variables (dict for single, list for batch).
            resolution: Output resolution (e.g., "1080p", "720p", "4k").
            fps: Frames per second (30 or 60).

        Returns:
            Render job data including id, status, variables.

        Raises:
            HyperFramesError: On API or network errors.
        """
        payload = {
            "asset_id": asset_id,
            "variables": variables,
            "quality": {"resolution": resolution, "fps": fps},
        }

        try:
            response = self._client.post("/v3/hyperframes/renders", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HyperFramesError(
                f"Render submission failed: {e.response.status_code} - {e.response.text}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise HyperFramesError(f"Network error during render submission: {e}") from e

    def get_render_status(self, render_id: str) -> dict[str, Any]:
        """Get the current status of a render job.

        Args:
            render_id: The render job ID.

        Returns:
            Render status data including id, status, progress.

        Raises:
            HyperFramesError: On API or network errors.
        """
        try:
            response = self._client.get(f"/v3/hyperframes/renders/{render_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HyperFramesError(
                f"Status check failed: {e.response.status_code} - {e.response.text}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise HyperFramesError(f"Network error during status check: {e}") from e

    def poll_render(
        self,
        render_id: str,
        poll_interval: float = 5.0,
        max_attempts: int = 60,
    ) -> dict[str, Any]:
        """Poll render status until completion or timeout.

        Args:
            render_id: The render job ID.
            poll_interval: Seconds between polls.
            max_attempts: Maximum number of poll attempts.

        Returns:
            Final render status data.

        Raises:
            HyperFramesError: On timeout, failure, or API errors.
        """
        for attempt in range(max_attempts):
            status = self.get_render_status(render_id)

            if status.get("status") == RenderStatus.COMPLETE:
                return status

            if status.get("status") == RenderStatus.FAILED:
                error_msg = status.get("error", "Unknown error")
                raise HyperFramesError(f"Render failed: {error_msg}")

            if attempt < max_attempts - 1:
                time.sleep(poll_interval)

        raise HyperFramesError(
            f"Render polling timeout after {max_attempts} attempts",
        )

    def download_render(self, render_id: str, output_path: str) -> None:
        """Download a completed render.

        Args:
            render_id: The render job ID.
            output_path: Local file path to save the download.

        Raises:
            HyperFramesError: On API or network errors.
        """
        try:
            response = self._client.get(f"/v3/hyperframes/renders/{render_id}/download")
            response.raise_for_status()

            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(response.content)
        except httpx.HTTPStatusError as e:
            raise HyperFramesError(
                f"Download failed: {e.response.status_code} - {e.response.text}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise HyperFramesError(f"Network error during download: {e}") from e

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "HyperFramesClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
