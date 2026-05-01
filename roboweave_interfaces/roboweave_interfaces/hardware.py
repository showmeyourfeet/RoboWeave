from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import VersionedModel


class ArmConfig(VersionedModel):
    """Configuration for a robotic arm."""

    arm_id: str
    name: str
    num_joints: int
    joint_names: list[str] = Field(default_factory=list)
    joint_limits_lower: list[float] = Field(default_factory=list)
    joint_limits_upper: list[float] = Field(default_factory=list)
    max_joint_velocities: list[float] = Field(default_factory=list)
    max_joint_efforts: list[float] = Field(default_factory=list)
    eef_link: str = ""
    base_link: str = ""
    driver_type: str = "sim"
    driver_config: dict[str, Any] = Field(default_factory=dict)


class GripperConfig(VersionedModel):
    """Configuration for a gripper."""

    gripper_id: str
    name: str
    type: str = "parallel"
    attached_to_arm: str = ""
    min_width: float = 0.0
    max_width: float = 0.1
    max_force: float = 20.0
    driver_type: str = "sim"
    driver_config: dict[str, Any] = Field(default_factory=dict)


class CameraConfig(VersionedModel):
    """Configuration for a camera."""

    camera_id: str
    name: str
    type: str = "rgbd"
    frame_id: str = ""
    image_topic: str = ""
    depth_topic: str = ""
    camera_info_topic: str = ""
    resolution: list[int] = Field(default_factory=list)


class MobileBaseConfig(VersionedModel):
    """Configuration for a mobile base."""

    base_type: str = "differential"
    max_linear_velocity: float = 1.0
    max_angular_velocity: float = 1.0
    cmd_vel_topic: str = "/cmd_vel"
    odom_topic: str = "/odom"


class HardwareConfig(VersionedModel):
    """Complete hardware configuration for a robot."""

    robot_id: str
    robot_name: str
    arms: list[ArmConfig] = Field(default_factory=list)
    grippers: list[GripperConfig] = Field(default_factory=list)
    cameras: list[CameraConfig] = Field(default_factory=list)
    has_mobile_base: bool = False
    mobile_base_config: MobileBaseConfig | None = None
    urdf_path: str = ""
    srdf_path: str = ""
