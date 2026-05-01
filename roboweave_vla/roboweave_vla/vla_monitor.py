"""VLA execution monitor: confidence, rejection, step, and timeout tracking.

Pure Python — no ROS2 imports.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class MonitorStatus:
    """Result of a monitor check."""

    should_abort: bool = False
    abort_reason: str = ""  # "VLA_CONFIDENCE_LOW" | "VLA_SAFETY_REJECTED" | "VLA_TIMEOUT"
    should_finish: bool = False  # True when max_steps reached (success)


class VLAMonitor:
    """Tracks VLA execution health: confidence, rejections, steps, timeout.

    Pure Python — no ROS2 imports.
    """

    def __init__(
        self,
        max_steps: int = 0,
        timeout_sec: float = 60.0,
        consecutive_low_confidence_limit: int = 3,
        max_rejection_count: int = 5,
        min_confidence_threshold: float = 0.3,
    ) -> None:
        self._max_steps = max_steps
        self._timeout_sec = timeout_sec
        self._consecutive_low_confidence_limit = consecutive_low_confidence_limit
        self._max_rejection_count = max_rejection_count
        self._min_confidence_threshold = min_confidence_threshold

        self._steps: int = 0
        self._confidences: list[float] = []
        self._consecutive_low: int = 0
        self._rejections: int = 0
        self._start_time: float | None = None

    def start(self) -> None:
        """Record the start time."""
        self._start_time = time.monotonic()

    def record_step(self, confidence: float) -> None:
        """Record a prediction step's confidence."""
        self._steps += 1
        self._confidences.append(confidence)
        if confidence < self._min_confidence_threshold:
            self._consecutive_low += 1
        else:
            self._consecutive_low = 0

    def record_rejection(self) -> None:
        """Increment the safety rejection counter."""
        self._rejections += 1

    def check(self) -> MonitorStatus:
        """Check all limits. Returns status with abort reason if any."""
        # Check consecutive low confidence
        if self._consecutive_low >= self._consecutive_low_confidence_limit:
            return MonitorStatus(should_abort=True, abort_reason="VLA_CONFIDENCE_LOW")

        # Check rejection count
        if self._rejections > self._max_rejection_count:
            return MonitorStatus(should_abort=True, abort_reason="VLA_SAFETY_REJECTED")

        # Check timeout
        if self._start_time is not None and self._timeout_sec > 0:
            elapsed = time.monotonic() - self._start_time
            if elapsed > self._timeout_sec:
                return MonitorStatus(should_abort=True, abort_reason="VLA_TIMEOUT")

        # Check max steps (success condition)
        if self._max_steps > 0 and self._steps >= self._max_steps:
            return MonitorStatus(should_finish=True)

        return MonitorStatus()

    @property
    def steps_executed(self) -> int:
        return self._steps

    @property
    def mean_confidence(self) -> float:
        if not self._confidences:
            return 0.0
        return sum(self._confidences) / len(self._confidences)

    @property
    def consecutive_low_confidence_count(self) -> int:
        return self._consecutive_low

    @property
    def rejection_count(self) -> int:
        return self._rejections

    @property
    def elapsed_sec(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    def reset(self) -> None:
        """Reset all counters for a new execution."""
        self._steps = 0
        self._confidences = []
        self._consecutive_low = 0
        self._rejections = 0
        self._start_time = None
