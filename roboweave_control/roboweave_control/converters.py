"""Pure functions for Pydantic ↔ ROS2 message conversion.

Since ROS2 may not be available, converters work with dict representations
of messages when ROS2 imports fail.
"""

from __future__ import annotations

from typing import Any

from roboweave_interfaces.control import ControlCommand, ControlStatus
from roboweave_interfaces.hardware import HardwareConfig
from roboweave_interfaces.world_state import (
    ArmState,
    GripperState,
    RobotState,
    SE3,
)

# Try importing ROS2 message types; fall back to dict-based approach
try:
    from roboweave_msgs.msg import (
        ArmState as ArmStateMsg,
        GripperState as GripperStateMsg,
        RobotStateMsg as RobotStateMsgType,
    )
    from geometry_msgs.msg import Pose, Point, Quaternion

    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False


# --- SE3 ↔ Pose conversion ---


def se3_to_pose_dict(se3: SE3) -> dict[str, Any]:
    """Convert SE3 to a dict representing geometry_msgs/Pose."""
    return {
        "position": {"x": se3.position[0], "y": se3.position[1], "z": se3.position[2]},
        "orientation": {
            "x": se3.quaternion[0],
            "y": se3.quaternion[1],
            "z": se3.quaternion[2],
            "w": se3.quaternion[3],
        },
    }


def pose_dict_to_se3(pose: dict[str, Any]) -> SE3:
    """Convert a dict representing geometry_msgs/Pose to SE3."""
    pos = pose.get("position", {})
    ori = pose.get("orientation", {})
    return SE3(
        position=[pos.get("x", 0.0), pos.get("y", 0.0), pos.get("z", 0.0)],
        quaternion=[
            ori.get("x", 0.0),
            ori.get("y", 0.0),
            ori.get("z", 0.0),
            ori.get("w", 1.0),
        ],
    )


# --- ArmState conversion ---


def arm_state_to_msg(arm: ArmState) -> dict[str, Any]:
    """Convert Pydantic ArmState to a msg dict."""
    return {
        "arm_id": arm.arm_id,
        "joint_positions": list(arm.joint_positions),
        "joint_velocities": list(arm.joint_velocities),
        "joint_efforts": list(arm.joint_efforts),
        "eef_pose": se3_to_pose_dict(arm.eef_pose),
        "manipulability": arm.manipulability,
    }


def msg_to_arm_state(msg: dict[str, Any]) -> ArmState:
    """Convert a msg dict to Pydantic ArmState."""
    eef_pose = pose_dict_to_se3(msg.get("eef_pose", {}))
    return ArmState(
        arm_id=msg.get("arm_id", ""),
        joint_positions=msg.get("joint_positions", []),
        joint_velocities=msg.get("joint_velocities", []),
        joint_efforts=msg.get("joint_efforts", []),
        eef_pose=eef_pose,
        manipulability=msg.get("manipulability", 0.0),
    )


# --- GripperState conversion ---


def gripper_state_to_msg(gs: GripperState) -> dict[str, Any]:
    """Convert Pydantic GripperState to a msg dict."""
    return {
        "gripper_id": gs.gripper_id,
        "type": gs.type,
        "width": gs.width,
        "force": gs.force,
        "is_grasping": gs.is_grasping,
        "grasped_object_id": gs.grasped_object_id,
    }


def msg_to_gripper_state(msg: dict[str, Any]) -> GripperState:
    """Convert a msg dict to Pydantic GripperState."""
    return GripperState(
        gripper_id=msg.get("gripper_id", ""),
        type=msg.get("type", "parallel"),
        width=msg.get("width", 0.0),
        force=msg.get("force", 0.0),
        is_grasping=msg.get("is_grasping", False),
        grasped_object_id=msg.get("grasped_object_id", ""),
    )


# --- RobotState conversion ---


def robot_state_to_msg(rs: RobotState) -> dict[str, Any]:
    """Convert Pydantic RobotState to a msg dict."""
    return {
        "robot_id": rs.robot_id,
        "arms": [arm_state_to_msg(a) for a in rs.arms],
        "grippers": [gripper_state_to_msg(g) for g in rs.grippers],
        "base_pose": se3_to_pose_dict(rs.base_pose) if rs.base_pose else None,
        "is_moving": rs.is_moving,
        "current_control_mode": rs.current_control_mode,
    }


def msg_to_robot_state(msg: dict[str, Any]) -> RobotState:
    """Convert a msg dict to Pydantic RobotState."""
    arms = [msg_to_arm_state(a) for a in msg.get("arms", [])]
    grippers = [msg_to_gripper_state(g) for g in msg.get("grippers", [])]
    base_pose = pose_dict_to_se3(msg["base_pose"]) if msg.get("base_pose") else None
    return RobotState(
        robot_id=msg.get("robot_id", ""),
        arms=arms,
        grippers=grippers,
        base_pose=base_pose,
        is_moving=msg.get("is_moving", False),
        current_control_mode=msg.get("current_control_mode", "position"),
    )


# --- HardwareConfig YAML conversion ---


def hardware_config_from_yaml(data: dict[str, Any]) -> HardwareConfig:
    """Parse a YAML dict into a HardwareConfig Pydantic model."""
    return HardwareConfig.model_validate(data)


def hardware_config_to_yaml(config: HardwareConfig) -> dict[str, Any]:
    """Serialize a HardwareConfig to a YAML-safe dict."""
    return config.model_dump(mode="python")
