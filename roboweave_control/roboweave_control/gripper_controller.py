"""Gripper control logic (pure Python core).

The ROS2 service wiring lives in ControlNode. This class implements
action resolution, force application, and width commanding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .drivers.base import Driver


@dataclass
class GripperCommandRequest:
    """Request for a gripper command."""

    gripper_id: str
    action: str  # "open", "close", "move_to_width"
    width: float = 0.0
    force: float = 0.0


@dataclass
class GripperCommandResponse:
    """Response from a gripper command."""

    success: bool
    achieved_width: float = 0.0
    error_code: str = ""
    message: str = ""


VALID_ACTIONS = ("open", "close", "move_to_width")


class GripperController:
    """Controls gripper actions: open, close, move_to_width."""

    def __init__(
        self,
        driver: Driver,
        timeout_sec: float = 5.0,
        control_rate_hz: float = 50.0,
    ) -> None:
        self._driver = driver
        self._timeout_sec = timeout_sec
        self._control_dt = 1.0 / control_rate_hz

    def execute(self, request: GripperCommandRequest) -> GripperCommandResponse:
        """Execute a gripper command.

        Args:
            request: The gripper command request.

        Returns:
            GripperCommandResponse with success status and achieved width.
        """
        gripper_id = request.gripper_id

        # Validate gripper exists
        if gripper_id not in self._driver._gripper_configs:
            return GripperCommandResponse(
                success=False,
                error_code="CTL_GRIPPER_FAILED",
                message=f"Unknown gripper_id: {gripper_id}",
            )

        cfg = self._driver._gripper_configs[gripper_id]

        # Resolve action to target width
        action = request.action
        if action == "open":
            target_width = cfg.max_width
        elif action == "close":
            target_width = cfg.min_width
        elif action == "move_to_width":
            target_width = request.width
        else:
            return GripperCommandResponse(
                success=False,
                error_code="CTL_GRIPPER_FAILED",
                message=f"Unknown action '{action}'. Valid actions: {', '.join(VALID_ACTIONS)}",
            )

        # Apply force before width command
        if request.force > 0:
            self._driver.set_gripper_force(gripper_id, request.force)

        # Command width
        self._driver.set_gripper_width(gripper_id, target_width)

        # Step driver until target reached or timeout
        elapsed = 0.0
        while elapsed < self._timeout_sec:
            self._driver.step(self._control_dt)
            elapsed += self._control_dt
            state = self._driver.get_gripper_state(gripper_id)
            if abs(state.width - target_width) < 1e-6:
                break

        # Query final state
        final_state = self._driver.get_gripper_state(gripper_id)
        return GripperCommandResponse(
            success=True,
            achieved_width=final_state.width,
        )
