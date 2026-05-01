from __future__ import annotations

from enum import Enum

from pydantic import Field

from .base import VersionedModel


class SafetyLevel(str, Enum):
    """Safety level classification."""

    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY_STOP = "emergency_stop"


class WorkspaceLimits(VersionedModel):
    """Axis-aligned workspace boundary limits."""

    x_min: float = -1.0
    x_max: float = 1.0
    y_min: float = -1.0
    y_max: float = 1.0
    z_min: float = 0.0
    z_max: float = 1.5


class SafetyConfig(VersionedModel):
    """Configuration for the safety supervisor."""

    max_joint_velocity: list[float] = Field(default_factory=list)
    max_eef_velocity: float = 1.0
    max_eef_angular_velocity: float = 2.0
    force_limit: float = 50.0
    torque_limit: float = 20.0
    min_human_distance: float = 0.3
    workspace_limits: WorkspaceLimits | None = None
    enable_self_collision_check: bool = True
    enable_environment_collision_check: bool = True
    cloud_disconnect_timeout_sec: float = 30.0


class SafetyEvent(VersionedModel):
    """A safety event raised by the safety supervisor."""

    event_id: str
    safety_level: SafetyLevel
    violation_type: str
    message: str
    timestamp: float
    auto_recovery: bool = False
