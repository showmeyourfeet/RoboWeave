"""roboweave_interfaces - Pure Python data structures for the RoboWeave robotics system."""

from ._version import SCHEMA_VERSION

# base
from .base import JsonEnvelope, TimestampedData, VersionedModel

# refs
from .refs import DataRef, DepthRef, ImageRef, MaskRef, PointCloudRef, TrajectoryRef, WorldStateRef

# task
from .task import (
    FailurePolicy, PlanGraph, PlanNode, RetryPolicy, SceneContext,
    SuccessCondition, TaskPriority, TaskRequest, TaskStatus,
)

# world_state
from .world_state import (
    ArmState, BoundingBox3D, EnvironmentState, FailureRecord, ForbiddenZone,
    GripperState, ObjectBelief, ObjectLifecycle, ObjectObservation, ObjectState,
    RobotState, SafeZone, SE3, TaskState, WorldState,
)

# skill
from .skill import (
    PostconditionResult, PreconditionResult, SkillCall, SkillCategory,
    SkillDescriptor, SkillLogs, SkillResult, SkillStatus,
)

# perception
from .perception import DetectionResult, PoseEstimationResult, PointCloudResult, SegmentationResult

# grasp
from .grasp import GraspCandidate, GraspConstraints

# motion
from .motion import MotionRequest, TrajectoryPoint, TrajectoryResult

# control
from .control import ControlCommand, ControlStatus

# vla
from .vla import VLAAction, VLAActionSpace, VLAActionType, VLASafetyConstraints

# event
from .event import EventType, ExecutionEvent, RecoveryAction

# errors
from .errors import ERROR_CODE_SPECS, ErrorCode, ErrorCodeSpec, FailureInfo, Severity

# episode
from .episode import EpisodeLabels, EpisodeLog, EpisodeStatus, FrameLog, SkillLog, SystemVersions

# safety
from .safety import SafetyConfig, SafetyEvent, SafetyLevel, WorkspaceLimits

# hardware
from .hardware import ArmConfig, CameraConfig, GripperConfig, HardwareConfig, MobileBaseConfig

# hitl
from .hitl import HITLRequest, HITLRequestType, HITLResponse

__all__ = [
    # base
    "SCHEMA_VERSION", "VersionedModel", "TimestampedData", "JsonEnvelope",
    # refs
    "DataRef", "ImageRef", "DepthRef", "PointCloudRef", "MaskRef", "TrajectoryRef", "WorldStateRef",
    # task
    "TaskPriority", "TaskStatus", "RetryPolicy", "SuccessCondition", "FailurePolicy",
    "SceneContext", "PlanNode", "PlanGraph", "TaskRequest",
    # world_state
    "SE3", "BoundingBox3D", "ObjectObservation", "ObjectBelief", "ObjectLifecycle",
    "ObjectState", "ArmState", "GripperState", "SafeZone", "ForbiddenZone",
    "EnvironmentState", "FailureRecord", "TaskState", "RobotState", "WorldState",
    # skill
    "SkillCategory", "SkillStatus", "SkillLogs", "PreconditionResult", "PostconditionResult",
    "SkillDescriptor", "SkillCall", "SkillResult",
    # perception
    "DetectionResult", "SegmentationResult", "PointCloudResult", "PoseEstimationResult",
    # grasp
    "GraspCandidate", "GraspConstraints",
    # motion
    "TrajectoryPoint", "MotionRequest", "TrajectoryResult",
    # control
    "ControlCommand", "ControlStatus",
    # vla
    "VLAActionType", "VLAActionSpace", "VLAAction", "VLASafetyConstraints",
    # event
    "EventType", "ExecutionEvent", "RecoveryAction",
    # errors
    "Severity", "ErrorCode", "ErrorCodeSpec", "FailureInfo", "ERROR_CODE_SPECS",
    # episode
    "EpisodeStatus", "EpisodeLabels", "SystemVersions", "SkillLog", "FrameLog", "EpisodeLog",
    # safety
    "SafetyLevel", "WorkspaceLimits", "SafetyConfig", "SafetyEvent",
    # hardware
    "ArmConfig", "GripperConfig", "CameraConfig", "MobileBaseConfig", "HardwareConfig",
    # hitl
    "HITLRequestType", "HITLRequest", "HITLResponse",
]
