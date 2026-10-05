"""Video Scriptwriter Agent — generates video scripts from prompts."""

from __future__ import annotations

from typing import Any

from ugc_marketplace.video.agents.base import BaseVideoAgent
from ugc_marketplace.video.models import VideoGenerationRequest


class VideoScriptwriterAgent(BaseVideoAgent[VideoGenerationRequest]):
    """Agent that generates video scripts from text prompts.

    Takes a natural language prompt and produces a structured video script
    with scenes, narration, and visual directions.
    """

    async def _execute(self, input_data: VideoGenerationRequest) -> dict[str, Any]:
        """Execute video script generation.

        Args:
            input_data: The video generation request.

        Returns:
            Script result with scenes and narration.
        """
        # Generate script structure
        script = self._generate_script(input_data)

        # Generate scene breakdown
        scenes = self._generate_scenes(script, input_data.duration_seconds)

        # Generate visual directions
        visuals = self._generate_visual_directions(scenes)

        return {
            "prompt": input_data.prompt,
            "script": script,
            "scenes": scenes,
            "visual_directions": visuals,
            "estimated_duration": input_data.duration_seconds,
            "aspect_ratio": input_data.aspect_ratio.value,
        }

    def _generate_script(self, request: VideoGenerationRequest) -> str:
        """Generate video script from prompt.

        Args:
            request: The video generation request.

        Returns:
            Generated script text.
        """
        # Use LLM to generate script if available, otherwise use template
        try:
            response = self.model.invoke(
                f"Write a {request.duration_seconds}-second video script based on: {request.prompt}. "
                f"Format: Hook (0-3s), Problem (3-10s), Solution (10-20s), CTA (20-{request.duration_seconds}s). "
                f"Keep it concise and engaging."
            )
            return response.content if hasattr(response, "content") else str(response)
        except Exception:
            pass

        # Fallback template
        return (
            f"Hook: Discover the power of {request.prompt[:50]}\n"
            f"Problem: Traditional solutions fall short\n"
            f"Solution: Our approach delivers results\n"
            f"CTA: Try it today and see the difference"
        )

    def _generate_scenes(self, script: str, duration: float) -> list[dict[str, Any]]:
        """Generate scene breakdown from script.

        Args:
            script: The generated script.
            duration: Total video duration in seconds.

        Returns:
            List of scene dictionaries.
        """
        scene_count = max(3, int(duration / 5))
        scene_duration = duration / scene_count

        scenes = []
        for i in range(scene_count):
            start = i * scene_duration
            end = (i + 1) * scene_duration
            scenes.append(
                {
                    "scene_number": i + 1,
                    "start_time": round(start, 1),
                    "end_time": round(end, 1),
                    "duration": round(scene_duration, 1),
                    "narration": f"Scene {i + 1}: {script[:100] if script else 'Visual content'}",
                    "visual_type": "motion_graphics" if i % 2 == 0 else "text_overlay",
                }
            )

        return scenes

    def _generate_visual_directions(self, scenes: list[dict[str, Any]]) -> list[str]:
        """Generate visual directions for each scene.

        Args:
            scenes: The scene breakdown.

        Returns:
            List of visual direction strings.
        """
        directions = []
        for scene in scenes:
            directions.append(
                f"Scene {scene['scene_number']}: {scene['visual_type']} "
                f"with smooth transitions, brand colors, and engaging motion"
            )
        return directions
