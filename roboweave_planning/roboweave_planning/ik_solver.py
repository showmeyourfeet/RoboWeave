"""IKSolver abstract interface and IKResult dataclass."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from roboweave_interfaces.world_state import SE3


@dataclass
class IKResult:
    """Result of an IK solve call."""

    reachable: bool
    ik_solution: list[float]
    failure_code: str
    manipulability: float


class IKSolver(ABC):
    """Abstract base class for inverse kinematics solvers."""

    @abstractmethod
    def solve(
        self,
        target_pose: SE3,
        arm_id: str,
        seed_joint_state: list[float] | None = None,
    ) -> IKResult:
        """Solve IK for the given target pose."""
        ...

    @abstractmethod
    def get_backend_name(self) -> str:
        """Return the name of this backend."""
        ...

    @abstractmethod
    def get_joint_count(self, arm_id: str) -> int:
        """Return the number of joints for the specified arm."""
        ...
