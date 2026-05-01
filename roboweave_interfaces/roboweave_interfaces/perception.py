from __future__ import annotations

from pydantic import Field

from .base import TimestampedData
from .world_state import SE3, BoundingBox3D


class DetectionResult(TimestampedData):
    """Result of an object detection query."""

    object_id: str
    category: str
    matched_query: str
    bbox_2d: list[int] = Field(default_factory=list)
    confidence: float = 0.0
    pose_camera: SE3 | None = None


class SegmentationResult(TimestampedData):
    """Result of a segmentation operation."""

    mask_id: str
    object_id: str
    mask_confidence: float = 0.0
    pixel_count: int = 0
    mask_uri: str = ""


class PointCloudResult(TimestampedData):
    """Result of a point cloud extraction."""

    object_id: str
    point_cloud_uri: str = ""
    center_pose: SE3 | None = None
    bbox_3d: BoundingBox3D | None = None
    num_points: int = 0
    surface_normals_available: bool = False


class PoseEstimationResult(TimestampedData):
    """Result of a pose estimation."""

    object_id: str
    pose: SE3 = Field(default_factory=SE3)
    confidence: float = 0.0
    covariance: list[float] = Field(default_factory=list)
    frame_id: str = "base_link"
