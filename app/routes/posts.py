"""API routes for triggering social platform posts."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.integrations import (
    ProductHuntIntegration,
    HackerNewsIntegration,
    RedditIntegration,
    TwitterIntegration,
)

router = APIRouter(prefix="/api/v1", tags=["posts"])


class PostContent(BaseModel):
    """Content for a social media post."""
    text: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    name: Optional[str] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    subreddit: Optional[str] = None
    media_ids: Optional[list[str]] = None
    topics: Optional[list[str]] = None


class PostResponse(BaseModel):
    """Response from a successful post."""
    id: str
    platform: str
    title: Optional[str] = None
    text: Optional[str] = None
    url: Optional[str] = None


# Platform integration registry - maps platform name to module attribute name
INTEGRATION_PLATFORMS = {
    "product_hunt": "ProductHuntIntegration",
    "hacker_news": "HackerNewsIntegration",
    "reddit": "RedditIntegration",
    "twitter": "TwitterIntegration",
}


def get_integration(platform: str):
    """Get integration instance for a platform."""
    class_name = INTEGRATION_PLATFORMS.get(platform)
    if not class_name:
        raise HTTPException(status_code=404, detail=f"Unknown platform: {platform}")

    integration_class = globals()[class_name]
    return integration_class()


@router.post("/posts/{platform}", response_model=PostResponse)
async def create_post(platform: str, content: PostContent):
    """Trigger a post to a social platform."""
    integration = get_integration(platform)
    try:
        result = await integration.post(content.model_dump(exclude_none=True))
        return PostResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Integration error: {str(e)}")


@router.post("/twitter/post", response_model=PostResponse)
async def post_to_twitter(content: PostContent):
    """Post a tweet via Twitter/X."""
    integration = TwitterIntegration()
    try:
        result = await integration.post(content.model_dump(exclude_none=True))
        return PostResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Twitter error: {str(e)}")


@router.get("/integrations/{platform}/health")
async def integration_health(platform: str):
    """Check health of a platform integration."""
    integration = get_integration(platform)
    try:
        result = await integration.health_check()
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Health check failed: {str(e)}")
