"""Detector ABC for object detection backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from roboweave_interfaces.perception import DetectionResult


class Detector(ABC):
    """Abstract interface for object detection backends."""

    @abstractmethod
    def detect(
        self,
        rgb: np.ndarray,
        query: str,
        confidence_threshold: float = 0.5,
    ) -> list[DetectionResult]:
        """Detect objects matching the query in the RGB image.

        Args:
            rgb: HxWx3 uint8 numpy array (RGB).
            query: Open-vocabulary text query.
            confidence_threshold: Minimum confidence to include.

        Returns:
            List of DetectionResult models.

        Raises:
            ValueError: If rgb is empty or query is empty.
        """
        ...

    @abstractmethod
    def get_backend_name(self) -> str:
        """Return the name of this backend."""
        ...
