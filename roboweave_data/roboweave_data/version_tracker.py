"""VersionTracker - Captures system version snapshots."""

from __future__ import annotations

import time
from typing import Any

from roboweave_interfaces._version import SCHEMA_VERSION
from roboweave_interfaces.episode import SystemVersions


class VersionTracker:
    """Captures system version snapshots."""

    def __init__(self, node: Any = None) -> None:
        """node: optional ROS2 node for parameter queries."""
        self._node = node
        self._latest_snapshot: SystemVersions | None = None

    def capture_snapshot(self) -> SystemVersions:
        """Capture a fresh SystemVersions snapshot.
        Populates roboweave_version from _version module.
        Queries ROS2 parameters if node is available.
        Sets unavailable fields to empty string."""
        snapshot = SystemVersions(
            timestamp=time.time(),
            roboweave_version=SCHEMA_VERSION,
        )

        # Best-effort ROS2 parameter queries
        if self._node is not None:
            snapshot = self._query_ros2_params(snapshot)

        self._latest_snapshot = snapshot
        return snapshot

    def _query_ros2_params(self, snapshot: SystemVersions) -> SystemVersions:
        """Query ROS2 parameters for version info. Best-effort."""
        try:
            # These would query other nodes' parameters in a real ROS2 system
            pass
        except Exception:
            pass
        return snapshot

    @property
    def latest_snapshot(self) -> SystemVersions | None:
        return self._latest_snapshot
