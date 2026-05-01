from __future__ import annotations

from .base import VersionedModel


class DataRef(VersionedModel):
    """Lightweight reference to large binary data stored elsewhere."""

    uri: str
    timestamp: float = 0.0
    frame_id: str = ""
    valid_until: float = 0.0
    source_module: str = ""


class ImageRef(DataRef):
    """Reference to an image stored at uri."""

    encoding: str = "rgb8"
    width: int = 0
    height: int = 0


class DepthRef(DataRef):
    """Reference to a depth image stored at uri."""

    encoding: str = "16UC1"
    width: int = 0
    height: int = 0
    depth_unit: str = "mm"


class PointCloudRef(DataRef):
    """Reference to a point cloud stored at uri."""

    num_points: int = 0
    has_color: bool = False
    has_normals: bool = False
    format: str = "ply"


class MaskRef(DataRef):
    """Reference to a segmentation mask stored at uri."""

    object_id: str = ""
    mask_confidence: float = 0.0
    pixel_count: int = 0


class TrajectoryRef(DataRef):
    """Reference to a trajectory stored at uri."""

    num_points: int = 0
    duration_sec: float = 0.0
    arm_id: str = ""


class WorldStateRef(DataRef):
    """Reference to a world state snapshot stored at uri."""

    num_objects: int = 0
    robot_id: str = ""
