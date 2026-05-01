"""Pure functions for Pydantic ↔ ROS2 message conversion.

Since ROS2 may not be available, converters work with dict representations
of messages when ROS2 imports fail. Follows the same pattern as
roboweave_perception/converters.py.
"""

from __future__ import annotations

from typing import Any

from roboweave_interfaces.grasp import GraspCandidate, GraspConstraints
from roboweave_interfaces.motion import TrajectoryPoint, TrajectoryResult
from roboweave_interfaces.world_state import SE3

from .ik_solver import IKResult
from .collision_checker import CollisionResult

# Try importing ROS2 message types; fall back to dict-based approach
try:
    from geometry_msgs.msg import Pose, Point, Quaternion

    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False


# --- SE3 ↔ Pose conversion ---


def se3_to_pose_dict(se3: SE3) -> dict[str, Any]:
    """Convert SE3 to a dict representing geometry_msgs/Pose."""
    return {
        "position": {
            "x": se3.position[0],
            "y": se3.position[1],
            "z": se3.position[2],
        },
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


# --- GraspCandidate conversion ---


def grasp_candidate_to_msg(gc: GraspCandidate) -> dict[str, Any]:
    """Convert GraspCandidate Pydantic model to a msg dict."""
    return {
        "grasp_id": gc.grasp_id,
        "grasp_pose": se3_to_pose_dict(gc.grasp_pose),
        "approach_direction": list(gc.approach_direction),
        "gripper_width": gc.gripper_width,
        "grasp_score": gc.grasp_score,
        "collision_score": gc.collision_score,
        "reachable": gc.reachable,
        "matched_regions": list(gc.matched_regions),
        "ik_solution": list(gc.ik_solution),
    }


def msg_to_grasp_candidate(msg: dict[str, Any]) -> GraspCandidate:
    """Convert a msg dict to GraspCandidate Pydantic model."""
    grasp_pose = pose_dict_to_se3(msg.get("grasp_pose", {}))
    return GraspCandidate(
        grasp_id=msg.get("grasp_id", ""),
        grasp_pose=grasp_pose,
        approach_direction=msg.get("approach_direction", [0.0, 0.0, -1.0]),
        gripper_width=msg.get("gripper_width", 0.0),
        grasp_score=msg.get("grasp_score", 0.0),
        collision_score=msg.get("collision_score", 0.0),
        reachable=msg.get("reachable"),
        matched_regions=msg.get("matched_regions", []),
        ik_solution=msg.get("ik_solution", []),
    )


# --- GraspConstraints conversion ---


def grasp_constraints_to_msg(gc: GraspConstraints) -> dict[str, Any]:
    """Convert GraspConstraints Pydantic model to a msg dict."""
    return {
        "preferred_regions": list(gc.preferred_regions),
        "avoid_regions": list(gc.avoid_regions),
        "max_force": gc.max_force,
        "min_gripper_width": gc.min_gripper_width,
        "max_gripper_width": gc.max_gripper_width,
        "approach_direction_hint": list(gc.approach_direction_hint),
    }


def msg_to_grasp_constraints(msg: dict[str, Any]) -> GraspConstraints:
    """Convert a msg dict to GraspConstraints Pydantic model."""
    return GraspConstraints(
        preferred_regions=msg.get("preferred_regions", []),
        avoid_regions=msg.get("avoid_regions", []),
        max_force=msg.get("max_force", 20.0),
        min_gripper_width=msg.get("min_gripper_width", 0.0),
        max_gripper_width=msg.get("max_gripper_width", 0.1),
        approach_direction_hint=msg.get("approach_direction_hint", []),
    )


# --- TrajectoryResult ↔ JointTrajectory conversion ---


def trajectory_result_to_joint_trajectory(tr: TrajectoryResult) -> dict[str, Any]:
    """Convert TrajectoryResult to a trajectory_msgs/JointTrajectory dict."""
    points = []
    for pt in tr.trajectory:
        points.append({
            "positions": list(pt.positions),
            "velocities": list(pt.velocities),
            "accelerations": list(pt.accelerations),
            "time_from_start": {
                "sec": int(pt.time_from_start_sec),
                "nanosec": int(
                    (pt.time_from_start_sec - int(pt.time_from_start_sec)) * 1e9
                ),
            },
        })
    return {
        "joint_names": [],
        "points": points,
        "duration_sec": tr.duration_sec,
        "collision_free": tr.collision_free,
        "failure_code": tr.failure_code,
        "message": tr.message,
    }


def joint_trajectory_to_trajectory_result(msg: dict[str, Any]) -> TrajectoryResult:
    """Convert a trajectory_msgs/JointTrajectory dict to TrajectoryResult."""
    points = []
    for pt in msg.get("points", []):
        time_from_start = pt.get("time_from_start", {})
        if isinstance(time_from_start, dict):
            sec = time_from_start.get("sec", 0)
            nanosec = time_from_start.get("nanosec", 0)
            t = sec + nanosec / 1e9
        else:
            t = float(time_from_start)
        points.append(TrajectoryPoint(
            positions=pt.get("positions", []),
            velocities=pt.get("velocities", []),
            accelerations=pt.get("accelerations", []),
            time_from_start_sec=t,
        ))
    return TrajectoryResult(
        trajectory=points,
        duration_sec=msg.get("duration_sec", 0.0),
        collision_free=msg.get("collision_free", True),
        failure_code=msg.get("failure_code", ""),
        message=msg.get("message", ""),
    )


# --- IKResult ↔ ReachabilityResult conversion ---


def ik_result_to_reachability_msg(ik: IKResult) -> dict[str, Any]:
    """Convert IKResult dataclass to a ReachabilityResult msg dict."""
    return {
        "reachable": ik.reachable,
        "ik_solution": list(ik.ik_solution),
        "failure_code": ik.failure_code,
        "manipulability": ik.manipulability,
    }


def reachability_msg_to_ik_result(msg: dict[str, Any]) -> IKResult:
    """Convert a ReachabilityResult msg dict to IKResult dataclass."""
    return IKResult(
        reachable=msg.get("reachable", False),
        ik_solution=msg.get("ik_solution", []),
        failure_code=msg.get("failure_code", ""),
        manipulability=msg.get("manipulability", 0.0),
    )


# --- CollisionResult ↔ CollisionPair[] conversion ---


def collision_result_to_msg(cr: CollisionResult) -> dict[str, Any]:
    """Convert CollisionResult to a msg dict with collision pairs."""
    pairs = []
    for obj_a, obj_b, min_dist in cr.collision_pairs:
        pairs.append({
            "object_a": obj_a,
            "object_b": obj_b,
            "min_distance": min_dist,
        })
    return {
        "in_collision": cr.in_collision,
        "collision_pairs": pairs,
    }


def msg_to_collision_result(msg: dict[str, Any]) -> CollisionResult:
    """Convert a msg dict to CollisionResult dataclass."""
    pairs = []
    for p in msg.get("collision_pairs", []):
        pairs.append((
            p.get("object_a", ""),
            p.get("object_b", ""),
            p.get("min_distance", 0.0),
        ))
    return CollisionResult(
        in_collision=msg.get("in_collision", False),
        collision_pairs=pairs,
    )
