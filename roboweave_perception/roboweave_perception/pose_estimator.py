"""PoseEstimator ABC for 6-DOF pose estimation backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

from roboweave_interfaces.perception import PointCloudResult, PoseEstimationResult


class PoseEstimator(ABC):
    """Abstract interface for 6-DOF pose estimation."""

    @abstractmethod
    def estimate(
        self,
        point_cloud: PointCloudResult,
        object_id: str,
        method: str = "default",
    ) -> PoseEstimationResult:
        """Estimate the 6-DOF pose of an object from its point cloud.

        Args:
            point_cloud: PointCloudResult from the builder.
            object_id: ID of the object.
            method: Estimation method string.

        Returns:
            PoseEstimationResult model.
        """
        ...

    @abstractmethod
    def get_backend_name(self) -> str:
        """Return the name of this backend."""
        ...
