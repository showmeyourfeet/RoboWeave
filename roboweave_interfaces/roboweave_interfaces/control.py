from __future__ import annotations

from pydantic import Field

from .base import VersionedModel


class ControlCommand(VersionedModel):
    """A control command for a robotic arm."""

    arm_id: str
    control_mode: str = "position"
    joint_positions: list[float] = Field(default_factory=list)
    joint_velocities: list[float] = Field(default_factory=list)
    joint_efforts: list[float] = Field(default_factory=list)
    stiffness: list[float] = Field(default_factory=list)
    damping: list[float] = Field(default_factory=list)


class ControlStatus(VersionedModel):
    """Status feedback from the control loop."""

    arm_id: str
    tracking_error: float = 0.0
    external_force: list[float] = Field(default_factory=list)
    external_torque: float = 0.0
    is_contact: bool = False
