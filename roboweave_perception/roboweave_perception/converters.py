"""Pure functions for Pydantic ↔ ROS2 message conversion.

Since ROS2 may not be available, converters work with dict representations
of messages when ROS2 imports fail. Follows the same pattern as
roboweave_control/converters.py.
"""

from __future__ import annotations

from typing import Any

from roboweave_interfaces.perception import (
    DetectionResult,
    PointCloudResult,
    PoseEstimationResult,
    SegmentationResult,
)
from roboweave_interfaces.refs import (
    DepthRef,
    ImageRef,
    MaskRef,
    PointCloudRef,
)
from roboweave_interfaces.world_state import SE3, BoundingBox3D

# Try importing ROS2 message types; fall back to dict-based approach
try:
    from roboweave_msgs.msg import (
        Detection as DetectionMsg,
        BoundingBox3D as BoundingBox3DMsg,
    )
    from geometry_msgs.msg import Pose, Point, Quaternion

    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False


# --- SE3 ↔ Pose conversion (reuse pattern from control) ---


def se3_to_pose_dict(se3: SE3) -> dict[str, Any]:
    """Convert SE3 to a dict representing geometry_msgs/Pose."""
    return {
        "position": {
            "x": se3.position[0],
            "y": se3.position[1],
            "z": se3.position[2],
        },
        "orientation": {
            "x": se3.quaternion[0],
            "y": se3.quaternion[1],
            "z": se3.quaternion[2],
            "w": se3.quaternion[3],
        },
    }


def pose_dict_to_se3(pose: dict[str, Any]) -> SE3:
    """Convert a dict representing geometry_msgs/Pose to SE3."""
    pos = pose.get("position", {})
    ori = pose.get("orientation", {})
    return SE3(
        position=[pos.get("x", 0.0), pos.get("y", 0.0), pos.get("z", 0.0)],
        quaternion=[
            ori.get("x", 0.0),
            ori.get("y", 0.0),
            ori.get("z", 0.0),
            ori.get("w", 1.0),
        ],
    )


# --- BoundingBox3D conversion ---


def bbox3d_to_msg(bbox: BoundingBox3D) -> dict[str, Any]:
    """Convert BoundingBox3D to a msg dict."""
    return {
        "center": se3_to_pose_dict(bbox.center),
        "size": list(bbox.size),
    }


def msg_to_bbox3d(msg: dict[str, Any]) -> BoundingBox3D:
    """Convert a msg dict to BoundingBox3D."""
    center = pose_dict_to_se3(msg.get("center", {}))
    size = msg.get("size", [0.0, 0.0, 0.0])
    return BoundingBox3D(center=center, size=size)


# --- DetectionResult conversion ---


def detection_result_to_msg(det: DetectionResult) -> dict[str, Any]:
    """Convert DetectionResult to a msg dict."""
    msg: dict[str, Any] = {
        "object_id": det.object_id,
        "category": det.category,
        "matched_query": det.matched_query,
        "bbox_2d": list(det.bbox_2d),
        "confidence": det.confidence,
    }
    if det.pose_camera is not None:
        msg["pose_camera"] = se3_to_pose_dict(det.pose_camera)
    else:
        msg["pose_camera"] = None
    return msg


def msg_to_detection_result(msg: dict[str, Any]) -> DetectionResult:
    """Convert a msg dict to DetectionResult."""
    pose_camera = None
    if msg.get("pose_camera") is not None:
        pose_camera = pose_dict_to_se3(msg["pose_camera"])
    return DetectionResult(
        object_id=msg.get("object_id", ""),
        category=msg.get("category", ""),
        matched_query=msg.get("matched_query", ""),
        bbox_2d=msg.get("bbox_2d", []),
        confidence=msg.get("confidence", 0.0),
        pose_camera=pose_camera,
    )


# --- SegmentationResult conversion ---


def segmentation_result_to_msg(seg: SegmentationResult) -> dict[str, Any]:
    """Convert SegmentationResult to a msg dict."""
    return {
        "mask_id": seg.mask_id,
        "object_id": seg.object_id,
        "mask_confidence": seg.mask_confidence,
        "pixel_count": seg.pixel_count,
        "mask_uri": seg.mask_uri,
    }


def msg_to_segmentation_result(msg: dict[str, Any]) -> SegmentationResult:
    """Convert a msg dict to SegmentationResult."""
    return SegmentationResult(
        mask_id=msg.get("mask_id", ""),
        object_id=msg.get("object_id", ""),
        mask_confidence=msg.get("mask_confidence", 0.0),
        pixel_count=msg.get("pixel_count", 0),
        mask_uri=msg.get("mask_uri", ""),
    )


# --- PointCloudResult conversion ---


def point_cloud_result_to_msg(pcr: PointCloudResult) -> dict[str, Any]:
    """Convert PointCloudResult to a msg dict."""
    msg: dict[str, Any] = {
        "object_id": pcr.object_id,
        "point_cloud_uri": pcr.point_cloud_uri,
        "num_points": pcr.num_points,
        "surface_normals_available": pcr.surface_normals_available,
    }
    if pcr.center_pose is not None:
        msg["center_pose"] = se3_to_pose_dict(pcr.center_pose)
    else:
        msg["center_pose"] = None
    if pcr.bbox_3d is not None:
        msg["bbox_3d"] = bbox3d_to_msg(pcr.bbox_3d)
    else:
        msg["bbox_3d"] = None
    return msg


def msg_to_point_cloud_result(msg: dict[str, Any]) -> PointCloudResult:
    """Convert a msg dict to PointCloudResult."""
    center_pose = None
    if msg.get("center_pose") is not None:
        center_pose = pose_dict_to_se3(msg["center_pose"])
    bbox_3d = None
    if msg.get("bbox_3d") is not None:
        bbox_3d = msg_to_bbox3d(msg["bbox_3d"])
    return PointCloudResult(
        object_id=msg.get("object_id", ""),
        point_cloud_uri=msg.get("point_cloud_uri", ""),
        num_points=msg.get("num_points", 0),
        surface_normals_available=msg.get("surface_normals_available", False),
        center_pose=center_pose,
        bbox_3d=bbox_3d,
    )


# --- PoseEstimationResult conversion ---


def pose_estimation_result_to_msg(per: PoseEstimationResult) -> dict[str, Any]:
    """Convert PoseEstimationResult to a msg dict."""
    return {
        "object_id": per.object_id,
        "pose": se3_to_pose_dict(per.pose),
        "confidence": per.confidence,
        "covariance": list(per.covariance),
        "frame_id": per.frame_id,
    }


def msg_to_pose_estimation_result(msg: dict[str, Any]) -> PoseEstimationResult:
    """Convert a msg dict to PoseEstimationResult."""
    pose = pose_dict_to_se3(msg.get("pose", {}))
    return PoseEstimationResult(
        object_id=msg.get("object_id", ""),
        pose=pose,
        confidence=msg.get("confidence", 0.0),
        covariance=msg.get("covariance", []),
        frame_id=msg.get("frame_id", "base_link"),
    )


# --- ImageRef conversion ---


def image_ref_to_msg(ref: ImageRef) -> dict[str, Any]:
    """Convert ImageRef to a msg dict."""
    return {
        "uri": ref.uri,
        "timestamp": ref.timestamp,
        "frame_id": ref.frame_id,
        "encoding": ref.encoding,
        "width": ref.width,
        "height": ref.height,
    }


def msg_to_image_ref(msg: dict[str, Any]) -> ImageRef:
    """Convert a msg dict to ImageRef."""
    return ImageRef(
        uri=msg.get("uri", ""),
        timestamp=msg.get("timestamp", 0.0),
        frame_id=msg.get("frame_id", ""),
        encoding=msg.get("encoding", "rgb8"),
        width=msg.get("width", 0),
        height=msg.get("height", 0),
    )


# --- DepthRef conversion ---


def depth_ref_to_msg(ref: DepthRef) -> dict[str, Any]:
    """Convert DepthRef to a msg dict."""
    return {
        "uri": ref.uri,
        "timestamp": ref.timestamp,
        "frame_id": ref.frame_id,
        "encoding": ref.encoding,
        "width": ref.width,
        "height": ref.height,
        "depth_unit": ref.depth_unit,
    }


def msg_to_depth_ref(msg: dict[str, Any]) -> DepthRef:
    """Convert a msg dict to DepthRef."""
    return DepthRef(
        uri=msg.get("uri", ""),
        timestamp=msg.get("timestamp", 0.0),
        frame_id=msg.get("frame_id", ""),
        encoding=msg.get("encoding", "16UC1"),
        width=msg.get("width", 0),
        height=msg.get("height", 0),
        depth_unit=msg.get("depth_unit", "mm"),
    )


# --- MaskRef conversion ---


def mask_ref_to_msg(ref: MaskRef) -> dict[str, Any]:
    """Convert MaskRef to a msg dict."""
    return {
        "uri": ref.uri,
        "timestamp": ref.timestamp,
        "frame_id": ref.frame_id,
        "object_id": ref.object_id,
        "mask_confidence": ref.mask_confidence,
        "pixel_count": ref.pixel_count,
    }


def msg_to_mask_ref(msg: dict[str, Any]) -> MaskRef:
    """Convert a msg dict to MaskRef."""
    return MaskRef(
        uri=msg.get("uri", ""),
        timestamp=msg.get("timestamp", 0.0),
        frame_id=msg.get("frame_id", ""),
        object_id=msg.get("object_id", ""),
        mask_confidence=msg.get("mask_confidence", 0.0),
        pixel_count=msg.get("pixel_count", 0),
    )


# --- PointCloudRef conversion ---


def point_cloud_ref_to_msg(ref: PointCloudRef) -> dict[str, Any]:
    """Convert PointCloudRef to a msg dict."""
    return {
        "uri": ref.uri,
        "timestamp": ref.timestamp,
        "frame_id": ref.frame_id,
        "num_points": ref.num_points,
        "has_color": ref.has_color,
        "has_normals": ref.has_normals,
        "format": ref.format,
    }


def msg_to_point_cloud_ref(msg: dict[str, Any]) -> PointCloudRef:
    """Convert a msg dict to PointCloudRef."""
    return PointCloudRef(
        uri=msg.get("uri", ""),
        timestamp=msg.get("timestamp", 0.0),
        frame_id=msg.get("frame_id", ""),
        num_points=msg.get("num_points", 0),
        has_color=msg.get("has_color", False),
        has_normals=msg.get("has_normals", False),
        format=msg.get("format", "ply"),
    )
