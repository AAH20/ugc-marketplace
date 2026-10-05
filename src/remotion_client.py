"""Python wrapper for Remotion client (mirrors TypeScript interface)."""
from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class RemotionClientConfig:
    """Remotion client configuration."""
    region: str
    functionName: str
    serveUrl: str
    credentials: Optional[dict[str, str]] = None


@dataclass
class RenderParams:
    """Render parameters."""
    composition: str
    inputProps: dict[str, Any]
    format: Optional[str] = None
    imageFormat: Optional[str] = None
    quality: Optional[int] = None
    scale: Optional[float] = None
    frameRange: Optional[tuple[int, int]] = None
    envVariables: Optional[dict[str, str]] = None
    maxRetries: Optional[int] = None
    timeoutInMilliseconds: Optional[int] = None


@dataclass
class RenderResult:
    """Render result."""
    renderId: str
    bucketName: str


class RemotionClient:
    """Client for Remotion Lambda rendering."""

    def __init__(self, config: RemotionClientConfig):
        self.config = config

    async def render(self, params: RenderParams) -> RenderResult:
        """Render a composition on Lambda."""
        # This is a Python wrapper - actual implementation calls the TypeScript client
        raise NotImplementedError("Use the TypeScript RemotionClient for actual rendering")

    async def poll(self, renderId: str, bucketName: str) -> dict:
        """Poll render progress."""
        raise NotImplementedError("Use the TypeScript RemotionClient for actual rendering")

    async def download(self, renderId: str, bucketName: str, outputPath: str) -> str:
        """Download a completed render."""
        raise NotImplementedError("Use the TypeScript RemotionClient for actual rendering")
