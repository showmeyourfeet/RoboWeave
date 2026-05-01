"""PointCloudBuilder ABC for RGBD-to-point-cloud construction."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from roboweave_interfaces.perception import PointCloudResult


class PointCloudBuilder(ABC):
    """Abstract interface for RGBD-to-point-cloud construction."""

    @abstractmethod
    def build(
        self,
        depth: np.ndarray,
        mask: np.ndarray,
        intrinsics: tuple[float, float, float, float],
        object_id: str,
    ) -> PointCloudResult:
        """Build a 3D point cloud from masked depth data.

        Args:
            depth: HxW float/uint16 numpy array (depth image).
            mask: HxW binary numpy array (1 = foreground).
            intrinsics: Camera intrinsics (fx, fy, cx, cy).
            object_id: ID of the object.

        Returns:
            PointCloudResult model.

        Raises:
            ValueError: If depth and mask have different dimensions.
        """
        ...

    @abstractmethod
    def get_backend_name(self) -> str:
        """Return the name of this backend."""
        ...
