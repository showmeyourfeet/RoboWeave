"""SimplePointCloudBuilder - Pinhole projection point cloud backend."""

from __future__ import annotations

import numpy as np

from roboweave_interfaces.perception import PointCloudResult
from roboweave_interfaces.world_state import SE3, BoundingBox3D
from ..backend_registry import register_backend
from ..point_cloud_builder import PointCloudBuilder


@register_backend("point_cloud_builder", "simple")
class SimplePointCloudBuilder(PointCloudBuilder):
    """Point cloud builder using standard pinhole camera model."""

    def build(
        self,
        depth: np.ndarray,
        mask: np.ndarray,
        intrinsics: tuple[float, float, float, float],
        object_id: str,
    ) -> PointCloudResult:
        """Build 3D point cloud from masked depth using pinhole projection."""
        if depth.shape[:2] != mask.shape[:2]:
            raise ValueError(
                f"Depth shape {depth.shape[:2]} does not match "
                f"mask shape {mask.shape[:2]}"
            )

        fx, fy, cx, cy = intrinsics

        # Find masked pixels with valid depth
        valid = (mask > 0) & (depth > 0)
        vs, us = np.where(valid)

        if len(vs) == 0:
            return PointCloudResult(
                object_id=object_id,
                num_points=0,
                center_pose=None,
                bbox_3d=None,
            )

        # Pinhole projection
        d = depth[vs, us].astype(np.float64)
        z = d
        x = (us.astype(np.float64) - cx) * z / fx
        y = (vs.astype(np.float64) - cy) * z / fy

        # Centroid
        cx_pt = float(np.mean(x))
        cy_pt = float(np.mean(y))
        cz_pt = float(np.mean(z))

        # Axis-aligned bounding box extent
        size_x = float(np.max(x) - np.min(x))
        size_y = float(np.max(y) - np.min(y))
        size_z = float(np.max(z) - np.min(z))

        center_pose = SE3(
            position=[cx_pt, cy_pt, cz_pt],
            quaternion=[0.0, 0.0, 0.0, 1.0],
        )
        bbox_3d = BoundingBox3D(
            center=center_pose,
            size=[size_x, size_y, size_z],
        )

        return PointCloudResult(
            object_id=object_id,
            num_points=int(len(vs)),
            center_pose=center_pose,
            bbox_3d=bbox_3d,
            point_cloud_uri=f"mem://{object_id}/points",
        )

    def get_backend_name(self) -> str:
        return "simple"
