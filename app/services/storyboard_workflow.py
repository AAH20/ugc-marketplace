"""Storyboard workflow with approval gates for AI video generation."""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from app.services.videoclaw_cli import VideoClawCLIClient

logger = logging.getLogger(__name__)


class StoryboardStatus(Enum):
    """Status of a storyboard in the workflow."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PRODUCING = "producing"
    COMPLETE = "complete"
    FAILED = "failed"


class ApprovalDecision(Enum):
    """Decision from an approval gate."""
    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"


@dataclass
class Scene:
    """A single scene in a storyboard."""
    scene_number: int
    description: str
    visual_prompt: str
    duration_seconds: float = 5.0
    transition: str = "cut"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Storyboard:
    """A complete storyboard for a video project."""
    project_id: str
    title: str
    scenes: List[Scene]
    status: StoryboardStatus = StoryboardStatus.DRAFT
    provider: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_duration(self) -> float:
        """Total duration of all scenes in seconds."""
        return sum(s.duration_seconds for s in self.scenes)

    @property
    def scene_count(self) -> int:
        """Number of scenes."""
        return len(self.scenes)


@dataclass
class ApprovalGate:
    """An approval gate in the workflow."""
    gate_id: str
    name: str
    description: str
    approver: Optional[str] = None
    decision: Optional[ApprovalDecision] = None
    feedback: str = ""
    timestamp: Optional[str] = None


class StoryboardWorkflow:
    """Workflow for creating AI-generated videos with storyboard approval gates.

    Workflow stages:
        1. Generate storyboard from prompt
        2. Approval gate: review storyboard
        3. Produce video segments (per scene)
        4. Approval gate: review produced segments
        5. Assemble final video
    """

    def __init__(
        self,
        cli_client: VideoClawCLIClient,
        provider_router: Optional[Any] = None,
    ):
        self.cli = cli_client
        self.provider_router = provider_router
        self._storyboards: Dict[str, Storyboard] = {}
        self._approval_gates: Dict[str, List[ApprovalGate]] = {}
        self._approval_callbacks: Dict[str, Callable] = {}

    def create_storyboard(
        self,
        title: str,
        prompt: str,
        scene_count: int = 5,
        provider: Optional[str] = None,
    ) -> Storyboard:
        """Create a new storyboard from a text prompt.

        Args:
            title: Project title.
            prompt: Text prompt describing the desired video.
            scene_count: Number of scenes to generate.
            provider: Preferred video provider.

        Returns:
            The created storyboard in DRAFT status.
        """
        # Create project via CLI
        result = self.cli.video_create(title, provider=provider or "auto")
        project_id = result["project_id"]

        # Generate scenes from prompt
        scenes = self._generate_scenes(prompt, scene_count)

        storyboard = Storyboard(
            project_id=project_id,
            title=title,
            scenes=scenes,
            status=StoryboardStatus.DRAFT,
            provider=provider,
        )
        self._storyboards[project_id] = storyboard
        self._approval_gates[project_id] = []

        logger.info("Created storyboard %s with %d scenes", project_id, scene_count)
        return storyboard

    def submit_for_approval(self, project_id: str, approver: str) -> ApprovalGate:
        """Submit a storyboard for approval.

        Args:
            project_id: The storyboard project ID.
            approver: Who is submitting for approval.

        Returns:
            The created approval gate.

        Raises:
            ValueError: If storyboard not found.
        """
        if project_id not in self._storyboards:
            raise ValueError(f"Storyboard {project_id} not found")

        storyboard = self._storyboards[project_id]
        storyboard.status = StoryboardStatus.PENDING_APPROVAL

        gate = ApprovalGate(
            gate_id=f"gate_{project_id}_storyboard",
            name="Storyboard Review",
            description="Review the generated storyboard scenes before production.",
            approver=approver,
        )
        self._approval_gates[project_id].append(gate)

        # Trigger callback if registered
        if project_id in self._approval_callbacks:
            self._approval_callbacks[project_id](gate)

        return gate

    def approve_storyboard(
        self,
        project_id: str,
        decision: ApprovalDecision,
        feedback: str = "",
    ) -> Storyboard:
        """Record an approval decision for a storyboard.

        Args:
            project_id: The storyboard project ID.
            decision: APPROVE, REJECT, or REVISE.
            feedback: Optional feedback text.

        Returns:
            Updated storyboard.

        Raises:
            ValueError: If storyboard not found.
        """
        if project_id not in self._storyboards:
            raise ValueError(f"Storyboard {project_id} not found")

        storyboard = self._storyboards[project_id]
        gates = self._approval_gates.get(project_id, [])

        if not gates:
            raise ValueError(f"No approval gate found for {project_id}")

        gate = gates[-1]
        gate.decision = decision
        gate.feedback = feedback

        if decision == ApprovalDecision.APPROVE:
            storyboard.status = StoryboardStatus.APPROVED
        elif decision == ApprovalDecision.REJECT:
            storyboard.status = StoryboardStatus.REJECTED
        elif decision == ApprovalDecision.REVISE:
            storyboard.status = StoryboardStatus.DRAFT

        return storyboard

    def produce_video(
        self,
        project_id: str,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Produce video segments for an approved storyboard.

        Args:
            project_id: The storyboard project ID.
            provider: Override provider (uses storyboard provider if None).

        Returns:
            Production result from CLI.

        Raises:
            ValueError: If storyboard not found or not approved.
        """
        if project_id not in self._storyboards:
            raise ValueError(f"Storyboard {project_id} not found")

        storyboard = self._storyboards[project_id]
        if storyboard.status != StoryboardStatus.APPROVED:
            raise ValueError(
                f"Storyboard must be approved before production, current: {storyboard.status}"
            )

        storyboard.status = StoryboardStatus.PRODUCING

        # Route to provider with fallback
        chosen_provider = provider or storyboard.provider or "auto"
        if self.provider_router:
            chosen_provider = self.provider_router.select_provider(
                task="video_produce",
                preferred=chosen_provider,
            )

        result = self.cli.video_produce(
            project_id,
            provider=chosen_provider,
        )

        storyboard.provider = chosen_provider
        return result

    def assemble_video(self, project_id: str) -> Dict[str, Any]:
        """Assemble the final video from produced segments.

        Args:
            project_id: The storyboard project ID.

        Returns:
            Assembly result with video URL.

        Raises:
            ValueError: If storyboard not found.
        """
        if project_id not in self._storyboards:
            raise ValueError(f"Storyboard {project_id} not found")

        storyboard = self._storyboards[project_id]
        result = self.cli.video_assemble(project_id)
        storyboard.status = StoryboardStatus.COMPLETE
        return result

    def register_approval_callback(
        self,
        project_id: str,
        callback: Callable[[ApprovalGate], None],
    ):
        """Register a callback for approval gate events."""
        self._approval_callbacks[project_id] = callback

    def get_storyboard(self, project_id: str) -> Optional[Storyboard]:
        """Get a storyboard by project ID."""
        return self._storyboards.get(project_id)

    def get_approval_history(self, project_id: str) -> List[ApprovalGate]:
        """Get approval gate history for a project."""
        return self._approval_gates.get(project_id, [])

    def _generate_scenes(self, prompt: str, count: int) -> List[Scene]:
        """Generate scenes from a text prompt.

        In production, this would call an LLM. For now, creates
        structured scenes from the prompt.
        """
        scenes = []
        for i in range(count):
            scenes.append(
                Scene(
                    scene_number=i + 1,
                    description=f"Scene {i + 1}: {prompt[:100]}",
                    visual_prompt=f"AI-generated visual for: {prompt[:200]}",
                    duration_seconds=5.0,
                    transition="cut" if i < count - 1 else "fade_out",
                )
            )
        return scenes
