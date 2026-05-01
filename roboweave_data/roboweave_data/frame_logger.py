"""FrameLogger - Rate-limited frame capture driven by external calls."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from roboweave_interfaces.episode import FrameLog
from roboweave_interfaces.refs import DataRef, DepthRef, ImageRef


class FrameLogger:
    """Captures FrameLog entries at a configurable rate."""

    def __init__(self, frame_rate_hz: float, episode_dir: Path) -> None:
        self._frame_rate_hz = frame_rate_hz
        self._min_interval = 1.0 / frame_rate_hz if frame_rate_hz > 0 else 0.0
        self._episode_dir = episode_dir
        self._last_capture_time: float | None = None
        self._frame_count: int = 0

    def maybe_capture(
        self,
        episode_id: str,
        timestamp: float,
        rgb_data: bytes | None = None,
        depth_data: bytes | None = None,
        robot_state_json: str | None = None,
        world_state_json: str | None = None,
        safety_status: dict | None = None,
    ) -> FrameLog | None:
        """Capture a frame if enough time has elapsed since the last capture.
        Writes binary data to frames/ directory. Returns FrameLog or None."""
        if self._last_capture_time is not None:
            elapsed = timestamp - self._last_capture_time
            if elapsed < self._min_interval:
                return None

        self._last_capture_time = timestamp
        frame_idx = self._frame_count
        self._frame_count += 1

        frames_dir = self._episode_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        rgb_ref = None
        depth_ref = None
        robot_state_ref = None
        world_state_ref = None

        # Write RGB data
        if rgb_data is not None:
            rgb_filename = f"{frame_idx:06d}_rgb.png"
            rgb_path = frames_dir / rgb_filename
            rgb_path.write_bytes(rgb_data)
            rgb_ref = ImageRef(
                uri=f"file://frames/{rgb_filename}",
                timestamp=timestamp,
                source_module="frame_logger",
            )

        # Write depth data
        if depth_data is not None:
            depth_filename = f"{frame_idx:06d}_depth.png"
            depth_path = frames_dir / depth_filename
            depth_path.write_bytes(depth_data)
            depth_ref = DepthRef(
                uri=f"file://frames/{depth_filename}",
                timestamp=timestamp,
                source_module="frame_logger",
            )

        # Write robot state JSON
        if robot_state_json is not None:
            rs_filename = f"{frame_idx:06d}_robot_state.json"
            rs_path = frames_dir / rs_filename
            rs_path.write_text(robot_state_json)
            robot_state_ref = DataRef(
                uri=f"file://frames/{rs_filename}",
                timestamp=timestamp,
                source_module="frame_logger",
            )

        # Write world state JSON
        if world_state_json is not None:
            ws_filename = f"{frame_idx:06d}_world_state.json"
            ws_path = frames_dir / ws_filename
            ws_path.write_text(world_state_json)
            world_state_ref = DataRef(
                uri=f"file://frames/{ws_filename}",
                timestamp=timestamp,
                source_module="frame_logger",
            )

        frame_log = FrameLog(
            timestamp=timestamp,
            episode_id=episode_id,
            rgb_ref=rgb_ref,
            depth_ref=depth_ref,
            robot_state_ref=robot_state_ref,
            world_state_ref=world_state_ref,
        )
        return frame_log

    def reset(self) -> None:
        """Reset the rate limiter (called on episode start/resume)."""
        self._last_capture_time = None
        self._frame_count = 0

    @property
    def frame_count(self) -> int:
        return self._frame_count
