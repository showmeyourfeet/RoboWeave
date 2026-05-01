"""Simple linear-interpolation motion planner backend."""

from __future__ import annotations

from roboweave_interfaces.motion import MotionRequest, TrajectoryPoint, TrajectoryResult

from ..backend_registry import register_backend, MOTION_PLANNER
from ..ik_solver import IKSolver
from ..motion_planner import MotionPlanner


@register_backend(MOTION_PLANNER, "simple")
class SimpleMotionPlanner(MotionPlanner):
    """Motion planner using linear interpolation in joint space."""

    def __init__(
        self,
        ik_solver: IKSolver,
        num_interpolation_points: int = 20,
        max_joint_velocity: float = 1.5,
    ) -> None:
        self._ik_solver = ik_solver
        self._num_points = max(num_interpolation_points, 10)
        self._max_joint_velocity = max_joint_velocity

    def plan(
        self,
        request: MotionRequest,
        current_joint_state: list[float],
    ) -> TrajectoryResult:
        """Plan a trajectory via linear interpolation."""
        # Check for no-goal case
        if not request.goal_joint_state and request.goal_pose is None:
            return TrajectoryResult(
                failure_code="MOT_NO_GOAL",
                message="No goal_joint_state and no goal_pose provided.",
            )

        # Resolve goal joints
        if request.planning_mode in ("cartesian", "cartesian_linear"):
            if request.goal_pose is not None and not request.goal_joint_state:
                ik_result = self._ik_solver.solve(
                    request.goal_pose, request.arm_id
                )
                if not ik_result.reachable:
                    return TrajectoryResult(
                        failure_code="IK_NO_SOLUTION",
                        message="IK solver could not find a solution.",
                    )
                goal_joints = ik_result.ik_solution
            elif request.goal_joint_state:
                goal_joints = list(request.goal_joint_state)
            else:
                return TrajectoryResult(
                    failure_code="MOT_NO_GOAL",
                    message="No goal_joint_state and no goal_pose provided.",
                )
        else:
            # joint_space mode
            if request.goal_joint_state:
                goal_joints = list(request.goal_joint_state)
            elif request.goal_pose is not None:
                ik_result = self._ik_solver.solve(
                    request.goal_pose, request.arm_id
                )
                if not ik_result.reachable:
                    return TrajectoryResult(
                        failure_code="IK_NO_SOLUTION",
                        message="IK solver could not find a solution.",
                    )
                goal_joints = ik_result.ik_solution
            else:
                return TrajectoryResult(
                    failure_code="MOT_NO_GOAL",
                    message="No goal_joint_state and no goal_pose provided.",
                )

        return self._interpolate(current_joint_state, goal_joints, request)

    def _interpolate(
        self,
        q_s: list[float],
        q_g: list[float],
        request: MotionRequest,
    ) -> TrajectoryResult:
        """Generate linearly interpolated trajectory."""
        n = self._num_points

        # Compute max displacement and duration
        max_disp = max(abs(g - s) for s, g in zip(q_s, q_g)) if q_s else 0.0
        velocity_scaling = request.max_velocity_scaling
        if velocity_scaling <= 0.0:
            velocity_scaling = 0.5

        if max_disp == 0.0:
            duration = 0.0
        else:
            duration = max_disp / (self._max_joint_velocity * velocity_scaling)

        # Compute constant velocities per joint
        if duration > 0.0:
            velocities = [(g - s) / duration for s, g in zip(q_s, q_g)]
        else:
            velocities = [0.0] * len(q_s)

        accelerations = [0.0] * len(q_s)

        # Build trajectory points
        trajectory: list[TrajectoryPoint] = []
        for i in range(n):
            alpha = i / (n - 1) if n > 1 else 0.0
            positions = [s + alpha * (g - s) for s, g in zip(q_s, q_g)]
            time_from_start = alpha * duration

            trajectory.append(TrajectoryPoint(
                positions=positions,
                velocities=list(velocities),
                accelerations=list(accelerations),
                time_from_start_sec=time_from_start,
            ))

        return TrajectoryResult(
            trajectory=trajectory,
            duration_sec=duration,
            collision_free=True,
            failure_code="",
            message="",
        )

    def get_backend_name(self) -> str:
        """Return backend name."""
        return "simple"
