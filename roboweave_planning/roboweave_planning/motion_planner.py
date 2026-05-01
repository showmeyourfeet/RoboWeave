"""MotionPlanner abstract interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from roboweave_interfaces.motion import MotionRequest, TrajectoryResult


class MotionPlanner(ABC):
    """Abstract base class for motion planners."""

    @abstractmethod
    def plan(
        self,
        request: MotionRequest,
        current_joint_state: list[float],
    ) -> TrajectoryResult:
        """Plan a trajectory from current state to the goal."""
        ...

    @abstractmethod
    def get_backend_name(self) -> str:
        """Return the name of this backend."""
        ...
