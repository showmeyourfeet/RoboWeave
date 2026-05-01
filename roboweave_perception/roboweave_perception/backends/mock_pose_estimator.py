"""MockPoseEstimator - A mock pose estimation backend for testing."""

from __future__ import annotations

from roboweave_interfaces.perception import PointCloudResult, PoseEstimationResult
from roboweave_interfaces.world_state import SE3
from ..backend_registry import register_backend
from ..pose_estimator import PoseEstimator


@register_backend("pose_estimator", "mock")
class MockPoseEstimator(PoseEstimator):
    """Mock pose estimator that passes through center_pose."""

    def estimate(
        self,
        point_cloud: PointCloudResult,
        object_id: str,
        method: str = "default",
    ) -> PoseEstimationResult:
        """Return center_pose as the estimated pose."""
        if point_cloud.num_points == 0 or point_cloud.center_pose is None:
            return PoseEstimationResult(
                object_id=object_id,
                pose=SE3(),
                confidence=0.0,
                covariance=[0.0] * 36,
                frame_id="base_link",
            )

        # Identity covariance: 1.0 on diagonal of 6x6 matrix
        covariance = [0.0] * 36
        for i in range(6):
            covariance[i * 6 + i] = 1.0

        return PoseEstimationResult(
            object_id=object_id,
            pose=point_cloud.center_pose,
            confidence=1.0,
            covariance=covariance,
            frame_id="base_link",
        )

    def get_backend_name(self) -> str:
        return "mock"
