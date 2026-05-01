"""PoseTracker - Continuous pose tracking with lost detection."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from roboweave_interfaces.perception import PoseEstimationResult
from roboweave_interfaces.world_state import SE3

from .detector import Detector
from .segmentor import Segmentor
from .point_cloud_builder import PointCloudBuilder
from .pose_estimator import PoseEstimator


@dataclass
class TrackingFeedback:
    """Feedback published during tracking."""

    current_pose: SE3 | None = None
    confidence: float = 0.0
    tracking_age_sec: float = 0.0


@dataclass
class TrackingResult:
    """Final result of a tracking session."""

    final_status: str = "completed"
    error_code: str = ""
    last_pose: SE3 | None = None


class PoseTracker:
    """Manages continuous pose tracking via the full perception pipeline."""

    def __init__(
        self,
        detector: Detector,
        segmentor: Segmentor,
        point_cloud_builder: PointCloudBuilder,
        pose_estimator: PoseEstimator,
        max_missed_frames: int = 5,
    ) -> None:
        self._detector = detector
        self._segmentor = segmentor
        self._pcb = point_cloud_builder
        self._pe = pose_estimator
        self._max_missed_frames = max_missed_frames

        self._running = False
        self._cancelled = False
        self._consecutive_misses = 0
        self._last_pose: SE3 | None = None

    @property
    def consecutive_misses(self) -> int:
        return self._consecutive_misses

    def start_tracking(
        self,
        object_id: str,
        get_rgb: Callable[[], np.ndarray],
        get_depth: Callable[[], np.ndarray],
        intrinsics: tuple[float, float, float, float],
        tracking_frequency_hz: float = 10.0,
        feedback_callback: Callable[[TrackingFeedback], None] | None = None,
    ) -> TrackingResult:
        """Run the tracking loop synchronously.

        Args:
            object_id: ID of the object to track.
            get_rgb: Callable returning current RGB frame.
            get_depth: Callable returning current depth frame.
            intrinsics: Camera intrinsics (fx, fy, cx, cy).
            tracking_frequency_hz: Loop rate in Hz.
            feedback_callback: Optional callback for feedback.

        Returns:
            TrackingResult with final_status.
        """
        self._running = True
        self._cancelled = False
        self._consecutive_misses = 0
        start_time = time.time()
        period = 1.0 / tracking_frequency_hz

        while self._running:
            if self._cancelled:
                return TrackingResult(
                    final_status="cancelled",
                    last_pose=self._last_pose,
                )

            frame_start = time.time()

            # Run pipeline
            success = self._run_pipeline_step(
                object_id, get_rgb, get_depth, intrinsics
            )

            if not success:
                self._consecutive_misses += 1
                if self._consecutive_misses >= self._max_missed_frames:
                    self._running = False
                    return TrackingResult(
                        final_status="lost",
                        error_code="PER_TRACKING_LOST",
                        last_pose=self._last_pose,
                    )
            else:
                self._consecutive_misses = 0

            # Publish feedback
            if feedback_callback:
                age = time.time() - start_time
                feedback = TrackingFeedback(
                    current_pose=self._last_pose,
                    confidence=1.0 if success else 0.0,
                    tracking_age_sec=age,
                )
                feedback_callback(feedback)

            # Rate limiting
            elapsed = time.time() - frame_start
            sleep_time = period - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        # If we exited the loop due to cancel
        if self._cancelled:
            return TrackingResult(
                final_status="cancelled",
                last_pose=self._last_pose,
            )

        return TrackingResult(
            final_status="completed",
            last_pose=self._last_pose,
        )

    def _run_pipeline_step(
        self,
        object_id: str,
        get_rgb: Callable[[], np.ndarray],
        get_depth: Callable[[], np.ndarray],
        intrinsics: tuple[float, float, float, float],
    ) -> bool:
        """Run one detect→segment→build→estimate cycle. Returns True on success."""
        try:
            rgb = get_rgb()
            detections = self._detector.detect(rgb, object_id)
            if not detections:
                return False

            det = detections[0]
            seg_result = self._segmentor.segment(rgb, object_id, det.bbox_2d)

            depth = get_depth()
            mask = np.zeros(depth.shape[:2], dtype=np.uint8)
            # Use bbox from detection as mask region
            if det.bbox_2d and len(det.bbox_2d) == 4:
                x_min, y_min, x_max, y_max = det.bbox_2d
                mask[y_min:y_max, x_min:x_max] = 1

            pc_result = self._pcb.build(depth, mask, intrinsics, object_id)
            if pc_result.num_points == 0:
                return False

            pose_result = self._pe.estimate(pc_result, object_id)
            if pose_result.confidence > 0:
                self._last_pose = pose_result.pose
                return True
            return False
        except Exception:
            return False

    def cancel(self) -> None:
        """Request cancellation of the tracking loop."""
        self._cancelled = True
        self._running = False

    def stop(self) -> None:
        """Stop the tracking loop normally."""
        self._running = False
