from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .base import VersionedModel


class Severity(str, Enum):
    """Severity level for errors and events."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCode(str, Enum):
    """Comprehensive error codes for all RoboWeave subsystems."""

    OK = "OK"
    UNKNOWN = "UNKNOWN"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    INVALID_INPUT = "INVALID_INPUT"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # Perception
    PER_DETECTION_FAILED = "PER_DETECTION_FAILED"
    PER_NO_OBJECT_FOUND = "PER_NO_OBJECT_FOUND"
    PER_AMBIGUOUS_TARGET = "PER_AMBIGUOUS_TARGET"
    PER_SEGMENTATION_FAILED = "PER_SEGMENTATION_FAILED"
    PER_MASK_TOO_SMALL = "PER_MASK_TOO_SMALL"
    PER_POINT_CLOUD_EMPTY = "PER_POINT_CLOUD_EMPTY"
    PER_POSE_ESTIMATION_FAILED = "PER_POSE_ESTIMATION_FAILED"
    PER_TRACKING_LOST = "PER_TRACKING_LOST"
    PER_MODEL_LOAD_FAILED = "PER_MODEL_LOAD_FAILED"

    # Grasp
    GRP_NO_GRASP_FOUND = "GRP_NO_GRASP_FOUND"
    GRP_ALL_GRASPS_COLLIDE = "GRP_ALL_GRASPS_COLLIDE"
    GRP_ALL_GRASPS_UNREACHABLE = "GRP_ALL_GRASPS_UNREACHABLE"
    GRP_CONSTRAINT_UNSATISFIABLE = "GRP_CONSTRAINT_UNSATISFIABLE"

    # Inverse Kinematics
    IK_NO_SOLUTION = "IK_NO_SOLUTION"
    IK_JOINT_LIMIT = "IK_JOINT_LIMIT"
    IK_SINGULARITY = "IK_SINGULARITY"
    IK_COLLISION = "IK_COLLISION"

    # Motion Planning
    MOT_PLANNING_FAILED = "MOT_PLANNING_FAILED"
    MOT_PLANNING_TIMEOUT = "MOT_PLANNING_TIMEOUT"
    MOT_COLLISION_DETECTED = "MOT_COLLISION_DETECTED"
    MOT_INVALID_START_STATE = "MOT_INVALID_START_STATE"
    MOT_INVALID_GOAL = "MOT_INVALID_GOAL"

    # Control
    CTL_TRACKING_ERROR = "CTL_TRACKING_ERROR"
    CTL_FORCE_EXCEEDED = "CTL_FORCE_EXCEEDED"
    CTL_GRIPPER_FAILED = "CTL_GRIPPER_FAILED"
    CTL_GRASP_SLIP = "CTL_GRASP_SLIP"
    CTL_DRIVER_ERROR = "CTL_DRIVER_ERROR"

    # VLA
    VLA_PREDICTION_FAILED = "VLA_PREDICTION_FAILED"
    VLA_ACTION_DRIFT = "VLA_ACTION_DRIFT"
    VLA_CONFIDENCE_LOW = "VLA_CONFIDENCE_LOW"
    VLA_SAFETY_VIOLATION = "VLA_SAFETY_VIOLATION"
    VLA_TASK_INCOMPLETE = "VLA_TASK_INCOMPLETE"
    VLA_MODEL_LOAD_FAILED = "VLA_MODEL_LOAD_FAILED"

    # Safety
    SAF_EMERGENCY_STOP = "SAF_EMERGENCY_STOP"
    SAF_COLLISION_RISK = "SAF_COLLISION_RISK"
    SAF_FORCE_LIMIT = "SAF_FORCE_LIMIT"
    SAF_SPEED_LIMIT = "SAF_SPEED_LIMIT"
    SAF_WORKSPACE_VIOLATION = "SAF_WORKSPACE_VIOLATION"
    SAF_HUMAN_PROXIMITY = "SAF_HUMAN_PROXIMITY"

    # Communication
    COM_CLOUD_DISCONNECTED = "COM_CLOUD_DISCONNECTED"
    COM_SERVICE_TIMEOUT = "COM_SERVICE_TIMEOUT"
    COM_INVALID_RESPONSE = "COM_INVALID_RESPONSE"

    # Task
    TSK_INSTRUCTION_UNCLEAR = "TSK_INSTRUCTION_UNCLEAR"
    TSK_PLAN_INVALID = "TSK_PLAN_INVALID"
    TSK_SKILL_NOT_FOUND = "TSK_SKILL_NOT_FOUND"
    TSK_PRECONDITION_FAILED = "TSK_PRECONDITION_FAILED"
    TSK_POSTCONDITION_FAILED = "TSK_POSTCONDITION_FAILED"
    TSK_MAX_RETRY_EXCEEDED = "TSK_MAX_RETRY_EXCEEDED"


class ErrorCodeSpec(BaseModel):
    """Metadata specification for an error code."""

    code: ErrorCode
    module: str
    severity: Severity
    recoverable: bool
    retryable: bool
    default_recovery_policy: str = ""
    escalate_to_cloud: bool = False
    escalate_to_user: bool = False
    safety_related: bool = False


class FailureInfo(VersionedModel):
    """Information about a failure occurrence."""

    code: ErrorCode
    message: str = ""
    recoverable: bool = True
    suggested_recovery: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


ERROR_CODE_SPECS: dict[ErrorCode, ErrorCodeSpec] = {
    # General
    ErrorCode.OK: ErrorCodeSpec(
        code=ErrorCode.OK, module="system", severity=Severity.INFO,
        recoverable=True, retryable=False,
    ),
    ErrorCode.UNKNOWN: ErrorCodeSpec(
        code=ErrorCode.UNKNOWN, module="system", severity=Severity.ERROR,
        recoverable=False, retryable=False, escalate_to_cloud=True,
    ),
    ErrorCode.TIMEOUT: ErrorCodeSpec(
        code=ErrorCode.TIMEOUT, module="system", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="retry_with_backoff",
    ),
    ErrorCode.CANCELLED: ErrorCodeSpec(
        code=ErrorCode.CANCELLED, module="system", severity=Severity.INFO,
        recoverable=True, retryable=False,
    ),
    ErrorCode.INVALID_INPUT: ErrorCodeSpec(
        code=ErrorCode.INVALID_INPUT, module="system", severity=Severity.ERROR,
        recoverable=False, retryable=False, escalate_to_user=True,
    ),
    ErrorCode.SERVICE_UNAVAILABLE: ErrorCodeSpec(
        code=ErrorCode.SERVICE_UNAVAILABLE, module="system", severity=Severity.ERROR,
        recoverable=True, retryable=True, default_recovery_policy="retry_with_backoff",
        escalate_to_cloud=True,
    ),
    # Perception
    ErrorCode.PER_DETECTION_FAILED: ErrorCodeSpec(
        code=ErrorCode.PER_DETECTION_FAILED, module="perception", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="reobserve_from_new_view",
    ),
    ErrorCode.PER_NO_OBJECT_FOUND: ErrorCodeSpec(
        code=ErrorCode.PER_NO_OBJECT_FOUND, module="perception", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="reobserve_from_new_view",
    ),
    ErrorCode.PER_AMBIGUOUS_TARGET: ErrorCodeSpec(
        code=ErrorCode.PER_AMBIGUOUS_TARGET, module="perception", severity=Severity.WARNING,
        recoverable=True, retryable=False, default_recovery_policy="disambiguate_with_user",
        escalate_to_user=True,
    ),
    ErrorCode.PER_SEGMENTATION_FAILED: ErrorCodeSpec(
        code=ErrorCode.PER_SEGMENTATION_FAILED, module="perception", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="reobserve_from_new_view",
    ),
    ErrorCode.PER_MASK_TOO_SMALL: ErrorCodeSpec(
        code=ErrorCode.PER_MASK_TOO_SMALL, module="perception", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="move_closer",
    ),
    ErrorCode.PER_POINT_CLOUD_EMPTY: ErrorCodeSpec(
        code=ErrorCode.PER_POINT_CLOUD_EMPTY, module="perception", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="reobserve_from_new_view",
    ),
    ErrorCode.PER_POSE_ESTIMATION_FAILED: ErrorCodeSpec(
        code=ErrorCode.PER_POSE_ESTIMATION_FAILED, module="perception", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="reobserve_from_new_view",
    ),
    ErrorCode.PER_TRACKING_LOST: ErrorCodeSpec(
        code=ErrorCode.PER_TRACKING_LOST, module="perception", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="redetect_object",
    ),
    ErrorCode.PER_MODEL_LOAD_FAILED: ErrorCodeSpec(
        code=ErrorCode.PER_MODEL_LOAD_FAILED, module="perception", severity=Severity.ERROR,
        recoverable=False, retryable=False, escalate_to_cloud=True,
    ),
    # Grasp
    ErrorCode.GRP_NO_GRASP_FOUND: ErrorCodeSpec(
        code=ErrorCode.GRP_NO_GRASP_FOUND, module="grasp", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="reobserve_from_new_view",
    ),
    ErrorCode.GRP_ALL_GRASPS_COLLIDE: ErrorCodeSpec(
        code=ErrorCode.GRP_ALL_GRASPS_COLLIDE, module="grasp", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="clear_obstacles",
    ),
    ErrorCode.GRP_ALL_GRASPS_UNREACHABLE: ErrorCodeSpec(
        code=ErrorCode.GRP_ALL_GRASPS_UNREACHABLE, module="grasp", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="reposition_base",
    ),
    ErrorCode.GRP_CONSTRAINT_UNSATISFIABLE: ErrorCodeSpec(
        code=ErrorCode.GRP_CONSTRAINT_UNSATISFIABLE, module="grasp", severity=Severity.WARNING,
        recoverable=True, retryable=False, default_recovery_policy="relax_constraints",
        escalate_to_user=True,
    ),
    # IK
    ErrorCode.IK_NO_SOLUTION: ErrorCodeSpec(
        code=ErrorCode.IK_NO_SOLUTION, module="ik", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="try_alternative_pose",
    ),
    ErrorCode.IK_JOINT_LIMIT: ErrorCodeSpec(
        code=ErrorCode.IK_JOINT_LIMIT, module="ik", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="try_alternative_pose",
    ),
    ErrorCode.IK_SINGULARITY: ErrorCodeSpec(
        code=ErrorCode.IK_SINGULARITY, module="ik", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="perturb_goal",
    ),
    ErrorCode.IK_COLLISION: ErrorCodeSpec(
        code=ErrorCode.IK_COLLISION, module="ik", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="try_alternative_pose",
    ),
    # Motion
    ErrorCode.MOT_PLANNING_FAILED: ErrorCodeSpec(
        code=ErrorCode.MOT_PLANNING_FAILED, module="motion", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="replan_with_relaxed_constraints",
    ),
    ErrorCode.MOT_PLANNING_TIMEOUT: ErrorCodeSpec(
        code=ErrorCode.MOT_PLANNING_TIMEOUT, module="motion", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="retry_with_longer_timeout",
    ),
    ErrorCode.MOT_COLLISION_DETECTED: ErrorCodeSpec(
        code=ErrorCode.MOT_COLLISION_DETECTED, module="motion", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="replan_avoiding_collision",
        safety_related=True,
    ),
    ErrorCode.MOT_INVALID_START_STATE: ErrorCodeSpec(
        code=ErrorCode.MOT_INVALID_START_STATE, module="motion", severity=Severity.ERROR,
        recoverable=True, retryable=False, default_recovery_policy="update_robot_state",
    ),
    ErrorCode.MOT_INVALID_GOAL: ErrorCodeSpec(
        code=ErrorCode.MOT_INVALID_GOAL, module="motion", severity=Severity.ERROR,
        recoverable=True, retryable=False, default_recovery_policy="request_new_goal",
        escalate_to_user=True,
    ),
    # Control
    ErrorCode.CTL_TRACKING_ERROR: ErrorCodeSpec(
        code=ErrorCode.CTL_TRACKING_ERROR, module="control", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="reduce_speed",
    ),
    ErrorCode.CTL_FORCE_EXCEEDED: ErrorCodeSpec(
        code=ErrorCode.CTL_FORCE_EXCEEDED, module="control", severity=Severity.CRITICAL,
        recoverable=True, retryable=False, default_recovery_policy="stop_and_retract",
        safety_related=True,
    ),
    ErrorCode.CTL_GRIPPER_FAILED: ErrorCodeSpec(
        code=ErrorCode.CTL_GRIPPER_FAILED, module="control", severity=Severity.ERROR,
        recoverable=True, retryable=True, default_recovery_policy="retry_gripper",
    ),
    ErrorCode.CTL_GRASP_SLIP: ErrorCodeSpec(
        code=ErrorCode.CTL_GRASP_SLIP, module="control", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="regrasp",
    ),
    ErrorCode.CTL_DRIVER_ERROR: ErrorCodeSpec(
        code=ErrorCode.CTL_DRIVER_ERROR, module="control", severity=Severity.ERROR,
        recoverable=False, retryable=False, escalate_to_cloud=True,
    ),
    # VLA
    ErrorCode.VLA_PREDICTION_FAILED: ErrorCodeSpec(
        code=ErrorCode.VLA_PREDICTION_FAILED, module="vla", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="retry_prediction",
    ),
    ErrorCode.VLA_ACTION_DRIFT: ErrorCodeSpec(
        code=ErrorCode.VLA_ACTION_DRIFT, module="vla", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="reset_to_checkpoint",
    ),
    ErrorCode.VLA_CONFIDENCE_LOW: ErrorCodeSpec(
        code=ErrorCode.VLA_CONFIDENCE_LOW, module="vla", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="request_user_guidance",
        escalate_to_user=True,
    ),
    ErrorCode.VLA_SAFETY_VIOLATION: ErrorCodeSpec(
        code=ErrorCode.VLA_SAFETY_VIOLATION, module="vla", severity=Severity.CRITICAL,
        recoverable=True, retryable=False, default_recovery_policy="stop_and_replan",
        safety_related=True,
    ),
    ErrorCode.VLA_TASK_INCOMPLETE: ErrorCodeSpec(
        code=ErrorCode.VLA_TASK_INCOMPLETE, module="vla", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="continue_or_replan",
    ),
    ErrorCode.VLA_MODEL_LOAD_FAILED: ErrorCodeSpec(
        code=ErrorCode.VLA_MODEL_LOAD_FAILED, module="vla", severity=Severity.ERROR,
        recoverable=False, retryable=False, escalate_to_cloud=True,
    ),
    # Safety
    ErrorCode.SAF_EMERGENCY_STOP: ErrorCodeSpec(
        code=ErrorCode.SAF_EMERGENCY_STOP, module="safety", severity=Severity.CRITICAL,
        recoverable=False, retryable=False, safety_related=True,
        escalate_to_user=True,
    ),
    ErrorCode.SAF_COLLISION_RISK: ErrorCodeSpec(
        code=ErrorCode.SAF_COLLISION_RISK, module="safety", severity=Severity.CRITICAL,
        recoverable=True, retryable=False, default_recovery_policy="stop_and_replan",
        safety_related=True,
    ),
    ErrorCode.SAF_FORCE_LIMIT: ErrorCodeSpec(
        code=ErrorCode.SAF_FORCE_LIMIT, module="safety", severity=Severity.CRITICAL,
        recoverable=True, retryable=False, default_recovery_policy="stop_and_retract",
        safety_related=True,
    ),
    ErrorCode.SAF_SPEED_LIMIT: ErrorCodeSpec(
        code=ErrorCode.SAF_SPEED_LIMIT, module="safety", severity=Severity.CRITICAL,
        recoverable=True, retryable=False, default_recovery_policy="reduce_speed",
        safety_related=True,
    ),
    ErrorCode.SAF_WORKSPACE_VIOLATION: ErrorCodeSpec(
        code=ErrorCode.SAF_WORKSPACE_VIOLATION, module="safety", severity=Severity.CRITICAL,
        recoverable=True, retryable=False, default_recovery_policy="return_to_workspace",
        safety_related=True,
    ),
    ErrorCode.SAF_HUMAN_PROXIMITY: ErrorCodeSpec(
        code=ErrorCode.SAF_HUMAN_PROXIMITY, module="safety", severity=Severity.CRITICAL,
        recoverable=True, retryable=False, default_recovery_policy="slow_and_wait",
        safety_related=True,
    ),
    # Communication
    ErrorCode.COM_CLOUD_DISCONNECTED: ErrorCodeSpec(
        code=ErrorCode.COM_CLOUD_DISCONNECTED, module="communication", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="operate_autonomously",
        escalate_to_cloud=True,
    ),
    ErrorCode.COM_SERVICE_TIMEOUT: ErrorCodeSpec(
        code=ErrorCode.COM_SERVICE_TIMEOUT, module="communication", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="retry_with_backoff",
    ),
    ErrorCode.COM_INVALID_RESPONSE: ErrorCodeSpec(
        code=ErrorCode.COM_INVALID_RESPONSE, module="communication", severity=Severity.ERROR,
        recoverable=True, retryable=True, default_recovery_policy="retry_request",
    ),
    # Task
    ErrorCode.TSK_INSTRUCTION_UNCLEAR: ErrorCodeSpec(
        code=ErrorCode.TSK_INSTRUCTION_UNCLEAR, module="task", severity=Severity.WARNING,
        recoverable=True, retryable=False, default_recovery_policy="ask_user_clarification",
        escalate_to_user=True,
    ),
    ErrorCode.TSK_PLAN_INVALID: ErrorCodeSpec(
        code=ErrorCode.TSK_PLAN_INVALID, module="task", severity=Severity.ERROR,
        recoverable=True, retryable=False, default_recovery_policy="replan",
        escalate_to_cloud=True,
    ),
    ErrorCode.TSK_SKILL_NOT_FOUND: ErrorCodeSpec(
        code=ErrorCode.TSK_SKILL_NOT_FOUND, module="task", severity=Severity.ERROR,
        recoverable=False, retryable=False, escalate_to_cloud=True,
    ),
    ErrorCode.TSK_PRECONDITION_FAILED: ErrorCodeSpec(
        code=ErrorCode.TSK_PRECONDITION_FAILED, module="task", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="satisfy_precondition",
    ),
    ErrorCode.TSK_POSTCONDITION_FAILED: ErrorCodeSpec(
        code=ErrorCode.TSK_POSTCONDITION_FAILED, module="task", severity=Severity.WARNING,
        recoverable=True, retryable=True, default_recovery_policy="retry_skill",
    ),
    ErrorCode.TSK_MAX_RETRY_EXCEEDED: ErrorCodeSpec(
        code=ErrorCode.TSK_MAX_RETRY_EXCEEDED, module="task", severity=Severity.ERROR,
        recoverable=False, retryable=False, default_recovery_policy="escalate",
        escalate_to_cloud=True, escalate_to_user=True,
    ),
}
