"""Mock IK solver backend for testing."""

from __future__ import annotations

from roboweave_interfaces.world_state import SE3

from ..backend_registry import register_backend, IK_SOLVER
from ..ik_solver import IKResult, IKSolver


@register_backend(IK_SOLVER, "mock")
class MockIKSolver(IKSolver):
    """Mock IK solver that always returns a reachable result."""

    def solve(
        self,
        target_pose: SE3,
        arm_id: str,
        seed_joint_state: list[float] | None = None,
    ) -> IKResult:
        """Return a deterministic reachable result."""
        return IKResult(
            reachable=True,
            ik_solution=[0.0] * 6,
            failure_code="",
            manipulability=0.5,
        )

    def get_backend_name(self) -> str:
        """Return backend name."""
        return "mock"

    def get_joint_count(self, arm_id: str) -> int:
        """Return 6 joints for any arm."""
        return 6
