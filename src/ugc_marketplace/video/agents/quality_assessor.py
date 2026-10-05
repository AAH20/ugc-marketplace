"""Video Quality Assessor Agent — evaluates video quality and engagement potential."""

from __future__ import annotations

from typing import Any

from ugc_marketplace.video.agents.base import BaseVideoAgent
from ugc_marketplace.video.models import VideoGenerationResult, VideoQualityMetrics


class VideoQualityAssessorAgent(BaseVideoAgent[VideoGenerationResult]):
    """Agent that evaluates video quality and predicts engagement.

    Analyzes video output across multiple dimensions: visual quality,
    audio quality, pacing, engagement prediction, and brand consistency.
    """

    async def _execute(self, input_data: VideoGenerationResult) -> dict[str, Any]:
        """Execute video quality assessment.

        Args:
            input_data: The video generation result to assess.

        Returns:
            Quality assessment with scores and recommendations.
        """
        # Calculate quality metrics
        metrics = self._calculate_metrics(input_data)

        # Generate improvement recommendations
        recommendations = self._generate_recommendations(metrics)

        # Predict engagement
        engagement_prediction = self._predict_engagement(metrics)

        return {
            "video_id": str(input_data.id),
            "quality_metrics": metrics.model_dump(),
            "engagement_prediction": engagement_prediction,
            "recommendations": recommendations,
            "overall_score": metrics.overall_score,
        }

    def _calculate_metrics(self, result: VideoGenerationResult) -> VideoQualityMetrics:
        """Calculate video quality metrics.

        Args:
            result: The video generation result.

        Returns:
            Quality metrics.
        """
        # Visual quality based on provider and format
        visual_quality = 0.7
        if result.provider.value == "hyperframes":
            visual_quality = 0.85
        elif result.provider.value == "remotion":
            visual_quality = 0.8

        # Audio quality (placeholder — would analyze actual audio)
        audio_quality = 0.75

        # Pacing score based on duration
        pacing_score = 0.7
        if 10 <= result.duration_seconds <= 30:
            pacing_score = 0.9  # Optimal for social media
        elif result.duration_seconds <= 60:
            pacing_score = 0.8

        # Brand consistency (placeholder)
        brand_consistency = 0.7

        # Overall score
        overall = (visual_quality + audio_quality + pacing_score + brand_consistency) / 4

        # Identify issues
        issues = []
        if visual_quality < 0.8:
            issues.append("Visual quality could be improved")
        if audio_quality < 0.8:
            issues.append("Audio quality needs attention")
        if pacing_score < 0.8:
            issues.append("Pacing may not be optimal for target platform")

        return VideoQualityMetrics(
            video_id=result.id,
            visual_quality=round(visual_quality, 2),
            audio_quality=round(audio_quality, 2),
            pacing_score=round(pacing_score, 2),
            engagement_prediction=round(overall * 0.9, 2),
            brand_consistency=round(brand_consistency, 2),
            overall_score=round(overall, 2),
            issues=issues,
        )

    def _generate_recommendations(self, metrics: VideoQualityMetrics) -> list[str]:
        """Generate improvement recommendations.

        Args:
            metrics: The quality metrics.

        Returns:
            List of recommendations.
        """
        recs = []
        if metrics.visual_quality < 0.8:
            recs.append("Consider using HyperFrames for higher visual quality")
        if metrics.pacing_score < 0.8:
            recs.append("Optimize video length for target platform (15-30s for social)")
        if metrics.engagement_prediction < 0.7:
            recs.append("Add stronger hook in first 3 seconds")
        if not recs:
            recs.append("Video quality is good — ready for publishing")
        return recs

    def _predict_engagement(self, metrics: VideoQualityMetrics) -> float:
        """Predict engagement rate.

        Args:
            metrics: The quality metrics.

        Returns:
            Predicted engagement rate (0-1).
        """
        # Weighted prediction based on quality metrics
        prediction = (
            metrics.visual_quality * 0.3
            + metrics.audio_quality * 0.2
            + metrics.pacing_score * 0.3
            + metrics.brand_consistency * 0.2
        )
        return round(prediction, 2)
