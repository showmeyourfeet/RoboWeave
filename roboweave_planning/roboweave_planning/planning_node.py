"""PlanningNode - Main entry point for roboweave_planning.

If ROS2 (rclpy) is available, runs as a ROS2 node.
Otherwise, provides the class structure for standalone use.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from .backend_registry import get_backend, list_backends
from .collision_checker import CollisionChecker
from .converters import (
    collision_result_to_msg,
    grasp_candidate_to_msg,
    ik_result_to_reachability_msg,
    msg_to_grasp_constraints,
    pose_dict_to_se3,
    trajectory_result_to_joint_trajectory,
)
from .grasp_planner import GraspPlanner
from .ik_solver import IKSolver
from .motion_planner import MotionPlanner

logger = logging.getLogger(__name__)

# Try importing ROS2
try:
    import rclpy
    from rclpy.node import Node

    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False
    Node = object  # type: ignore[assignment,misc]


class PlanningNode(Node):  # type: ignore[misc]
    """Main planning node hosting services and action server."""

    def __init__(
        self,
        planning_params_path: str = "",
        planning_backends_path: str = "",
        **kwargs: Any,
    ) -> None:
        if HAS_ROS2:
            super().__init__("planning_node", **kwargs)
            self.declare_parameter("planning_params_path", planning_params_path)
            self.declare_parameter("planning_backends_path", planning_backends_path)
            planning_params_path = (
                self.get_parameter("planning_params_path").value
            )
            planning_backends_path = (
                self.get_parameter("planning_backends_path").value
            )

        # Default parameters
        self._max_planning_time_ms = 5000
        self._default_velocity_scaling = 0.5
        self._default_acceleration_scaling = 0.5
        self._min_trajectory_points = 10
        self._max_grasp_candidates = 5
        self._max_joint_velocity = 1.5

        if planning_params_path:
            self._load_planning_params(planning_params_path)

        # Import backends to trigger registration
        import roboweave_planning.backends  # noqa: F401

        # Instantiate backends
        self._grasp_planner: GraspPlanner | None = None
        self._ik_solver: IKSolver | None = None
        self._collision_checker: CollisionChecker | None = None
        self._motion_planner: MotionPlanner | None = None

        if planning_backends_path:
            self._load_backends(planning_backends_path)
        else:
            self._load_default_backends()

        # Set up ROS2 services (if available)
        if HAS_ROS2:
            self._setup_services()

        logger.info("PlanningNode started successfully.")

    def _load_planning_params(self, path: str) -> None:
        """Load planning parameters from YAML."""
        p = Path(path)
        if not p.exists():
            logger.error(f"Planning params not found: {path}")
            return

        with open(p) as f:
            data = yaml.safe_load(f)

        params = data.get("planning", {})
        self._max_planning_time_ms = params.get(
            "max_planning_time_ms", self._max_planning_time_ms
        )
        self._default_velocity_scaling = params.get(
            "default_velocity_scaling", self._default_velocity_scaling
        )
        self._default_acceleration_scaling = params.get(
            "default_acceleration_scaling", self._default_acceleration_scaling
        )
        self._min_trajectory_points = params.get(
            "min_trajectory_points", self._min_trajectory_points
        )
        self._max_grasp_candidates = params.get(
            "max_grasp_candidates", self._max_grasp_candidates
        )
        self._max_joint_velocity = params.get(
            "max_joint_velocity", self._max_joint_velocity
        )

    def _load_backends(self, path: str) -> None:
        """Load backends from planning_backends.yaml."""
        p = Path(path)
        if not p.exists():
            logger.error(f"Planning backends config not found: {path}")
            self._load_default_backends()
            return

        with open(p) as f:
            data = yaml.safe_load(f)

        # Grasp planner
        gp_cfg = data.get("grasp_planner", {})
        self._grasp_planner = self._get_backend_safe(
            "grasp_planner", gp_cfg.get("active", "mock")
        )

        # IK solver
        ik_cfg = data.get("ik_solver", {})
        self._ik_solver = self._get_backend_safe(
            "ik_solver", ik_cfg.get("active", "mock")
        )

        # Collision checker
        cc_cfg = data.get("collision_checker", {})
        self._collision_checker = self._get_backend_safe(
            "collision_checker", cc_cfg.get("active", "mock")
        )

        # Motion planner (needs ik_solver)
        mp_cfg = data.get("motion_planner", {})
        mp_params = mp_cfg.get("params", {})
        self._motion_planner = self._get_backend_safe(
            "motion_planner",
            mp_cfg.get("active", "simple"),
            ik_solver=self._ik_solver,
            num_interpolation_points=mp_params.get(
                "num_interpolation_points", self._min_trajectory_points
            ),
            max_joint_velocity=self._max_joint_velocity,
        )

    def _load_default_backends(self) -> None:
        """Load default mock/simple backends."""
        self._grasp_planner = self._get_backend_safe("grasp_planner", "mock")
        self._ik_solver = self._get_backend_safe("ik_solver", "mock")
        self._collision_checker = self._get_backend_safe(
            "collision_checker", "mock"
        )
        self._motion_planner = self._get_backend_safe(
            "motion_planner", "simple",
            ik_solver=self._ik_solver,
            num_interpolation_points=self._min_trajectory_points,
            max_joint_velocity=self._max_joint_velocity,
        )

    def _get_backend_safe(self, capability: str, name: str, **kwargs):
        """Get a backend, falling back to mock/simple on error."""
        try:
            backend = get_backend(capability, name, **kwargs)
            logger.info(f"Loaded {capability} backend: {name}")
            return backend
        except KeyError:
            logger.error(
                f"Backend '{name}' not found for '{capability}', "
                f"falling back to default"
            )
            fallback = "simple" if capability == "motion_planner" else "mock"
            try:
                return get_backend(capability, fallback, **kwargs)
            except KeyError:
                logger.error(
                    f"Fallback backend also not found for '{capability}'"
                )
                return None

    def _setup_services(self) -> None:
        """Set up ROS2 service and action servers."""
        # TODO: Create service servers for plan_grasp, check_reachability,
        # check_collision on /roboweave/planning/ namespace
        # TODO: Create action server for plan_motion
        pass

    def _handle_plan_grasp(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle PlanGrasp service request."""
        try:
            # Resolve point cloud from request
            point_cloud = request.get("point_cloud")
            if point_cloud is None:
                point_cloud = np.empty((0, 3), dtype=np.float64)
            elif not isinstance(point_cloud, np.ndarray):
                point_cloud = np.array(point_cloud, dtype=np.float64)

            object_id = request.get("object_id", "")
            arm_id = request.get("arm_id", "")
            constraints_dict = request.get("constraints", {})
            constraints = msg_to_grasp_constraints(constraints_dict)

            candidates = self._grasp_planner.plan_grasps(
                point_cloud, object_id, constraints, arm_id
            )

            if not candidates:
                return {
                    "success": False,
                    "error_code": "GRP_NO_GRASP_FOUND",
                    "error_message": "No grasp candidates found.",
                    "candidates": [],
                }

            return {
                "success": True,
                "error_code": "",
                "error_message": "",
                "candidates": [
                    grasp_candidate_to_msg(c) for c in candidates
                ],
            }
        except Exception as e:
            return {
                "success": False,
                "error_code": "GRP_PLANNING_FAILED",
                "error_message": str(e),
                "candidates": [],
            }

    def _handle_check_reachability(
        self, request: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle CheckReachability service request."""
        try:
            target_pose_dict = request.get("target_pose", {})
            target_pose = pose_dict_to_se3(target_pose_dict)
            arm_id = request.get("arm_id", "")
            seed = request.get("current_joint_state")

            result = self._ik_solver.solve(target_pose, arm_id, seed)
            return {
                "success": True,
                "error_code": "",
                "error_message": "",
                "result": ik_result_to_reachability_msg(result),
            }
        except Exception as e:
            return {
                "success": False,
                "error_code": "IK_SOLVER_FAILED",
                "error_message": str(e),
                "result": {},
            }

    def _handle_check_collision(
        self, request: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle CheckCollision service request."""
        try:
            joint_state = request.get("joint_state", [])
            arm_id = request.get("arm_id", "")
            ignore_objects = request.get("ignore_objects", [])

            result = self._collision_checker.check(
                joint_state, arm_id, ignore_objects
            )
            return {
                "success": True,
                "error_code": "",
                "error_message": "",
                "result": collision_result_to_msg(result),
            }
        except Exception as e:
            return {
                "success": False,
                "error_code": "COL_CHECK_FAILED",
                "error_message": str(e),
                "result": {},
            }

    def _handle_plan_motion(self, goal: dict[str, Any]) -> dict[str, Any]:
        """Handle PlanMotion action goal."""
        try:
            from roboweave_interfaces.motion import MotionRequest
            from roboweave_interfaces.world_state import SE3

            arm_id = goal.get("arm_id", "")
            goal_pose_dict = goal.get("goal_pose")
            goal_joint_state = goal.get("goal_joint_state")
            planning_mode = goal.get("planning_mode", "joint_space")
            max_velocity_scaling = goal.get(
                "max_velocity_scaling", self._default_velocity_scaling
            )
            max_acceleration_scaling = goal.get(
                "max_acceleration_scaling", self._default_acceleration_scaling
            )
            ignore_objects = goal.get("ignore_collision_objects", [])
            max_planning_time_ms = goal.get(
                "max_planning_time_ms", self._max_planning_time_ms
            )

            goal_pose = None
            if goal_pose_dict:
                goal_pose = pose_dict_to_se3(goal_pose_dict)

            request = MotionRequest(
                arm_id=arm_id,
                goal_pose=goal_pose,
                goal_joint_state=goal_joint_state,
                planning_mode=planning_mode,
                max_velocity_scaling=max_velocity_scaling,
                max_acceleration_scaling=max_acceleration_scaling,
                ignore_collision_objects=ignore_objects,
                max_planning_time_ms=max_planning_time_ms,
            )

            current_joints = goal.get("current_joint_state", [0.0] * 6)
            result = self._motion_planner.plan(request, current_joints)

            if result.failure_code:
                return {
                    "success": False,
                    "trajectory": {},
                    "duration_sec": 0.0,
                    "collision_free": False,
                    "failure_code": result.failure_code,
                    "message": result.message,
                }

            return {
                "success": True,
                "trajectory": trajectory_result_to_joint_trajectory(result),
                "duration_sec": result.duration_sec,
                "collision_free": result.collision_free,
                "failure_code": "",
                "message": "",
            }
        except Exception as e:
            return {
                "success": False,
                "trajectory": {},
                "duration_sec": 0.0,
                "collision_free": False,
                "failure_code": "MOT_PLANNING_FAILED",
                "message": str(e),
            }

    def shutdown(self) -> None:
        """Release backend resources."""
        logger.info("PlanningNode shutting down.")


def main() -> None:
    """Entry point for the planning node."""
    if HAS_ROS2:
        rclpy.init()
        node = PlanningNode()
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            node.shutdown()
            node.destroy_node()
            rclpy.shutdown()
    else:
        logger.warning(
            "ROS2 not available. PlanningNode requires rclpy to run."
        )


if __name__ == "__main__":
    main()
