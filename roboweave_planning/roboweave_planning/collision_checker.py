"""CollisionChecker abstract interface and CollisionResult dataclass."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from roboweave_interfaces.world_state import SE3, BoundingBox3D


@dataclass
class CollisionResult:
    """Result of a collision check call."""

    in_collision: bool
    collision_pairs: list[tuple[str, str, float]] = field(default_factory=list)


class CollisionChecker(ABC):
    """Abstract base class for collision checkers."""

    @abstractmethod
    def check(
        self,
        joint_state: list[float],
        arm_id: str,
        ignore_objects: list[str] | None = None,
    ) -> CollisionResult:
        """Check if the given joint state is in collision."""
        ...

    @abstractmethod
    def get_backend_name(self) -> str:
        """Return the name of this backend."""
        ...

    @abstractmethod
    def update_scene(
        self,
        objects: list[tuple[str, SE3, BoundingBox3D]],
    ) -> None:
        """Update the internal collision world representation."""
        ...
