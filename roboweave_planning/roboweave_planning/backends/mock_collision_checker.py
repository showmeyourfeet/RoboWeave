"""Mock collision checker backend for testing."""

from __future__ import annotations

from roboweave_interfaces.world_state import SE3, BoundingBox3D

from ..backend_registry import register_backend, COLLISION_CHECKER
from ..collision_checker import CollisionChecker, CollisionResult


@register_backend(COLLISION_CHECKER, "mock")
class MockCollisionChecker(CollisionChecker):
    """Mock collision checker that always reports no collision."""

    def check(
        self,
        joint_state: list[float],
        arm_id: str,
        ignore_objects: list[str] | None = None,
    ) -> CollisionResult:
        """Return no-collision result."""
        return CollisionResult(in_collision=False, collision_pairs=[])

    def get_backend_name(self) -> str:
        """Return backend name."""
        return "mock"

    def update_scene(
        self,
        objects: list[tuple[str, SE3, BoundingBox3D]],
    ) -> None:
        """No-op scene update."""
        pass
