"""VLASafetyFilter — pure Python VLA action clamping and rejection pipeline."""

from __future__ import annotations

import math

from roboweave_interfaces.safety import SafetyConfig, WorkspaceLimits
from roboweave_interfaces.vla import VLAAction, VLAActionSpace, VLASafetyConstraints
from roboweave_interfaces.world_state import SE3

from .safety_guard import SafetyGuard


class VLASafetyFilter:
    """Filters VLA actions by clamping velocities and checking workspace/confidence."""

    def __init__(
        self,
        config: SafetyConfig,
        default_workspace: WorkspaceLimits,
        guard: SafetyGuard,
        workspaces: dict[str, WorkspaceLimits] | None = None,
    ) -> None:
        self._config = config
        self._default_workspace = default_workspace
        self._guard = guard
        self._workspaces = workspaces or {}

    def filter_action(
        self,
        action: VLAAction,
        constraints: VLASafetyConstraints,
        arm_id: str,
        current_eef_pose: SE3 | None = None,
    ) -> tuple[bool, VLAAction | None, str, str]:
        """Filter a VLA action through the safety pipeline.

        Returns (approved, filtered_action_or_None, rejection_reason, violation_type).
        """
        # 1. E-stop check
        if self._guard.e_stop_active:
            return (False, None, "emergency_stop_active", "emergency_stop")

        # 2. Confidence check
        if action.confidence < constraints.min_confidence_threshold:
            return (
                False, None,
                f"confidence {action.confidence:.3f} below threshold {constraints.min_confidence_threshold:.3f}",
                "confidence_below_threshold",
            )

        # Work on a copy of the action for clamping
        filtered = action.model_copy(deep=True)

        # 3. Velocity clamping — clamp delta_pose linear magnitude
        control_freq = VLAActionSpace().control_frequency_hz  # default 10 Hz
        max_linear_step = constraints.max_velocity / control_freq

        if filtered.delta_pose is not None:
            pos = filtered.delta_pose.position
            if len(pos) >= 3:
                mag = math.sqrt(pos[0] ** 2 + pos[1] ** 2 + pos[2] ** 2)
                if mag > max_linear_step and mag > 0:
                    scale = max_linear_step / mag
                    filtered.delta_pose.position = [
                        pos[0] * scale,
                        pos[1] * scale,
                        pos[2] * scale,
                    ]

        # Clamp joint deltas — preserve sign
        max_joint_delta = VLAActionSpace().max_joint_delta
        if filtered.joint_delta:
            clamped = []
            for jd in filtered.joint_delta:
                if abs(jd) > max_joint_delta:
                    clamped.append(math.copysign(max_joint_delta, jd))
                else:
                    clamped.append(jd)
            filtered.joint_delta = clamped

        # 4. Workspace check
        workspace = self._resolve_workspace(constraints.workspace_limit_id)
        if current_eef_pose is not None and filtered.delta_pose is not None:
            result_pos = [
                current_eef_pose.position[i] + filtered.delta_pose.position[i]
                for i in range(3)
            ]
            x, y, z = result_pos[0], result_pos[1], result_pos[2]
            if (
                x < workspace.x_min or x > workspace.x_max
                or y < workspace.y_min or y > workspace.y_max
                or z < workspace.z_min or z > workspace.z_max
            ):
                return (
                    False, None,
                    f"resulting EEF position [{x:.3f}, {y:.3f}, {z:.3f}] outside workspace",
                    "workspace_violation",
                )

        # 5. Approve
        return (True, filtered, "", "")

    def _resolve_workspace(self, workspace_id: str) -> WorkspaceLimits:
        """Look up workspace by ID, fall back to default."""
        if workspace_id and workspace_id in self._workspaces:
            return self._workspaces[workspace_id]
        return self._default_workspace
