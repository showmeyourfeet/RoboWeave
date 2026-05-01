"""RuntimeNode — ROS2 adapter for the RoboWeave runtime.

Instantiates all pure-Python components and wires them to ROS2 interfaces.
Falls back to standalone mode if rclpy is not available.
"""

from __future__ import annotations

import logging
from typing import Any

from .cloud_bridge import CloudBridge
from .execution_monitor import ExecutionMonitor
from .hitl_manager import HITLManager
from .resource_manager import ResourceManager
from .skill_orchestrator import SkillOrchestrator
from .task_executor import TaskExecutor
from .world_model import WorldModel

logger = logging.getLogger(__name__)

try:
    import rclpy
    from rclpy.node import Node as RclpyNode

    _HAS_RCLPY = True
except ImportError:
    _HAS_RCLPY = False
    RclpyNode = object  # type: ignore[assignment,misc]


class RuntimeNode(RclpyNode):  # type: ignore[misc]
    """ROS2 node that wires all runtime components to ROS2 interfaces."""

    def __init__(self, **kwargs: Any) -> None:
        if _HAS_RCLPY:
            super().__init__("roboweave_runtime", **kwargs)
            publish_hz = self.declare_parameter("publish_hz", 1.0).value
            tick_hz = self.declare_parameter("tick_hz", 10.0).value
        else:
            publish_hz = kwargs.get("publish_hz", 1.0)
            tick_hz = kwargs.get("tick_hz", 10.0)

        # Instantiate pure-Python components
        self.world_model = WorldModel(publish_hz=publish_hz)
        self.resource_manager = ResourceManager()
        self.execution_monitor = ExecutionMonitor()
        self.skill_orchestrator = SkillOrchestrator(
            self.world_model, self.resource_manager, self.execution_monitor
        )
        self.task_executor = TaskExecutor(
            self.skill_orchestrator,
            self.world_model,
            self.execution_monitor,
            tick_hz=tick_hz,
        )
        self.cloud_bridge = CloudBridge()
        self.hitl_manager = HITLManager()

        # Wire callbacks
        self.world_model.on_state_changed = self._on_world_state_changed
        self.execution_monitor.on_event = self._on_execution_event
        self.task_executor.on_task_status = self._on_task_status

        if _HAS_RCLPY:
            self._setup_ros2_interfaces(publish_hz, tick_hz)

    def _setup_ros2_interfaces(self, publish_hz: float, tick_hz: float) -> None:
        """Register ROS2 services, publishers, subscribers, and timers."""
        # Timers
        self.create_timer(1.0 / tick_hz, self._tick_bt)
        self.create_timer(1.0 / publish_hz, self._publish_world_state)
        self.create_timer(1.0, self._tick_ttl)

        logger.info(
            "RuntimeNode initialized (publish_hz=%.1f, tick_hz=%.1f)",
            publish_hz,
            tick_hz,
        )

    def _tick_bt(self) -> None:
        """Timer callback: single BT tick."""
        self.task_executor.tick()

    def _publish_world_state(self) -> None:
        """Timer callback: publish full WorldState snapshot."""
        pass  # ROS2 publisher would go here

    def _tick_ttl(self) -> None:
        """Timer callback: check object TTL expiry."""
        self.world_model.tick_ttl()

    def _on_world_state_changed(self, state: Any) -> None:
        """Callback: world state changed."""
        pass  # ROS2 publisher would go here

    def _on_execution_event(self, event: Any) -> None:
        """Callback: execution event published."""
        pass  # ROS2 publisher would go here

    def _on_task_status(
        self,
        task_id: str,
        status: str,
        progress: float,
        current_node_id: str,
        failure_code: str,
        message: str,
    ) -> None:
        """Callback: task status changed."""
        pass  # ROS2 publisher would go here


def main() -> None:
    """Entry point for the runtime node."""
    if not _HAS_RCLPY:
        logger.error("rclpy not available. Cannot start RuntimeNode.")
        return

    rclpy.init()
    node = RuntimeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
