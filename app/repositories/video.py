"""Async CRUD repositories for video generation."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.video import (
    VideoGenerationRequest,
    VideoGenerationResult,
    VideoQualityMetrics,
    VideoTemplate,
    GenerationStatus,
)


class VideoRequestRepository:
    """Repository for VideoGenerationRequest CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> VideoGenerationRequest:
        request = VideoGenerationRequest(**data)
        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def get(self, request_id: int) -> Optional[VideoGenerationRequest]:
        result = await self.session.execute(
            select(VideoGenerationRequest).where(VideoGenerationRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        user_id: Optional[str] = None,
        status: Optional[GenerationStatus] = None,
    ) -> list[VideoGenerationRequest]:
        query = select(VideoGenerationRequest)
        if user_id is not None:
            query = query.where(VideoGenerationRequest.user_id == user_id)
        if status is not None:
            query = query.where(VideoGenerationRequest.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, request_id: int, data: dict) -> Optional[VideoGenerationRequest]:
        request = await self.get(request_id)
        if not request:
            return None
        for key, value in data.items():
            setattr(request, key, value)
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def delete(self, request_id: int) -> bool:
        request = await self.get(request_id)
        if not request:
            return False
        await self.session.delete(request)
        await self.session.commit()
        return True


class VideoResultRepository:
    """Repository for VideoGenerationResult CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> VideoGenerationResult:
        result = VideoGenerationResult(**data)
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return result

    async def get(self, result_id: int) -> Optional[VideoGenerationResult]:
        result = await self.session.execute(
            select(VideoGenerationResult).where(VideoGenerationResult.id == result_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        request_id: Optional[int] = None,
    ) -> list[VideoGenerationResult]:
        query = select(VideoGenerationResult)
        if request_id is not None:
            query = query.where(VideoGenerationResult.request_id == request_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, result_id: int, data: dict) -> Optional[VideoGenerationResult]:
        result = await self.get(result_id)
        if not result:
            return None
        for key, value in data.items():
            setattr(result, key, value)
        await self.session.commit()
        await self.session.refresh(result)
        return result

    async def delete(self, result_id: int) -> bool:
        result = await self.get(result_id)
        if not result:
            return False
        await self.session.delete(result)
        await self.session.commit()
        return True


class VideoQualityMetricsRepository:
    """Repository for VideoQualityMetrics CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> VideoQualityMetrics:
        metrics = VideoQualityMetrics(**data)
        self.session.add(metrics)
        await self.session.commit()
        await self.session.refresh(metrics)
        return metrics

    async def get(self, metrics_id: int) -> Optional[VideoQualityMetrics]:
        result = await self.session.execute(
            select(VideoQualityMetrics).where(VideoQualityMetrics.id == metrics_id)
        )
        return result.scalar_one_or_none()

    async def get_by_result_id(self, result_id: int) -> Optional[VideoQualityMetrics]:
        result = await self.session.execute(
            select(VideoQualityMetrics).where(VideoQualityMetrics.result_id == result_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        result_id: Optional[int] = None,
    ) -> list[VideoQualityMetrics]:
        query = select(VideoQualityMetrics)
        if result_id is not None:
            query = query.where(VideoQualityMetrics.result_id == result_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, metrics_id: int, data: dict) -> Optional[VideoQualityMetrics]:
        metrics = await self.get(metrics_id)
        if not metrics:
            return None
        for key, value in data.items():
            setattr(metrics, key, value)
        await self.session.commit()
        await self.session.refresh(metrics)
        return metrics

    async def delete(self, metrics_id: int) -> bool:
        metrics = await self.get(metrics_id)
        if not metrics:
            return False
        await self.session.delete(metrics)
        await self.session.commit()
        return True


class VideoTemplateRepository:
    """Repository for VideoTemplate CRUD operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> VideoTemplate:
        template = VideoTemplate(**data)
        self.session.add(template)
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def get(self, template_id: int) -> Optional[VideoTemplate]:
        result = await self.session.execute(
            select(VideoTemplate).where(VideoTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        category: Optional[str] = None,
        active_only: bool = False,
    ) -> list[VideoTemplate]:
        query = select(VideoTemplate)
        if category is not None:
            query = query.where(VideoTemplate.category == category)
        if active_only:
            query = query.where(VideoTemplate.is_active == True)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, template_id: int, data: dict) -> Optional[VideoTemplate]:
        template = await self.get(template_id)
        if not template:
            return None
        for key, value in data.items():
            setattr(template, key, value)
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def delete(self, template_id: int) -> bool:
        template = await self.get(template_id)
        if not template:
            return False
        await self.session.delete(template)
        await self.session.commit()
        return True
