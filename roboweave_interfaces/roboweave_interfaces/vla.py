from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field

from .base import TimestampedData, VersionedModel
from .world_state import SE3


class VLAActionType(str, Enum):
    """Type of VLA action output."""

    DELTA_EEF_POSE = "delta_eef_pose"
    TARGET_EEF_POSE = "target_eef_pose"
    JOINT_DELTA = "joint_delta"
    GRIPPER_COMMAND = "gripper_command"
    SKILL_SUBGOAL = "skill_subgoal"


class VLAActionSpace(VersionedModel):
    """Defines the action space constraints for a VLA model."""

    supported_action_types: list[VLAActionType] = Field(default_factory=list)
    max_delta_position: float = 0.05
    max_delta_rotation: float = 0.1
    max_joint_delta: float = 0.1
    control_frequency_hz: float = 10.0


class VLAAction(TimestampedData):
    """A single action output from a VLA model."""

    action_type: VLAActionType
    frame_id: str = "base_link"
    delta_pose: SE3 | None = None
    target_pose: SE3 | None = None
    joint_delta: list[float] = Field(default_factory=list)
    gripper_command: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    horizon_steps: int = 1
    requires_safety_filter: bool = True


class VLASafetyConstraints(VersionedModel):
    """Safety constraints applied to VLA action outputs."""

    max_velocity: float = 0.25
    max_angular_velocity: float = 0.5
    force_limit: float = 20.0
    torque_limit: float = 10.0
    workspace_limit_id: str = ""
    max_duration_sec: float = 60.0
    allow_contact: bool = False
    min_confidence_threshold: float = 0.3
