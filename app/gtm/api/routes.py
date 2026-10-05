"""GTM campaign routes — database-backed, no in-memory store."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gtm.db import get_gtm_session
from app.gtm.models import LaunchCampaign
from app.gtm.repository import CampaignRepository
from app.gtm.schemas import CampaignCreate, CampaignResponse, CampaignUpdate

router = APIRouter(prefix="/api/v1/gtm", tags=["gtm"])


@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(payload: CampaignCreate, db: AsyncSession = Depends(get_gtm_session)):
    repo = CampaignRepository(db)
    campaign = await repo.create(payload.model_dump(exclude_unset=True))
    return campaign


@router.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns(db: AsyncSession = Depends(get_gtm_session)):
    repo = CampaignRepository(db)
    return await repo.list()


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_gtm_session)):
    repo = CampaignRepository(db)
    campaign = await repo.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID, payload: CampaignUpdate, db: AsyncSession = Depends(get_gtm_session)
):
    repo = CampaignRepository(db)
    campaign = await repo.update(campaign_id, payload.model_dump(exclude_unset=True))
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_gtm_session)):
    repo = CampaignRepository(db)
    deleted = await repo.delete(campaign_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Campaign not found")
