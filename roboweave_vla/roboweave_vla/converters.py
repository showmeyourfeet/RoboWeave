"""Pure functions for VLA Pydantic ↔ ROS2 msg dict conversion.

No ROS2 imports at module level — follows the project convention.
"""

from __future__ import annotations

from typing import Any

from roboweave_interfaces.vla import (
    VLAAction,
    VLAActionSpace,
    VLAActionType,
    VLASafetyConstraints,
)
from roboweave_interfaces.world_state import SE3


def _se3_to_dict(se3: SE3 | None) -> dict[str, Any] | None:
    if se3 is None:
        return None
    return {
        "position": list(se3.position),
        "quaternion": list(se3.quaternion),
    }


def _dict_to_se3(d: dict[str, Any] | None) -> SE3 | None:
    if d is None:
        return None
    return SE3(
        position=d.get("position", [0.0, 0.0, 0.0]),
        quaternion=d.get("quaternion", [0.0, 0.0, 0.0, 1.0]),
    )


def vla_action_to_msg(action: VLAAction) -> dict[str, Any]:
    """Convert a VLAAction Pydantic model to a msg dict."""
    return {
        "action_type": action.action_type.value,
        "frame_id": action.frame_id,
        "delta_pose": _se3_to_dict(action.delta_pose),
        "target_pose": _se3_to_dict(action.target_pose),
        "joint_delta": list(action.joint_delta),
        "gripper_command": dict(action.gripper_command),
        "confidence": action.confidence,
        "horizon_steps": action.horizon_steps,
        "requires_safety_filter": action.requires_safety_filter,
    }


def msg_to_vla_action(msg: dict[str, Any]) -> VLAAction:
    """Convert a msg dict to a VLAAction Pydantic model."""
    return VLAAction(
        action_type=VLAActionType(msg["action_type"]),
        frame_id=msg.get("frame_id", "base_link"),
        delta_pose=_dict_to_se3(msg.get("delta_pose")),
        target_pose=_dict_to_se3(msg.get("target_pose")),
        joint_delta=msg.get("joint_delta", []),
        gripper_command=msg.get("gripper_command", {}),
        confidence=msg.get("confidence", 0.0),
        horizon_steps=msg.get("horizon_steps", 1),
        requires_safety_filter=msg.get("requires_safety_filter", True),
    )


def vla_safety_constraints_to_msg(c: VLASafetyConstraints) -> dict[str, Any]:
    """Convert VLASafetyConstraints to a msg dict."""
    return {
        "max_velocity": c.max_velocity,
        "max_angular_velocity": c.max_angular_velocity,
        "force_limit": c.force_limit,
        "torque_limit": c.torque_limit,
        "workspace_limit_id": c.workspace_limit_id,
        "max_duration_sec": c.max_duration_sec,
        "allow_contact": c.allow_contact,
        "min_confidence_threshold": c.min_confidence_threshold,
    }


def msg_to_vla_safety_constraints(msg: dict[str, Any]) -> VLASafetyConstraints:
    """Convert a msg dict to VLASafetyConstraints."""
    return VLASafetyConstraints(
        max_velocity=msg.get("max_velocity", 0.25),
        max_angular_velocity=msg.get("max_angular_velocity", 0.5),
        force_limit=msg.get("force_limit", 20.0),
        torque_limit=msg.get("torque_limit", 10.0),
        workspace_limit_id=msg.get("workspace_limit_id", ""),
        max_duration_sec=msg.get("max_duration_sec", 60.0),
        allow_contact=msg.get("allow_contact", False),
        min_confidence_threshold=msg.get("min_confidence_threshold", 0.3),
    )


def vla_action_space_to_msg(space: VLAActionSpace) -> dict[str, Any]:
    """Convert VLAActionSpace to a msg dict."""
    return {
        "supported_action_types": [t.value for t in space.supported_action_types],
        "max_delta_position": space.max_delta_position,
        "max_delta_rotation": space.max_delta_rotation,
        "max_joint_delta": space.max_joint_delta,
        "control_frequency_hz": space.control_frequency_hz,
    }


def msg_to_vla_action_space(msg: dict[str, Any]) -> VLAActionSpace:
    """Convert a msg dict to VLAActionSpace."""
    return VLAActionSpace(
        supported_action_types=[
            VLAActionType(t) for t in msg.get("supported_action_types", [])
        ],
        max_delta_position=msg.get("max_delta_position", 0.05),
        max_delta_rotation=msg.get("max_delta_rotation", 0.1),
        max_joint_delta=msg.get("max_joint_delta", 0.1),
        control_frequency_hz=msg.get("control_frequency_hz", 10.0),
    )
