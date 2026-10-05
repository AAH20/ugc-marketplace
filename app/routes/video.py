"""Video generation API routes."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.gtm.db import get_gtm_session
from app.repositories.video import (
    VideoRequestRepository,
    VideoResultRepository,
    VideoQualityMetricsRepository,
    VideoTemplateRepository,
)
from app.schemas.video import (
    VideoRequestCreate,
    VideoRequestUpdate,
    VideoRequestResponse,
    VideoResultCreate,
    VideoResultUpdate,
    VideoResultResponse,
    VideoQualityMetricsCreate,
    VideoQualityMetricsResponse,
    VideoTemplateCreate,
    VideoTemplateUpdate,
    VideoTemplateResponse,
)
from app.models.video import GenerationStatus

router = APIRouter(prefix="/api/v1/video", tags=["video"])


# --- Video Generation Requests ---

@router.post("/requests", response_model=VideoRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_video_request(
    data: VideoRequestCreate,
    session: AsyncSession = Depends(get_gtm_session),
):
    """Create a new video generation request."""
    repo = VideoRequestRepository(session)
    request = await repo.create(data.model_dump())
    return request


@router.get("/requests", response_model=list[VideoRequestResponse])
async def list_video_requests(
    user_id: str | None = None,
    status: GenerationStatus | None = None,
    session: AsyncSession = Depends(get_gtm_session),
):
    """List video generation requests with optional filters."""
    repo = VideoRequestRepository(session)
    return await repo.list(user_id=user_id, status=status)


@router.get("/requests/{request_id}", response_model=VideoRequestResponse)
async def get_video_request(
    request_id: int,
    session: AsyncSession = Depends(get_gtm_session),
):
    """Get a specific video generation request."""
    repo = VideoRequestRepository(session)
    request = await repo.get(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Video request not found")
    return request


@router.patch("/requests/{request_id}", response_model=VideoRequestResponse)
async def update_video_request(
    request_id: int,
    data: VideoRequestUpdate,
    session: AsyncSession = Depends(get_gtm_session),
):
    """Update a video generation request."""
    repo = VideoRequestRepository(session)
    updated = await repo.update(request_id, data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Video request not found")
    return updated


@router.delete("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video_request(
    request_id: int,
    session: AsyncSession = Depends(get_gtm_session),
):
    """Delete a video generation request."""
    repo = VideoRequestRepository(session)
    deleted = await repo.delete(request_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Video request not found")


# --- Video Generation Results ---

@router.post("/results", response_model=VideoResultResponse, status_code=status.HTTP_201_CREATED)
async def create_video_result(
    data: VideoResultCreate,
    session: AsyncSession = Depends(get_gtm_session),
):
    """Create a video generation result."""
    repo = VideoResultRepository(session)
    result = await repo.create(data.model_dump())
    return result


@router.get("/results", response_model=list[VideoResultResponse])
async def list_video_results(
    request_id: int | None = None,
    session: AsyncSession = Depends(get_gtm_session),
):
    """List video generation results with optional request filter."""
    repo = VideoResultRepository(session)
    return await repo.list(request_id=request_id)


@router.get("/results/{result_id}", response_model=VideoResultResponse)
async def get_video_result(
    result_id: int,
    session: AsyncSession = Depends(get_gtm_session),
):
    """Get a specific video generation result."""
    repo = VideoResultRepository(session)
    result = await repo.get(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Video result not found")
    return result


@router.patch("/results/{result_id}", response_model=VideoResultResponse)
async def update_video_result(
    result_id: int,
    data: VideoResultUpdate,
    session: AsyncSession = Depends(get_gtm_session),
):
    """Update a video generation result."""
    repo = VideoResultRepository(session)
    updated = await repo.update(result_id, data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Video result not found")
    return updated


@router.delete("/results/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video_result(
    result_id: int,
    session: AsyncSession = Depends(get_gtm_session),
):
    """Delete a video generation result."""
    repo = VideoResultRepository(session)
    deleted = await repo.delete(result_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Video result not found")


# --- Video Quality Metrics ---

@router.post("/quality-metrics", response_model=VideoQualityMetricsResponse, status_code=status.HTTP_201_CREATED)
async def create_quality_metrics(
    data: VideoQualityMetricsCreate,
    session: AsyncSession = Depends(get_gtm_session),
):
    """Create quality metrics for a video result."""
    repo = VideoQualityMetricsRepository(session)
    metrics = await repo.create(data.model_dump())
    return metrics


@router.get("/quality-metrics/{metrics_id}", response_model=VideoQualityMetricsResponse)
async def get_quality_metrics(
    metrics_id: int,
    session: AsyncSession = Depends(get_gtm_session),
):
    """Get specific quality metrics."""
    repo = VideoQualityMetricsRepository(session)
    metrics = await repo.get(metrics_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Quality metrics not found")
    return metrics


@router.get("/quality-metrics/result/{result_id}", response_model=VideoQualityMetricsResponse)
async def get_quality_metrics_by_result(
    result_id: int,
    session: AsyncSession = Depends(get_gtm_session),
):
    """Get quality metrics by result ID."""
    repo = VideoQualityMetricsRepository(session)
    metrics = await repo.get_by_result_id(result_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Quality metrics not found")
    return metrics


# --- Video Templates ---

@router.post("/templates", response_model=VideoTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_video_template(
    data: VideoTemplateCreate,
    session: AsyncSession = Depends(get_gtm_session),
):
    """Create a new video template."""
    repo = VideoTemplateRepository(session)
    template = await repo.create(data.model_dump())
    return template


@router.get("/templates", response_model=list[VideoTemplateResponse])
async def list_video_templates(
    category: str | None = None,
    active_only: bool = False,
    session: AsyncSession = Depends(get_gtm_session),
):
    """List video templates with optional filters."""
    repo = VideoTemplateRepository(session)
    return await repo.list(category=category, active_only=active_only)


@router.get("/templates/{template_id}", response_model=VideoTemplateResponse)
async def get_video_template(
    template_id: int,
    session: AsyncSession = Depends(get_gtm_session),
):
    """Get a specific video template."""
    repo = VideoTemplateRepository(session)
    template = await repo.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Video template not found")
    return template


@router.patch("/templates/{template_id}", response_model=VideoTemplateResponse)
async def update_video_template(
    template_id: int,
    data: VideoTemplateUpdate,
    session: AsyncSession = Depends(get_gtm_session),
):
    """Update a video template."""
    repo = VideoTemplateRepository(session)
    updated = await repo.update(template_id, data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Video template not found")
    return updated


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video_template(
    template_id: int,
    session: AsyncSession = Depends(get_gtm_session),
):
    """Delete a video template."""
    repo = VideoTemplateRepository(session)
    deleted = await repo.delete(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Video template not found")
