"""Mock grasp planner backend for testing."""

from __future__ import annotations

import uuid

import numpy as np

from roboweave_interfaces.grasp import GraspCandidate, GraspConstraints
from roboweave_interfaces.world_state import SE3

from ..backend_registry import register_backend, GRASP_PLANNER
from ..grasp_planner import GraspPlanner


@register_backend(GRASP_PLANNER, "mock")
class MockGraspPlanner(GraspPlanner):
    """Mock grasp planner that returns a single candidate at the centroid."""

    def plan_grasps(
        self,
        point_cloud: np.ndarray,
        object_id: str,
        constraints: GraspConstraints,
        arm_id: str,
    ) -> list[GraspCandidate]:
        """Return one grasp at centroid, or empty list for empty cloud."""
        if point_cloud.size == 0 or len(point_cloud) == 0:
            return []

        centroid = point_cloud.mean(axis=0).tolist()

        # Use hint if provided, otherwise default approach
        if constraints.approach_direction_hint:
            approach = list(constraints.approach_direction_hint)
        else:
            approach = [0.0, 0.0, -1.0]

        candidate = GraspCandidate(
            grasp_id=str(uuid.uuid4()),
            grasp_pose=SE3(
                position=centroid,
                quaternion=[0.0, 0.0, 0.0, 1.0],
            ),
            approach_direction=approach,
            gripper_width=0.05,
            grasp_score=0.8,
            collision_score=1.0,
        )
        return [candidate]

    def get_backend_name(self) -> str:
        """Return backend name."""
        return "mock"
