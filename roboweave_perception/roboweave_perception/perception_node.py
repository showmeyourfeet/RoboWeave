"""PerceptionNode - Main entry point for roboweave_perception.

If ROS2 (rclpy) is available, runs as a ROS2 node.
Otherwise, provides the class structure for standalone use.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .backend_registry import get_backend, list_backends
from .detector import Detector
from .segmentor import Segmentor
from .point_cloud_builder import PointCloudBuilder
from .pose_estimator import PoseEstimator
from .pose_tracker import PoseTracker

logger = logging.getLogger(__name__)

# Try importing ROS2
try:
    import rclpy
    from rclpy.node import Node

    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False
    Node = object  # type: ignore[assignment,misc]


class PerceptionNode(Node):  # type: ignore[misc]
    """Main perception node hosting services and action server."""

    # Default parameters
    DEFAULT_CONFIDENCE_THRESHOLD = 0.5
    DEFAULT_TRACKING_FREQUENCY_HZ = 10.0
    DEFAULT_MAX_MISSED_FRAMES = 5
    DEFAULT_MIN_POSE_CONFIDENCE = 0.1

    def __init__(
        self,
        perception_params_path: str = "",
        model_registry_path: str = "",
        **kwargs: Any,
    ) -> None:
        if HAS_ROS2:
            super().__init__("perception_node", **kwargs)
            self.declare_parameter("perception_params_path", perception_params_path)
            self.declare_parameter("model_registry_path", model_registry_path)
            perception_params_path = (
                self.get_parameter("perception_params_path").value
            )
            model_registry_path = (
                self.get_parameter("model_registry_path").value
            )

        # Load perception params
        self._confidence_threshold = self.DEFAULT_CONFIDENCE_THRESHOLD
        self._tracking_frequency_hz = self.DEFAULT_TRACKING_FREQUENCY_HZ
        self._max_missed_frames = self.DEFAULT_MAX_MISSED_FRAMES
        self._min_pose_confidence = self.DEFAULT_MIN_POSE_CONFIDENCE

        if perception_params_path:
            self._load_perception_params(perception_params_path)

        # Load model registry and instantiate backends
        self._detector: Detector | None = None
        self._segmentor: Segmentor | None = None
        self._point_cloud_builder: PointCloudBuilder | None = None
        self._pose_estimator: PoseEstimator | None = None

        # Import backends to trigger registration
        import roboweave_perception.backends  # noqa: F401

        if model_registry_path:
            self._load_backends(model_registry_path)
        else:
            self._load_default_backends()

        # Create pose tracker
        self._pose_tracker: PoseTracker | None = None
        if (
            self._detector
            and self._segmentor
            and self._point_cloud_builder
            and self._pose_estimator
        ):
            self._pose_tracker = PoseTracker(
                detector=self._detector,
                segmentor=self._segmentor,
                point_cloud_builder=self._point_cloud_builder,
                pose_estimator=self._pose_estimator,
                max_missed_frames=self._max_missed_frames,
            )

        # Set up ROS2 services (if available)
        if HAS_ROS2:
            self._setup_services()

        logger.info("PerceptionNode started successfully.")

    def _load_perception_params(self, path: str) -> None:
        """Load perception parameters from YAML."""
        p = Path(path)
        if not p.exists():
            logger.error(f"Perception params not found: {path}")
            return

        with open(p) as f:
            data = yaml.safe_load(f)

        params = data.get("perception", {})
        self._confidence_threshold = params.get(
            "default_confidence_threshold", self.DEFAULT_CONFIDENCE_THRESHOLD
        )
        self._tracking_frequency_hz = params.get(
            "default_tracking_frequency_hz", self.DEFAULT_TRACKING_FREQUENCY_HZ
        )
        self._max_missed_frames = params.get(
            "max_missed_frames", self.DEFAULT_MAX_MISSED_FRAMES
        )
        self._min_pose_confidence = params.get(
            "min_pose_confidence", self.DEFAULT_MIN_POSE_CONFIDENCE
        )

    def _load_backends(self, path: str) -> None:
        """Load backends from model registry YAML."""
        p = Path(path)
        if not p.exists():
            logger.error(f"Model registry not found: {path}")
            self._load_default_backends()
            return

        with open(p) as f:
            data = yaml.safe_load(f)

        backends_cfg = data.get("backends", {})
        self._detector = self._get_backend_safe(
            "detector", backends_cfg.get("detector", {}).get("active", "mock")
        )
        self._segmentor = self._get_backend_safe(
            "segmentor", backends_cfg.get("segmentor", {}).get("active", "mock")
        )
        self._point_cloud_builder = self._get_backend_safe(
            "point_cloud_builder",
            backends_cfg.get("point_cloud_builder", {}).get("active", "simple"),
        )
        self._pose_estimator = self._get_backend_safe(
            "pose_estimator",
            backends_cfg.get("pose_estimator", {}).get("active", "mock"),
        )

    def _load_default_backends(self) -> None:
        """Load default mock/simple backends."""
        self._detector = self._get_backend_safe("detector", "mock")
        self._segmentor = self._get_backend_safe("segmentor", "mock")
        self._point_cloud_builder = self._get_backend_safe(
            "point_cloud_builder", "simple"
        )
        self._pose_estimator = self._get_backend_safe("pose_estimator", "mock")

    def _get_backend_safe(self, capability: str, name: str):
        """Get a backend, falling back to mock/simple on error."""
        try:
            backend = get_backend(capability, name)
            logger.info(f"Loaded {capability} backend: {name}")
            return backend
        except KeyError:
            logger.error(
                f"Backend '{name}' not found for '{capability}', "
                f"falling back to default"
            )
            fallback = "simple" if capability == "point_cloud_builder" else "mock"
            try:
                return get_backend(capability, fallback)
            except KeyError:
                logger.error(f"Fallback backend also not found for '{capability}'")
                return None

    def _setup_services(self) -> None:
        """Set up ROS2 service and action servers."""
        # TODO: Create service servers for detect_objects, segment_object,
        # build_point_cloud, estimate_pose on /roboweave/perception/ namespace
        # TODO: Create action server for track_pose
        pass

    def _handle_detect_objects(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle DetectObjects service request."""
        try:
            import numpy as np
            from .converters import detection_result_to_msg

            # Resolve RGB from request (simplified for non-ROS2 testing)
            rgb = request.get("rgb")
            query = request.get("query", "")
            threshold = request.get(
                "confidence_threshold", self._confidence_threshold
            )

            if rgb is None:
                return {
                    "success": False,
                    "error_code": "PER_DETECTION_FAILED",
                    "error_message": "Cannot resolve rgb_ref",
                }

            results = self._detector.detect(rgb, query, threshold)
            return {
                "success": True,
                "detections": [detection_result_to_msg(r) for r in results],
            }
        except Exception as e:
            return {
                "success": False,
                "error_code": "PER_DETECTION_FAILED",
                "error_message": str(e),
            }

    def _handle_segment_object(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle SegmentObject service request."""
        try:
            from .converters import segmentation_result_to_msg

            rgb = request.get("rgb")
            object_id = request.get("object_id", "")
            bbox_hint = request.get("bbox_hint")

            if rgb is None:
                return {
                    "success": False,
                    "error_code": "PER_SEGMENTATION_FAILED",
                    "error_message": "Cannot resolve rgb image",
                }

            result = self._segmentor.segment(rgb, object_id, bbox_hint)
            return {
                "success": True,
                "segmentation": segmentation_result_to_msg(result),
            }
        except Exception as e:
            return {
                "success": False,
                "error_code": "PER_SEGMENTATION_FAILED",
                "error_message": str(e),
            }

    def _handle_build_point_cloud(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle BuildPointCloud service request."""
        try:
            from .converters import point_cloud_result_to_msg

            depth = request.get("depth")
            mask = request.get("mask")
            intrinsics = request.get("intrinsics")
            object_id = request.get("object_id", "")

            if depth is None or mask is None or intrinsics is None:
                return {
                    "success": False,
                    "error_code": "PER_POINT_CLOUD_FAILED",
                    "error_message": "Missing depth, mask, or intrinsics",
                }

            result = self._point_cloud_builder.build(
                depth, mask, tuple(intrinsics), object_id
            )

            if result.num_points == 0:
                return {
                    "success": False,
                    "error_code": "PER_POINT_CLOUD_EMPTY",
                    "error_message": "No valid points in point cloud",
                }

            return {
                "success": True,
                "point_cloud": point_cloud_result_to_msg(result),
            }
        except Exception as e:
            return {
                "success": False,
                "error_code": "PER_POINT_CLOUD_FAILED",
                "error_message": str(e),
            }

    def _handle_estimate_pose(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle EstimatePose service request."""
        try:
            from .converters import pose_estimation_result_to_msg
            from roboweave_interfaces.perception import PointCloudResult

            point_cloud = request.get("point_cloud")
            object_id = request.get("object_id", "")
            method = request.get("method", "default")

            if point_cloud is None:
                return {
                    "success": False,
                    "error_code": "PER_POSE_ESTIMATION_FAILED",
                    "error_message": "Missing point cloud",
                }

            # Accept PointCloudResult directly or convert from dict
            if not isinstance(point_cloud, PointCloudResult):
                from .converters import msg_to_point_cloud_result
                point_cloud = msg_to_point_cloud_result(point_cloud)

            result = self._pose_estimator.estimate(point_cloud, object_id, method)

            if result.confidence < self._min_pose_confidence:
                return {
                    "success": False,
                    "error_code": "PER_POSE_ESTIMATION_FAILED",
                    "error_message": (
                        f"Confidence {result.confidence} below threshold "
                        f"{self._min_pose_confidence}"
                    ),
                }

            return {
                "success": True,
                "pose_estimation": pose_estimation_result_to_msg(result),
            }
        except Exception as e:
            return {
                "success": False,
                "error_code": "PER_POSE_ESTIMATION_FAILED",
                "error_message": str(e),
            }

    def shutdown(self) -> None:
        """Release backend resources."""
        logger.info("PerceptionNode shutting down.")


def main() -> None:
    """Entry point for the perception node."""
    if HAS_ROS2:
        rclpy.init()
        node = PerceptionNode()
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            node.shutdown()
            node.destroy_node()
            rclpy.shutdown()
    else:
        logger.warning(
            "ROS2 not available. PerceptionNode requires rclpy to run."
        )


if __name__ == "__main__":
    main()
