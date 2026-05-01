from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .base import TimestampedData, VersionedModel
from .refs import MaskRef, PointCloudRef


class SE3(BaseModel):
    """6-DOF pose: position (x, y, z) + quaternion (x, y, z, w)."""

    position: list[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0], min_length=3, max_length=3
    )
    quaternion: list[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0, 1.0], min_length=4, max_length=4
    )


class BoundingBox3D(BaseModel):
    """Axis-aligned 3D bounding box."""

    center: SE3 = Field(default_factory=SE3)
    size: list[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0], min_length=3, max_length=3
    )


class ObjectObservation(TimestampedData):
    """Raw sensor observation of an object."""

    bbox_2d: list[int] = Field(default_factory=list)
    mask_ref: MaskRef | None = None
    pose_in_camera: SE3 | None = None
    point_cloud_ref: PointCloudRef | None = None
    detection_confidence: float = 0.0
    segmentation_confidence: float = 0.0


class ObjectBelief(TimestampedData):
    """Fused belief about an object's state."""

    pose_in_base: SE3 | None = None
    bbox_3d: BoundingBox3D | None = None
    pose_covariance: list[float] = Field(default_factory=list)
    velocity: list[float] = Field(default_factory=list)
    is_static: bool = True
    grasp_candidates: list[str] = Field(default_factory=list)
    reachable: bool | None = None


class ObjectLifecycle(str, Enum):
    """Lifecycle state of a tracked object."""

    ACTIVE = "active"
    OCCLUDED = "occluded"
    LOST = "lost"
    REMOVED = "removed"
    HELD = "held"


class ObjectState(VersionedModel):
    """Complete state of a tracked object."""

    object_id: str
    category: str
    description: str = ""
    observed: ObjectObservation | None = None
    belief: ObjectBelief | None = None
    lifecycle_state: ObjectLifecycle = ObjectLifecycle.ACTIVE
    last_seen: float = 0.0
    confidence: float = 0.0
    ttl_sec: float = 5.0
    properties: dict[str, Any] = Field(default_factory=dict)


class ArmState(VersionedModel):
    """State of a robotic arm."""

    arm_id: str
    joint_positions: list[float] = Field(default_factory=list)
    joint_velocities: list[float] = Field(default_factory=list)
    joint_efforts: list[float] = Field(default_factory=list)
    eef_pose: SE3 = Field(default_factory=SE3)
    manipulability: float = 0.0


class GripperState(VersionedModel):
    """State of a gripper."""

    gripper_id: str
    type: str = "parallel"
    width: float = 0.0
    force: float = 0.0
    is_grasping: bool = False
    grasped_object_id: str = ""


class SafeZone(BaseModel):
    """A safe operational zone."""

    zone_id: str
    type: str
    center: SE3 = Field(default_factory=SE3)
    params: dict[str, float] = Field(default_factory=dict)


class ForbiddenZone(BaseModel):
    """A forbidden zone the robot must avoid."""

    zone_id: str
    type: str
    center: SE3 = Field(default_factory=SE3)
    params: dict[str, float] = Field(default_factory=dict)
    reason: str = ""


class EnvironmentState(VersionedModel):
    """State of the environment surrounding the robot."""

    table_planes: list[dict[str, Any]] = Field(default_factory=list)
    obstacles: list[ObjectState] = Field(default_factory=list)
    safe_zones: list[SafeZone] = Field(default_factory=list)
    forbidden_zones: list[ForbiddenZone] = Field(default_factory=list)


class FailureRecord(BaseModel):
    """Record of a task execution failure."""

    node_id: str
    failure_code: str
    timestamp: float
    recovery_action: str = ""
    recovery_result: str = ""


class TaskState(VersionedModel):
    """State of a task being executed."""

    task_id: str
    plan_id: str
    current_node_id: str = ""
    status: str = "pending"
    progress: float = 0.0
    failure_history: list[FailureRecord] = Field(default_factory=list)


class RobotState(VersionedModel):
    """Complete state of the robot."""

    robot_id: str
    arms: list[ArmState] = Field(default_factory=list)
    grippers: list[GripperState] = Field(default_factory=list)
    base_pose: SE3 | None = None
    is_moving: bool = False
    current_control_mode: str = "position"


class WorldState(VersionedModel):
    """Complete world state snapshot."""

    timestamp: float
    robot: RobotState
    objects: list[ObjectState] = Field(default_factory=list)
    environment: EnvironmentState = Field(default_factory=EnvironmentState)
    task: TaskState | None = None
