"""Converters — ROS2 msg dict ↔ Pydantic model conversion helpers.

These converters work with dictionary representations of ROS2 messages,
allowing the safety package to be tested without ROS2 dependencies.
"""

from __future__ import annotations

import json

from roboweave_interfaces.base import JsonEnvelope
from roboweave_interfaces.safety import SafetyLevel
from roboweave_interfaces.vla import VLAAction, VLASafetyConstraints
from roboweave_interfaces.world_state import ArmState, SE3

from .safety_guard import SafetyGuard


def robot_state_msg_to_arms(msg_dict: dict) -> list[ArmState]:
    """Convert a RobotStateMsg dictionary to a list of ArmState."""
    arms: list[ArmState] = []
    for arm_data in msg_dict.get("arms", []):
        eef_pose_data = arm_data.get("eef_pose", {})
        position = eef_pose_data.get("position", [0.0, 0.0, 0.0])
        quaternion = eef_pose_data.get("quaternion", [0.0, 0.0, 0.0, 1.0])

        # Handle geometry_msgs/Pose format
        if "position" not in eef_pose_data and "x" in eef_pose_data:
            position = [
                eef_pose_data.get("x", 0.0),
                eef_pose_data.get("y", 0.0),
                eef_pose_data.get("z", 0.0),
            ]
        orient = eef_pose_data.get("orientation", {})
        if orient:
            quaternion = [
                orient.get("x", 0.0),
                orient.get("y", 0.0),
                orient.get("z", 0.0),
                orient.get("w", 1.0),
            ]

        arms.append(ArmState(
            arm_id=arm_data.get("arm_id", ""),
            joint_positions=arm_data.get("joint_positions", []),
            joint_velocities=arm_data.get("joint_velocities", []),
            joint_efforts=arm_data.get("joint_efforts", []),
            eef_pose=SE3(position=position, quaternion=quaternion),
        ))
    return arms


def safety_status_to_msg(
    level: SafetyLevel, guard: SafetyGuard, heartbeat: float
) -> dict:
    """Build a SafetyStatus message dict from guard state."""
    return {
        "level": level.value,
        "e_stop_active": guard.e_stop_active,
        "e_stop_latched": guard.e_stop_latched,
        "active_violations": guard.active_violations,
        "heartbeat": heartbeat,
    }


def json_envelope_to_vla_action(json_str: str) -> VLAAction:
    """Deserialize a JsonEnvelope payload to VLAAction."""
    envelope = JsonEnvelope.model_validate_json(json_str)
    return VLAAction.model_validate_json(envelope.payload_json)


def json_envelope_to_vla_constraints(json_str: str) -> VLASafetyConstraints:
    """Deserialize a JsonEnvelope payload to VLASafetyConstraints."""
    envelope = JsonEnvelope.model_validate_json(json_str)
    return VLASafetyConstraints.model_validate_json(envelope.payload_json)


def vla_action_to_json_envelope(action: VLAAction) -> str:
    """Serialize a VLAAction to a JsonEnvelope JSON string."""
    envelope = JsonEnvelope.wrap(action)
    return envelope.model_dump_json()
