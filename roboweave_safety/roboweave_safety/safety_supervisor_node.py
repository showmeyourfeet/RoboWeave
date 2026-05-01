"""SafetySupervisorNode — ROS2 node wiring for the safety supervisor."""

from __future__ import annotations

import time
from pathlib import Path

import yaml

try:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import (
        DurabilityPolicy,
        QoSProfile,
        ReliabilityPolicy,
    )

    HAS_RCLPY = True
except ImportError:
    HAS_RCLPY = False

from roboweave_interfaces.safety import SafetyConfig, SafetyLevel, WorkspaceLimits

from .converters import (
    json_envelope_to_vla_action,
    json_envelope_to_vla_constraints,
    robot_state_msg_to_arms,
    safety_status_to_msg,
    vla_action_to_json_envelope,
)
from .safety_guard import SafetyGuard
from .safety_monitor import SafetyMonitor
from .vla_safety_filter import VLASafetyFilter


def _load_yaml(path: str) -> dict:
    """Load a YAML file, return empty dict on failure."""
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    with open(p) as f:
        return yaml.safe_load(f) or {}


if HAS_RCLPY:

    class SafetySupervisorNode(Node):
        """ROS2 node that composes SafetyMonitor, SafetyGuard, VLASafetyFilter."""

        def __init__(self) -> None:
            super().__init__("safety_supervisor")

            # Declare parameters
            self.declare_parameter("safety_params_file", "")
            self.declare_parameter("workspace_limits_file", "")
            self.declare_parameter("publish_rate_hz", 10.0)
            self.declare_parameter("watchdog_timeout_sec", 0.5)

            # Load config
            config = self._load_safety_config()
            workspaces = self._load_workspace_limits()
            default_workspace = workspaces.get("default", WorkspaceLimits())

            # Create components
            self.monitor = SafetyMonitor(config, default_workspace)
            self.guard = SafetyGuard()
            self.vla_filter = VLASafetyFilter(
                config, default_workspace, self.guard, workspaces
            )

            # Heartbeat counter
            self._heartbeat: float = 0.0
            self._last_robot_state_time: float = time.time()

            # Publisher — QoS: Reliable, depth=1, Transient Local
            qos = QoSProfile(
                reliability=ReliabilityPolicy.RELIABLE,
                depth=1,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
            )
            self._status_pub = self.create_publisher(
                self._get_msg_type("SafetyStatus"),
                "/roboweave/safety/status",
                qos,
            )

            # Subscriber
            self._state_sub = self.create_subscription(
                self._get_msg_type("RobotStateMsg"),
                "/roboweave/robot_state",
                self._robot_state_callback,
                10,
            )

            # Timer for status publishing
            rate = self.get_parameter("publish_rate_hz").value
            self._timer = self.create_timer(1.0 / rate, self._publish_status)

            # Watchdog timer
            watchdog_sec = self.get_parameter("watchdog_timeout_sec").value
            self._watchdog_timer = self.create_timer(
                watchdog_sec, self._watchdog_check
            )

            # Services
            self._safety_control_srv = self.create_service(
                self._get_srv_type("SafetyControl"),
                "/roboweave/safety/control",
                self._safety_control_callback,
            )
            self._filter_vla_srv = self.create_service(
                self._get_srv_type("FilterVLAAction"),
                "/roboweave/safety/filter_vla_action",
                self._filter_vla_callback,
            )

            self.get_logger().info("SafetySupervisorNode initialized")

        def _get_msg_type(self, name: str):
            """Dynamically import a roboweave_msgs message type."""
            import importlib
            mod = importlib.import_module("roboweave_msgs.msg")
            return getattr(mod, name)

        def _get_srv_type(self, name: str):
            """Dynamically import a roboweave_msgs service type."""
            import importlib
            mod = importlib.import_module("roboweave_msgs.srv")
            return getattr(mod, name)

        def _load_safety_config(self) -> SafetyConfig:
            """Load SafetyConfig from YAML, fall back to defaults."""
            path = self.get_parameter("safety_params_file").value
            data = _load_yaml(path)
            if not data:
                self.get_logger().warning(
                    f"Safety params file not found or empty: '{path}', using defaults"
                )
                return SafetyConfig()
            safety_data = data.get("safety", data)
            try:
                return SafetyConfig(**safety_data)
            except Exception as e:
                self.get_logger().warning(f"Invalid safety config: {e}, using defaults")
                return SafetyConfig()

        def _load_workspace_limits(self) -> dict[str, WorkspaceLimits]:
            """Load workspace limits from YAML, fall back to defaults."""
            path = self.get_parameter("workspace_limits_file").value
            data = _load_yaml(path)
            if not data:
                self.get_logger().warning(
                    f"Workspace limits file not found or empty: '{path}', using defaults"
                )
                return {"default": WorkspaceLimits()}
            workspaces_data = data.get("workspaces", data)
            result: dict[str, WorkspaceLimits] = {}
            for name, ws_data in workspaces_data.items():
                try:
                    result[name] = WorkspaceLimits(**ws_data)
                except Exception as e:
                    self.get_logger().warning(
                        f"Invalid workspace '{name}': {e}, skipping"
                    )
            if "default" not in result:
                result["default"] = WorkspaceLimits()
            return result

        def _robot_state_callback(self, msg) -> None:
            """Process incoming robot state."""
            self._last_robot_state_time = time.time()
            # Convert msg to dict (ROS2 msg has a to_dict or we access fields)
            try:
                msg_dict = {"arms": []}
                for arm_msg in msg.arms:
                    arm_dict = {
                        "arm_id": arm_msg.arm_id,
                        "joint_positions": list(arm_msg.joint_positions),
                        "joint_velocities": list(arm_msg.joint_velocities),
                        "joint_efforts": list(arm_msg.joint_efforts),
                        "eef_pose": {
                            "position": list(arm_msg.eef_pose.position),
                            "orientation": {
                                "x": arm_msg.eef_pose.orientation.x,
                                "y": arm_msg.eef_pose.orientation.y,
                                "z": arm_msg.eef_pose.orientation.z,
                                "w": arm_msg.eef_pose.orientation.w,
                            },
                        },
                    }
                    msg_dict["arms"].append(arm_dict)

                arms = robot_state_msg_to_arms(msg_dict)
                violations = self.monitor.check(arms)

                if violations:
                    for v in violations:
                        self.get_logger().warning(f"Safety violation: {v.message}")
                    self.guard.process_violations(violations)
                else:
                    # Clear timeout violation if present
                    if "robot_state_timeout" in self.guard.active_violations:
                        self.guard.clear_violations()
            except Exception as e:
                self.get_logger().error(f"Error processing robot state: {e}")

        def _watchdog_check(self) -> None:
            """Check for robot state timeout."""
            timeout = self.get_parameter("watchdog_timeout_sec").value
            elapsed = time.time() - self._last_robot_state_time
            if elapsed > timeout:
                if "robot_state_timeout" not in self.guard.active_violations:
                    self.get_logger().warning("Robot state watchdog timeout")
                    from roboweave_interfaces.safety import SafetyEvent
                    import uuid
                    timeout_event = SafetyEvent(
                        event_id=str(uuid.uuid4()),
                        safety_level=SafetyLevel.WARNING,
                        violation_type="robot_state_timeout",
                        message="No robot state received within watchdog timeout",
                        timestamp=time.time(),
                    )
                    self.guard.process_violations([timeout_event])

        def _publish_status(self) -> None:
            """Publish safety status at configured rate."""
            self._heartbeat += 1.0
            status_dict = safety_status_to_msg(
                self.guard.level, self.guard, self._heartbeat
            )
            # Build and publish ROS2 message
            try:
                SafetyStatusMsg = self._get_msg_type("SafetyStatus")
                msg = SafetyStatusMsg()
                msg.level = status_dict["level"]
                msg.e_stop_active = status_dict["e_stop_active"]
                msg.e_stop_latched = status_dict["e_stop_latched"]
                msg.active_violations = status_dict["active_violations"]
                msg.heartbeat = status_dict["heartbeat"]
                self._status_pub.publish(msg)
            except Exception as e:
                self.get_logger().error(f"Error publishing status: {e}")

        def _safety_control_callback(self, request, response):
            """Handle SafetyControl service requests."""
            action = request.action
            self.get_logger().info(f"SafetyControl request: action={action}")

            supported_actions = [
                "emergency_stop", "release_stop", "enter_safe_mode",
                "set_speed_limit", "set_force_limit", "set_workspace",
            ]

            if action == "emergency_stop":
                self.guard.emergency_stop()
                response.success = True
                response.message = "Emergency stop activated"
            elif action == "release_stop":
                operator_id = getattr(request, "operator_id", "")
                ok, msg = self.guard.release_stop(operator_id)
                response.success = ok
                response.message = msg
            elif action == "enter_safe_mode":
                self.guard.enter_safe_mode()
                response.success = True
                response.message = "Safe mode activated"
            elif action == "set_speed_limit":
                try:
                    import json
                    params = json.loads(request.params_json)
                    config = self.monitor._config.model_copy()
                    if "max_joint_velocity" in params:
                        config.max_joint_velocity = params["max_joint_velocity"]
                    if "max_eef_velocity" in params:
                        config.max_eef_velocity = params["max_eef_velocity"]
                    self.monitor.update_config(config)
                    response.success = True
                    response.message = "Speed limits updated"
                except Exception as e:
                    response.success = False
                    response.message = f"Invalid params: {e}"
            elif action == "set_force_limit":
                try:
                    import json
                    params = json.loads(request.params_json)
                    config = self.monitor._config.model_copy()
                    if "torque_limit" in params:
                        config.torque_limit = params["torque_limit"]
                    if "force_limit" in params:
                        config.force_limit = params["force_limit"]
                    self.monitor.update_config(config)
                    response.success = True
                    response.message = "Force limits updated"
                except Exception as e:
                    response.success = False
                    response.message = f"Invalid params: {e}"
            elif action == "set_workspace":
                try:
                    import json
                    params = json.loads(request.params_json)
                    workspace = WorkspaceLimits(**params)
                    self.monitor.update_workspace(workspace)
                    response.success = True
                    response.message = "Workspace limits updated"
                except Exception as e:
                    response.success = False
                    response.message = f"Invalid params: {e}"
            else:
                response.success = False
                response.message = (
                    f"Unrecognized action '{action}'. "
                    f"Supported: {supported_actions}"
                )

            return response

        def _filter_vla_callback(self, request, response):
            """Handle FilterVLAAction service requests."""
            try:
                action = json_envelope_to_vla_action(request.action_json)
                constraints = json_envelope_to_vla_constraints(
                    request.constraints_json
                )
                arm_id = getattr(request, "arm_id", "")
                current_pose = None
                if hasattr(request, "current_eef_pose_json") and request.current_eef_pose_json:
                    import json
                    pose_data = json.loads(request.current_eef_pose_json)
                    current_pose = SE3(**pose_data)

                approved, filtered, reason, vtype = self.vla_filter.filter_action(
                    action, constraints, arm_id, current_pose
                )

                response.approved = approved
                response.rejection_reason = reason
                response.violation_type = vtype
                if filtered is not None:
                    response.filtered_action_json = vla_action_to_json_envelope(filtered)
                else:
                    response.filtered_action_json = ""

                if not approved:
                    self.get_logger().warning(
                        f"VLA action rejected: {reason} ({vtype})"
                    )
            except Exception as e:
                response.approved = False
                response.rejection_reason = f"deserialization_error: {e}"
                response.violation_type = "deserialization_error"
                response.filtered_action_json = ""
                self.get_logger().error(f"VLA filter error: {e}")

            return response


def main():
    """Entry point for the safety_supervisor node."""
    if not HAS_RCLPY:
        print("ERROR: rclpy not available. Cannot start SafetySupervisorNode.")
        return

    rclpy.init()
    node = SafetySupervisorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
