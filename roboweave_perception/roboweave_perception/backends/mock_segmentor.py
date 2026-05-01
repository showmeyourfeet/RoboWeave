"""MockSegmentor - A mock segmentation backend for testing."""

from __future__ import annotations

import numpy as np

from roboweave_interfaces.perception import SegmentationResult
from ..backend_registry import register_backend
from ..segmentor import Segmentor


@register_backend("segmentor", "mock")
class MockSegmentor(Segmentor):
    """Mock segmentor that returns a synthetic mask."""

    def segment(
        self,
        rgb: np.ndarray,
        object_id: str,
        bbox_hint: list[int] | None = None,
    ) -> SegmentationResult:
        """Return a segmentation result with synthetic mask area."""
        if rgb.size == 0:
            raise ValueError("RGB image is empty")

        h, w = rgb.shape[:2]

        if bbox_hint is not None:
            x_min, y_min, x_max, y_max = bbox_hint
            pixel_count = (x_max - x_min) * (y_max - y_min)
        else:
            # 25% of image area
            pixel_count = (h * w) // 4

        return SegmentationResult(
            mask_id=f"mask_{object_id}",
            object_id=object_id,
            mask_confidence=1.0,
            pixel_count=pixel_count,
            mask_uri=f"mem://{object_id}/mask",
        )

    def get_backend_name(self) -> str:
        return "mock"
