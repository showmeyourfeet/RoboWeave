"""SafetyMonitor — pure Python velocity, force/torque, and workspace checks."""

from __future__ import annotations

import math
import time
import uuid

from roboweave_interfaces.safety import (
    SafetyConfig,
    SafetyEvent,
    SafetyLevel,
    WorkspaceLimits,
)
from roboweave_interfaces.world_state import ArmState


class SafetyMonitor:
    """Checks robot arm state against configured safety limits.

    Stateless per call — takes arm states and returns violations.
    """

    def __init__(self, config: SafetyConfig, workspace: WorkspaceLimits) -> None:
        self._config = config
        self._workspace = workspace

    def check(self, arms: list[ArmState]) -> list[SafetyEvent]:
        """Check all arms against velocity, force/torque, and workspace limits."""
        violations: list[SafetyEvent] = []
        for arm in arms:
            violations.extend(self.check_velocity(arm))
            violations.extend(self.check_force_torque(arm))
            violations.extend(self.check_workspace(arm))
        return violations

    def check_velocity(self, arm: ArmState) -> list[SafetyEvent]:
        """Per-joint velocity check and EEF velocity magnitude check."""
        violations: list[SafetyEvent] = []
        now = time.time()

        # Per-joint velocity check
        for i, vel in enumerate(arm.joint_velocities):
            if i < len(self._config.max_joint_velocity):
                limit = self._config.max_joint_velocity[i]
                if abs(vel) > limit:
                    violations.append(SafetyEvent(
                        event_id=str(uuid.uuid4()),
                        safety_level=SafetyLevel.WARNING,
                        violation_type="velocity_exceeded",
                        message=f"Joint {i} velocity {vel:.3f} exceeds limit {limit:.3f} on arm {arm.arm_id}",
                        timestamp=now,
                    ))

        # EEF linear velocity (use joint velocities magnitude as proxy)
        if arm.joint_velocities:
            eef_linear_vel = math.sqrt(sum(v * v for v in arm.joint_velocities))
            if eef_linear_vel > self._config.max_eef_velocity:
                violations.append(SafetyEvent(
                    event_id=str(uuid.uuid4()),
                    safety_level=SafetyLevel.WARNING,
                    violation_type="velocity_exceeded",
                    message=f"EEF linear velocity {eef_linear_vel:.3f} exceeds limit {self._config.max_eef_velocity:.3f} on arm {arm.arm_id}",
                    timestamp=now,
                ))

        return violations

    def check_force_torque(self, arm: ArmState) -> list[SafetyEvent]:
        """Per-joint effort check against torque_limit."""
        violations: list[SafetyEvent] = []
        now = time.time()

        for i, effort in enumerate(arm.joint_efforts):
            if abs(effort) > self._config.torque_limit:
                violations.append(SafetyEvent(
                    event_id=str(uuid.uuid4()),
                    safety_level=SafetyLevel.WARNING,
                    violation_type="torque_exceeded",
                    message=f"Joint {i} effort {effort:.3f} exceeds torque limit {self._config.torque_limit:.3f} on arm {arm.arm_id}",
                    timestamp=now,
                ))

        return violations

    def check_workspace(self, arm: ArmState) -> list[SafetyEvent]:
        """EEF position check against WorkspaceLimits bounds."""
        violations: list[SafetyEvent] = []
        now = time.time()
        pos = arm.eef_pose.position

        if len(pos) >= 3:
            x, y, z = pos[0], pos[1], pos[2]
            out_of_bounds = (
                x < self._workspace.x_min or x > self._workspace.x_max
                or y < self._workspace.y_min or y > self._workspace.y_max
                or z < self._workspace.z_min or z > self._workspace.z_max
            )
            if out_of_bounds:
                violations.append(SafetyEvent(
                    event_id=str(uuid.uuid4()),
                    safety_level=SafetyLevel.CRITICAL,
                    violation_type="workspace_violation",
                    message=f"EEF position [{x:.3f}, {y:.3f}, {z:.3f}] outside workspace bounds on arm {arm.arm_id}",
                    timestamp=now,
                ))

        return violations

    def update_config(self, config: SafetyConfig) -> None:
        """Update safety configuration at runtime."""
        self._config = config

    def update_workspace(self, workspace: WorkspaceLimits) -> None:
        """Update workspace limits at runtime."""
        self._workspace = workspace
