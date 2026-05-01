"""Trajectory execution logic (pure Python core).

The ROS2 action server wiring lives in ControlNode. This class implements
the core execution loop: iterate trajectory points, command the driver,
compute tracking error, and report progress.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from roboweave_interfaces.motion import TrajectoryPoint

from .drivers.base import Driver


@dataclass
class TrajectoryGoal:
    """Goal for trajectory execution."""

    arm_id: str
    points: list[TrajectoryPoint]
    velocity_scaling: float = 0.0  # 0 means use default


@dataclass
class TrajectoryFeedback:
    """Feedback during trajectory execution."""

    progress: float
    tracking_error: float
    current_joint_positions: list[float]


@dataclass
class TrajectoryResult:
    """Result of trajectory execution."""

    success: bool
    error_code: str = ""
    message: str = ""
    max_tracking_error: float = 0.0


class TrajectoryExecutor:
    """Executes joint trajectories on a driver with tracking error monitoring."""

    def __init__(
        self,
        driver: Driver,
        default_velocity_scaling: float = 0.5,
        tracking_error_threshold: float = 0.1,
        control_rate_hz: float = 50.0,
    ) -> None:
        self._driver = driver
        self._default_velocity_scaling = default_velocity_scaling
        self._tracking_error_threshold = tracking_error_threshold
        self._control_dt = 1.0 / control_rate_hz
        self._active_arms: dict[str, bool] = {}

    def is_arm_busy(self, arm_id: str) -> bool:
        """Check if an arm is currently executing a trajectory."""
        return self._active_arms.get(arm_id, False)

    def execute(
        self,
        goal: TrajectoryGoal,
        feedback_callback: Callable[[TrajectoryFeedback], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> TrajectoryResult:
        """Execute a trajectory goal synchronously.

        Args:
            goal: The trajectory goal to execute.
            feedback_callback: Optional callback for progress feedback.
            cancel_check: Optional callable returning True if cancelled.

        Returns:
            TrajectoryResult with success status and tracking info.
        """
        arm_id = goal.arm_id

        # Validate arm exists
        if arm_id not in self._driver._arm_configs:
            return TrajectoryResult(
                success=False,
                error_code="CTL_INVALID_ARM",
                message=f"Unknown arm_id: {arm_id}",
            )

        # Check not busy
        if self.is_arm_busy(arm_id):
            return TrajectoryResult(
                success=False,
                error_code="CTL_ARM_BUSY",
                message=f"Arm {arm_id} is already executing a trajectory",
            )

        # Resolve velocity scaling
        velocity_scaling = goal.velocity_scaling
        if velocity_scaling <= 0.0:
            velocity_scaling = self._default_velocity_scaling
        velocity_scaling = max(0.0, min(1.0, velocity_scaling))

        self._active_arms[arm_id] = True
        max_tracking_error = 0.0

        try:
            points = goal.points
            if not points:
                return TrajectoryResult(success=True, max_tracking_error=0.0)

            for idx, point in enumerate(points):
                # Check cancellation
                if cancel_check and cancel_check():
                    self._driver.emergency_stop()
                    return TrajectoryResult(
                        success=False,
                        error_code="CTL_CANCELLED",
                        message="Trajectory cancelled by user",
                        max_tracking_error=max_tracking_error,
                    )

                # Command the driver
                self._driver.set_joint_positions(
                    arm_id, point.positions, velocity_scaling
                )

                # Determine how long to hold this point
                if idx + 1 < len(points):
                    dt_segment = points[idx + 1].time_from_start_sec - point.time_from_start_sec
                else:
                    dt_segment = 0.5  # Final point: allow settling time

                # Step the driver in control-rate increments
                elapsed = 0.0
                while elapsed < dt_segment:
                    step_dt = min(self._control_dt, dt_segment - elapsed)
                    self._driver.step(step_dt)
                    elapsed += step_dt

                # Compute tracking error
                js = self._driver.get_joint_state(arm_id)
                tracking_error = max(
                    abs(js.positions[i] - point.positions[i])
                    for i in range(len(point.positions))
                )
                max_tracking_error = max(max_tracking_error, tracking_error)

                # Check threshold
                if tracking_error > self._tracking_error_threshold:
                    return TrajectoryResult(
                        success=False,
                        error_code="CTL_TRACKING_ERROR",
                        message=f"Tracking error {tracking_error:.4f} exceeds threshold",
                        max_tracking_error=max_tracking_error,
                    )

                # Publish feedback
                if feedback_callback:
                    progress = (idx + 1) / len(points)
                    feedback_callback(TrajectoryFeedback(
                        progress=progress,
                        tracking_error=tracking_error,
                        current_joint_positions=list(js.positions),
                    ))

            return TrajectoryResult(success=True, max_tracking_error=max_tracking_error)

        finally:
            self._active_arms[arm_id] = False
