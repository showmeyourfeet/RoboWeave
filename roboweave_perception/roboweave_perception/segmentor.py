"""Segmentor ABC for object segmentation backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from roboweave_interfaces.perception import SegmentationResult


class Segmentor(ABC):
    """Abstract interface for object segmentation backends."""

    @abstractmethod
    def segment(
        self,
        rgb: np.ndarray,
        object_id: str,
        bbox_hint: list[int] | None = None,
    ) -> SegmentationResult:
        """Segment the specified object from the RGB image.

        Args:
            rgb: HxWx3 uint8 numpy array (RGB).
            object_id: ID of the object to segment.
            bbox_hint: Optional [x_min, y_min, x_max, y_max] bounding box.

        Returns:
            SegmentationResult model.

        Raises:
            ValueError: If rgb is empty.
        """
        ...

    @abstractmethod
    def get_backend_name(self) -> str:
        """Return the name of this backend."""
        ...
