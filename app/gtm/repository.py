"""Async CRUD repository for LaunchCampaign."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gtm.models import LaunchCampaign


class CampaignRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _map_in(data: dict) -> dict:
        """Map schema field names to model attribute names."""
        mapped = dict(data)
        if "metadata_" in mapped:
            mapped["extra_metadata"] = mapped.pop("metadata_")
        return mapped

    async def create(self, data: dict) -> LaunchCampaign:
        campaign = LaunchCampaign(**self._map_in(data))
        self.session.add(campaign)
        await self.session.commit()
        await self.session.refresh(campaign)
        return campaign

    async def get(self, campaign_id: UUID) -> LaunchCampaign | None:
        result = await self.session.execute(
            select(LaunchCampaign).where(LaunchCampaign.id == campaign_id)
        )
        return result.scalar_one_or_none()

    async def list(self) -> list[LaunchCampaign]:
        result = await self.session.execute(select(LaunchCampaign))
        return list(result.scalars().all())

    async def update(self, campaign_id: UUID, data: dict) -> LaunchCampaign | None:
        campaign = await self.get(campaign_id)
        if not campaign:
            return None
        for key, value in self._map_in(data).items():
            setattr(campaign, key, value)
        await self.session.commit()
        await self.session.refresh(campaign)
        return campaign

    async def delete(self, campaign_id: UUID) -> bool:
        campaign = await self.get(campaign_id)
        if not campaign:
            return False
        await self.session.delete(campaign)
        await self.session.commit()
        return True
