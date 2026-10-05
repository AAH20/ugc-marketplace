"""GTM API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from ugc_marketplace.gtm.agents.channel_analyzer import ChannelAnalyzerAgent
from ugc_marketplace.gtm.agents.competitor_researcher import CompetitorResearcherAgent
from ugc_marketplace.gtm.agents.launch_strategist import LaunchStrategistAgent
from ugc_marketplace.gtm.models import (
    CampaignAnalytics,
    CompetitorAnalysis,
    LaunchCampaign,
    LaunchCampaignCreate,
    LaunchChannel,
)

router = APIRouter()

# In-memory store for demo (replace with DB in production)
_campaigns: dict[uuid.UUID, LaunchCampaign] = {}


@router.post("/campaigns", response_model=LaunchCampaign, status_code=status.HTTP_201_CREATED)
async def create_campaign(campaign: LaunchCampaignCreate) -> LaunchCampaign:
    """Create a new launch campaign."""
    new_campaign = LaunchCampaign(
        name=campaign.name,
        description=campaign.description,
        channels=campaign.channels,
        content_type=campaign.content_type,
        target_audience=campaign.target_audience,
        budget=campaign.budget,
        scheduled_at=campaign.scheduled_at,
        metadata=campaign.metadata,
    )
    _campaigns[new_campaign.id] = new_campaign
    return new_campaign


@router.get("/campaigns/{campaign_id}", response_model=LaunchCampaign)
async def get_campaign(campaign_id: uuid.UUID) -> LaunchCampaign:
    """Get a campaign by ID."""
    if campaign_id not in _campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaigns[campaign_id]


@router.post("/campaigns/{campaign_id}/strategy")
async def generate_strategy(campaign_id: uuid.UUID) -> dict:
    """Generate launch strategy for a campaign."""
    if campaign_id not in _campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign = _campaigns[campaign_id]
    agent = LaunchStrategistAgent()
    result = await agent.execute(campaign)

    if not result.success or result.data is None:
        raise HTTPException(status_code=500, detail=result.error or "Strategy generation failed")

    return result.data


@router.post("/campaigns/{campaign_id}/analyze")
async def analyze_campaign(campaign_id: uuid.UUID, analytics: CampaignAnalytics) -> dict:
    """Analyze campaign performance."""
    if campaign_id not in _campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")

    agent = ChannelAnalyzerAgent()
    result = await agent.execute(analytics)

    if not result.success or result.data is None:
        raise HTTPException(status_code=500, detail=result.error or "Analysis failed")

    return result.data


@router.post("/competitors/analyze")
async def analyze_competitor(competitor: CompetitorAnalysis) -> dict:
    """Analyze a competitor's GTM strategy."""
    agent = CompetitorResearcherAgent()
    result = await agent.execute(competitor)

    if not result.success or result.data is None:
        raise HTTPException(status_code=500, detail=result.error or "Competitor analysis failed")

    return result.data


@router.get("/channels")
async def list_channels() -> list[str]:
    """List all supported launch channels."""
    return [c.value for c in LaunchChannel]
