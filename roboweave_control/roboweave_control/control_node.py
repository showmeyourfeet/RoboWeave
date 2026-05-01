"""ControlNode - Main entry point for roboweave_control.

If ROS2 (rclpy) is available, runs as a ROS2 node.
Otherwise, provides the class structure for standalone use.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from roboweave_interfaces.hardware import HardwareConfig

from .converters import hardware_config_from_yaml, robot_state_to_msg
from .drivers.base import Driver
from .drivers.sim_driver import SimDriver
from .gripper_controller import GripperController
from .trajectory_executor import TrajectoryExecutor
from .converters import (
    arm_state_to_msg,
    gripper_state_to_msg,
)
from roboweave_interfaces.world_state import ArmState, GripperState, RobotState

logger = logging.getLogger(__name__)

# Try importing ROS2
try:
    import rclpy
    from rclpy.node import Node

    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False
    Node = object  # type: ignore[assignment,misc]


class ControlNode(Node):  # type: ignore[misc]
    """Main control node managing driver lifecycle and sub-components."""

    # Default parameters
    DEFAULT_PUBLISH_RATE_HZ = 50.0
    DEFAULT_VELOCITY_SCALING = 0.5
    DEFAULT_TRACKING_ERROR_THRESHOLD = 0.1
    VELOCITY_THRESHOLD = 0.01  # rad/s for is_moving detection

    def __init__(
        self,
        hardware_config_path: str = "",
        publish_rate_hz: float = DEFAULT_PUBLISH_RATE_HZ,
        default_velocity_scaling: float = DEFAULT_VELOCITY_SCALING,
        tracking_error_threshold: float = DEFAULT_TRACKING_ERROR_THRESHOLD,
        **kwargs: Any,
    ) -> None:
        if HAS_ROS2:
            super().__init__("control_node", **kwargs)
            # Declare ROS2 parameters
            self.declare_parameter("hardware_config_path", hardware_config_path)
            self.declare_parameter("publish_rate_hz", publish_rate_hz)
            self.declare_parameter("default_velocity_scaling", default_velocity_scaling)
            self.declare_parameter("tracking_error_threshold", tracking_error_threshold)
            # Read back from parameter server
            hardware_config_path = self.get_parameter("hardware_config_path").value
            publish_rate_hz = self.get_parameter("publish_rate_hz").value
            default_velocity_scaling = self.get_parameter("default_velocity_scaling").value
            tracking_error_threshold = self.get_parameter("tracking_error_threshold").value

        self._publish_rate_hz = publish_rate_hz
        self._default_velocity_scaling = default_velocity_scaling
        self._tracking_error_threshold = tracking_error_threshold

        # Load hardware config
        self._hardware_config: HardwareConfig | None = None
        self._driver: Driver | None = None
        self._trajectory_executor: TrajectoryExecutor | None = None
        self._gripper_controller: GripperController | None = None

        if hardware_config_path:
            self._load_and_start(hardware_config_path)

    def _load_and_start(self, config_path: str) -> None:
        """Load config, instantiate driver, connect, and create sub-components."""
        path = Path(config_path)
        if not path.exists():
            logger.error(f"Hardware config not found: {config_path}")
            return

        with open(path) as f:
            data = yaml.safe_load(f)

        self._hardware_config = hardware_config_from_yaml(data)
        self._driver = self._create_driver(self._hardware_config)

        if not self._driver.connect():
            logger.error("Driver connect() failed. Shutting down.")
            if HAS_ROS2:
                self.destroy_node()
            return

        # Create sub-components
        self._trajectory_executor = TrajectoryExecutor(
            driver=self._driver,
            default_velocity_scaling=self._default_velocity_scaling,
            tracking_error_threshold=self._tracking_error_threshold,
            control_rate_hz=self._publish_rate_hz,
        )
        self._gripper_controller = GripperController(
            driver=self._driver,
            control_rate_hz=self._publish_rate_hz,
        )

        # Set up state publisher timer (ROS2 only)
        if HAS_ROS2:
            period = 1.0 / self._publish_rate_hz
            self._state_timer = self.create_timer(period, self._publish_state)
            # TODO: Create ROS2 action server for ExecuteTrajectory
            # TODO: Create ROS2 service server for GripperCommand

        logger.info("ControlNode started successfully.")

    def _create_driver(self, config: HardwareConfig) -> Driver:
        """Instantiate the appropriate driver based on config."""
        # MVP: only sim driver
        return SimDriver(config.arms, config.grippers)

    def _publish_state(self) -> None:
        """Timer callback: query driver, build RobotState, publish."""
        if not self._driver or not self._hardware_config:
            return

        arms = []
        for arm_id in self._driver._arm_configs:
            js = self._driver.get_joint_state(arm_id)
            arms.append(ArmState(
                arm_id=arm_id,
                joint_positions=js.positions,
                joint_velocities=js.velocities,
                joint_efforts=js.efforts,
            ))

        grippers = []
        for gripper_id in self._driver._gripper_configs:
            gs = self._driver.get_gripper_state(gripper_id)
            grippers.append(GripperState(
                gripper_id=gripper_id,
                width=gs.width,
                force=gs.force,
                is_grasping=gs.is_grasping,
            ))

        # Determine is_moving
        is_moving = any(
            any(abs(v) > self.VELOCITY_THRESHOLD for v in arm.joint_velocities)
            for arm in arms
        )

        robot_state = RobotState(
            robot_id=self._hardware_config.robot_id,
            arms=arms,
            grippers=grippers,
            is_moving=is_moving,
        )

        # TODO: Publish robot_state_to_msg(robot_state) on /roboweave/robot_state
        self._last_robot_state = robot_state

    def shutdown(self) -> None:
        """Disconnect driver on shutdown."""
        if self._driver:
            self._driver.disconnect()
            logger.info("Driver disconnected.")


def main() -> None:
    """Entry point for the control node."""
    if HAS_ROS2:
        rclpy.init()
        node = ControlNode()
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            node.shutdown()
            node.destroy_node()
            rclpy.shutdown()
    else:
        logger.warning("ROS2 not available. ControlNode requires rclpy to run.")


if __name__ == "__main__":
    main()
