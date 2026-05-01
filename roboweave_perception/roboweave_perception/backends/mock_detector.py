"""MockDetector - A mock object detection backend for testing."""

from __future__ import annotations

import numpy as np

from roboweave_interfaces.perception import DetectionResult
from ..backend_registry import register_backend
from ..detector import Detector


@register_backend("detector", "mock")
class MockDetector(Detector):
    """Mock detector that returns a single synthetic detection."""

    def detect(
        self,
        rgb: np.ndarray,
        query: str,
        confidence_threshold: float = 0.5,
    ) -> list[DetectionResult]:
        """Return a single detection with a centered bounding box."""
        if rgb.size == 0:
            raise ValueError("RGB image is empty")
        if not query or not query.strip():
            raise ValueError("Query string is empty")

        h, w = rgb.shape[:2]
        # Centered bounding box covering ~25% of image
        x_min = w // 4
        y_min = h // 4
        x_max = 3 * w // 4
        y_max = 3 * h // 4

        category = query.strip().split()[0]

        return [
            DetectionResult(
                object_id=f"{category}_001",
                category=category,
                matched_query=query,
                bbox_2d=[x_min, y_min, x_max, y_max],
                confidence=1.0,
            )
        ]

    def get_backend_name(self) -> str:
        return "mock"
