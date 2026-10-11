"""Coverage-gap tests for :mod:`ugc_marketplace.agents.quality_scoring`.

The whole ``agents`` package has zero references anywhere under ``tests/``.
These tests exercise the deterministic, LLM-free scoring paths of the four
scorer agents (readability, originality, seo, engagement) through their real
public ``score`` coroutine and the private calculators they delegate to.
"""

from __future__ import annotations

import pytest

from ugc_marketplace.agents.quality_scoring.engagement import EngagementScorerAgent
from ugc_marketplace.agents.quality_scoring.originality import OriginalityScorerAgent
from ugc_marketplace.agents.quality_scoring.readability import ReadabilityScorerAgent
from ugc_marketplace.agents.quality_scoring.seo import SEOScorerAgent
from ugc_marketplace.models.schemas import ScoreDimension, ScoreLevel

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Readability
# ---------------------------------------------------------------------------


def test_count_syllables_known_words():
    agent = ReadabilityScorerAgent()
    assert agent._count_syllables("cat") == 1
    assert agent._count_syllables("hello") == 2
    assert agent._count_syllables("make") == 1  # trailing silent 'e' removed
    assert agent._count_syllables("nth") == 1  # no vowels → clamped to 1


async def test_readability_score_returns_dimension_score():
    agent = ReadabilityScorerAgent()
    result = await agent.score("The cat sat on the mat. The dog ran fast.")

    assert result.success is True
    assert result.data.dimension is ScoreDimension.READABILITY
    assert 0.0 <= result.data.score <= 1.0
    assert result.data.level in {ScoreLevel.LOW, ScoreLevel.MEDIUM, ScoreLevel.HIGH}


async def test_readability_empty_content_does_not_crash():
    result = await ReadabilityScorerAgent().score("")

    assert result.success is True
    # Empty content must not be scored as perfectly readable.
    assert result.data.score == 0.0
    assert result.data.level is ScoreLevel.LOW


# ---------------------------------------------------------------------------
# SEO
# ---------------------------------------------------------------------------


async def test_seo_rewards_structure_and_keywords():
    agent = SEOScorerAgent()
    plain = await agent.score("just some words here")
    rich = await agent.score(
        "# Heading\n\nsee [link](https://x) and ![img](https://y)\n\n" + "word " * 320,
        context={"target_keywords": ["word"], "meta_description": "desc"},
    )

    assert plain.success and rich.success
    assert rich.data.dimension is ScoreDimension.SEO
    assert rich.data.score > plain.data.score


async def test_seo_score_is_capped_at_one():
    result = await SEOScorerAgent().score(
        "# H\n[link](https://x)\n![img](https://y)\n" + "word " * 400,
        context={"target_keywords": ["word"], "meta_description": "d"},
    )
    assert result.data.score <= 1.0


# ---------------------------------------------------------------------------
# Engagement
# ---------------------------------------------------------------------------


async def test_engagement_rewards_question_cta_and_emotion():
    agent = EngagementScorerAgent()
    plain = await agent.score("just some words here")
    engaging = await agent.score("Amazing! Click here to subscribe, don't you agree?")

    assert plain.success and engaging.success
    assert engaging.data.dimension is ScoreDimension.ENGAGEMENT
    assert engaging.data.score > plain.data.score


# ---------------------------------------------------------------------------
# Originality
# ---------------------------------------------------------------------------


async def test_originality_recognises_percentage_data_figure():
    """Regression: the ``\\d+%`` alternative never matched because of a
    misplaced trailing ``\\b`` (a ``%`` is not a word char, so no boundary
    exists after it).  A percentage figure must count as data."""
    agent = OriginalityScorerAgent()

    # Every word unique (uniqueness_ratio == 1.0) plus a first-person
    # perspective; the only remaining signal is the "50%" data figure.
    #   base 0.5 + perspective 0.2 + data 0.15 == 0.85  (HIGH)
    #   without the data contribution it is only 0.7    (MEDIUM)
    result = await agent.score("I think 50% matters")

    assert result.success
    assert result.data.dimension is ScoreDimension.ORIGINALITY
    assert result.data.score >= 0.8


async def test_originality_recognises_phrase_data_and_examples():
    agent = OriginalityScorerAgent()
    result = await agent.score("In my opinion for example a study shows the data.")

    assert result.success
    assert result.data.score > 0.0
