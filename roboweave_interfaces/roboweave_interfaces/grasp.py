from __future__ import annotations

from pydantic import Field

from .base import VersionedModel
from .world_state import SE3


class GraspConstraints(VersionedModel):
    """Constraints for grasp planning."""

    preferred_regions: list[str] = Field(default_factory=list)
    avoid_regions: list[str] = Field(default_factory=list)
    max_force: float = 20.0
    min_gripper_width: float = 0.0
    max_gripper_width: float = 0.1
    approach_direction_hint: list[float] = Field(default_factory=list)


class GraspCandidate(VersionedModel):
    """A candidate grasp pose with quality metrics."""

    grasp_id: str
    grasp_pose: SE3 = Field(default_factory=SE3)
    approach_direction: list[float] = Field(default_factory=lambda: [0.0, 0.0, -1.0])
    gripper_width: float = 0.0
    grasp_score: float = 0.0
    collision_score: float = 0.0
    reachable: bool | None = None
    matched_regions: list[str] = Field(default_factory=list)
    ik_solution: list[float] = Field(default_factory=list)
