from __future__ import annotations

from pydantic import BaseModel, Field

from .base import VersionedModel
from .world_state import SE3


class TrajectoryPoint(BaseModel):
    """A single point in a trajectory."""

    positions: list[float] = Field(default_factory=list)
    velocities: list[float] = Field(default_factory=list)
    accelerations: list[float] = Field(default_factory=list)
    time_from_start_sec: float = 0.0


class MotionRequest(VersionedModel):
    """Request for motion planning."""

    arm_id: str
    goal_pose: SE3 | None = None
    goal_joint_state: list[float] | None = None
    planning_mode: str = "joint_space"
    max_velocity_scaling: float = 0.5
    max_acceleration_scaling: float = 0.5
    ignore_collision_objects: list[str] = Field(default_factory=list)
    waypoints: list[SE3] = Field(default_factory=list)
    max_planning_time_ms: int = 5000


class TrajectoryResult(VersionedModel):
    """Result of motion planning."""

    trajectory: list[TrajectoryPoint] = Field(default_factory=list)
    duration_sec: float = 0.0
    collision_free: bool = True
    failure_code: str = ""
    message: str = ""
