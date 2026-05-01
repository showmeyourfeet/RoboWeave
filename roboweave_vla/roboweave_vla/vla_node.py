"""VLANode: ROS2 node hosting the RunVLASkill action server.

Uses HAS_ROS2 pattern to allow import without a running ROS2 graph.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from roboweave_interfaces.vla import VLASafetyConstraints

from .skill_registry import SkillRegistry
from .vla_monitor import VLAMonitor

# Lazy ROS2 imports
try:
    import rclpy
    from rclpy.action import ActionServer, CancelResponse, GoalResponse
    from rclpy.node import Node

    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False

logger = logging.getLogger(__name__)


# Default config values
_DEFAULT_PARAMS = {
    "default_control_frequency_hz": 10.0,
    "monitor": {
        "consecutive_low_confidence_limit": 3,
        "max_rejection_count": 5,
    },
    "default_safety_constraints": {
        "min_confidence_threshold": 0.3,
        "max_duration_sec": 60.0,
    },
    "safety_filter_service": "/roboweave/safety/filter_vla_action",
}


class VLANode:
    """ROS2 node hosting the RunVLASkill action server.

    When ROS2 is not available, the class can still be imported but
    cannot be instantiated as a live node.
    """

    def __init__(self, **kwargs: Any) -> None:
        self._registry = SkillRegistry()
        self._params: dict[str, Any] = dict(_DEFAULT_PARAMS)
        self._cancelled = False
        self._node: Any = None
        self._action_server: Any = None
        self._safety_client: Any = None

        if HAS_ROS2:
            self._node = rclpy.create_node("vla_node", **kwargs)
            # Declare parameters for config paths
            self._node.declare_parameter("vla_params_path", "")
            self._node.declare_parameter("vla_skill_registry_path", "")

            params_path = (
                self._node.get_parameter("vla_params_path")
                .get_parameter_value()
                .string_value
            )
            registry_path = (
                self._node.get_parameter("vla_skill_registry_path")
                .get_parameter_value()
                .string_value
            )

            if params_path:
                self._load_params(params_path)
            if registry_path:
                self._load_skill_registry(registry_path)

            # Create safety filter client
            from .safety_filter import SafetyFilterClient

            service_name = self._params.get(
                "safety_filter_service", "/roboweave/safety/filter_vla_action"
            )
            self._safety_client = SafetyFilterClient(self._node, service_name)

            # Create action server
            try:
                from roboweave_msgs.action import RunVLASkill  # type: ignore[import]

                self._action_server = ActionServer(
                    self._node,
                    RunVLASkill,
                    "/roboweave/vla/run_skill",
                    execute_callback=self._execute_callback,
                    cancel_callback=self._cancel_callback,
                )
            except ImportError:
                self._node.get_logger().warn(
                    "roboweave_msgs not available; action server not created"
                )

    def _load_params(self, path: str) -> None:
        """Load VLA parameters from YAML file."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            self._params.update(data)
            if HAS_ROS2 and self._node:
                self._node.get_logger().info(f"Loaded VLA params from {path}")
        except Exception as e:
            if HAS_ROS2 and self._node:
                self._node.get_logger().warn(
                    f"Failed to load VLA params from {path}: {e}. Using defaults."
                )

    def _load_skill_registry(self, path: str) -> None:
        """Load and register skills from YAML registry file."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            skills_config = data.get("skills", [])
            for entry in skills_config:
                module_path = entry["module_path"]
                class_name = entry["class_name"]
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name)
                instance = cls()
                self._registry.register(instance)
                if HAS_ROS2 and self._node:
                    self._node.get_logger().info(
                        f"Registered VLA skill: {entry['skill_name']}"
                    )
        except Exception as e:
            if HAS_ROS2 and self._node:
                self._node.get_logger().warn(
                    f"Failed to load skill registry from {path}: {e}. "
                    "No skills registered."
                )

    async def _execute_callback(self, goal_handle: Any) -> Any:
        """Execute a RunVLASkill goal."""
        from roboweave_msgs.action import RunVLASkill  # type: ignore[import]

        request = goal_handle.request
        skill_name = request.skill_name
        instruction = request.instruction
        arm_id = request.arm_id
        max_steps = request.max_steps
        timeout_sec = request.timeout_sec

        # Parse safety constraints
        constraints = VLASafetyConstraints()
        if request.safety_constraints_json:
            try:
                constraints = VLASafetyConstraints.model_validate_json(
                    request.safety_constraints_json
                )
            except Exception:
                pass

        self._node.get_logger().info(
            f"VLA execution start: skill={skill_name}, instruction='{instruction}', "
            f"arm_id={arm_id}, constraints={constraints.model_dump()}"
        )

        # Look up skill
        skill = self._registry.get(skill_name)
        if skill is None:
            self._node.get_logger().error(
                f"Skill '{skill_name}' not found in registry"
            )
            goal_handle.abort()
            result = RunVLASkill.Result()
            result.status = "failed"
            result.failure_code = "VLA_SKILL_NOT_FOUND"
            result.message = f"Skill '{skill_name}' not found"
            result.steps_executed = 0
            return result

        # Reset skill before starting
        await skill.reset()

        # Create monitor
        monitor_cfg = self._params.get("monitor", {})
        effective_timeout = timeout_sec if timeout_sec > 0 else constraints.max_duration_sec
        monitor = VLAMonitor(
            max_steps=max_steps,
            timeout_sec=effective_timeout,
            consecutive_low_confidence_limit=monitor_cfg.get(
                "consecutive_low_confidence_limit", 3
            ),
            max_rejection_count=monitor_cfg.get("max_rejection_count", 5),
            min_confidence_threshold=constraints.min_confidence_threshold,
        )

        self._cancelled = False
        monitor.start()

        control_freq = self._params.get("default_control_frequency_hz", 10.0)
        control_period = 1.0 / control_freq

        # Prediction loop
        while not self._cancelled:
            # Get observation (placeholder)
            rgb = np.zeros((100, 100, 3), dtype=np.uint8)
            robot_state = None  # Would come from subscription

            try:
                from roboweave_interfaces.world_state import RobotState

                rs = RobotState(robot_id="default")
                action = await skill.predict(rgb, None, rs, instruction)
            except Exception as e:
                self._node.get_logger().error(f"predict() error: {e}")
                goal_handle.abort()
                result = RunVLASkill.Result()
                result.status = "failed"
                result.failure_code = "VLA_PREDICT_ERROR"
                result.message = str(e)
                result.steps_executed = monitor.steps_executed
                return result

            monitor.record_step(action.confidence)

            # Log step
            self._node.get_logger().info(
                f"VLA step {monitor.steps_executed}: "
                f"action_type={action.action_type.value}, "
                f"confidence={action.confidence:.3f}"
            )

            # Safety filter
            if self._safety_client and action.requires_safety_filter:
                filter_result = await self._safety_client.filter(
                    action, constraints, arm_id
                )
                if filter_result.rejection_reason == "safety_service_unavailable":
                    self._node.get_logger().error("Safety service unavailable, aborting")
                    goal_handle.abort()
                    result = RunVLASkill.Result()
                    result.status = "failed"
                    result.failure_code = "VLA_SAFETY_UNAVAILABLE"
                    result.message = "Safety filter service unavailable"
                    result.steps_executed = monitor.steps_executed
                    return result

                if not filter_result.approved:
                    monitor.record_rejection()
                    self._node.get_logger().warn(
                        f"VLA step {monitor.steps_executed} rejected: "
                        f"{filter_result.rejection_reason}"
                    )
                else:
                    # Dispatch filtered action (placeholder)
                    pass

            # Check monitor
            status = monitor.check()
            if status.should_abort:
                self._node.get_logger().error(
                    f"VLA execution aborted: {status.abort_reason}, "
                    f"steps={monitor.steps_executed}"
                )
                goal_handle.abort()
                result = RunVLASkill.Result()
                result.status = "failed"
                result.failure_code = status.abort_reason
                result.message = status.abort_reason
                result.steps_executed = monitor.steps_executed
                return result

            if status.should_finish:
                self._node.get_logger().info(
                    f"VLA execution complete: steps={monitor.steps_executed}, "
                    f"elapsed={monitor.elapsed_sec:.2f}s"
                )
                goal_handle.succeed()
                result = RunVLASkill.Result()
                result.status = "success"
                result.failure_code = ""
                result.message = "Completed successfully"
                result.steps_executed = monitor.steps_executed
                return result

            # Publish feedback
            feedback = RunVLASkill.Feedback()
            feedback.current_step = monitor.steps_executed
            feedback.confidence = action.confidence
            feedback.action_type = action.action_type.value
            feedback.status = "running"
            goal_handle.publish_feedback(feedback)

            # Wait control period
            await asyncio.sleep(control_period)

        # Cancelled
        await skill.reset()
        self._node.get_logger().info(
            f"VLA execution cancelled: steps={monitor.steps_executed}"
        )
        goal_handle.canceled()
        result = RunVLASkill.Result()
        result.status = "cancelled"
        result.failure_code = ""
        result.message = "Cancelled by request"
        result.steps_executed = monitor.steps_executed
        return result

    def _cancel_callback(self, goal_handle: Any) -> Any:
        """Accept cancel requests."""
        self._cancelled = True
        if HAS_ROS2:
            return CancelResponse.ACCEPT
        return None

    @property
    def registry(self) -> SkillRegistry:
        """Access the skill registry."""
        return self._registry


def main() -> None:
    """Entry point for the VLA node."""
    if not HAS_ROS2:
        logger.error("ROS2 (rclpy) is not available. Cannot start VLANode.")
        return

    rclpy.init()
    node = VLANode()
    try:
        rclpy.spin(node._node)
    except KeyboardInterrupt:
        pass
    finally:
        if node._node:
            node._node.destroy_node()
        rclpy.shutdown()
