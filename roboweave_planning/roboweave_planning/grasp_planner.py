"""GraspPlanner abstract interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from roboweave_interfaces.grasp import GraspCandidate, GraspConstraints


class GraspPlanner(ABC):
    """Abstract base class for grasp planners."""

    @abstractmethod
    def plan_grasps(
        self,
        point_cloud: np.ndarray,
        object_id: str,
        constraints: GraspConstraints,
        arm_id: str,
    ) -> list[GraspCandidate]:
        """Plan grasps for the given point cloud and constraints."""
        ...

    @abstractmethod
    def get_backend_name(self) -> str:
        """Return the name of this backend."""
        ...
