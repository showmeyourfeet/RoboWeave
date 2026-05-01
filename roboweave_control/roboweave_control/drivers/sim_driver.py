"""Simulated driver for testing and development."""

from __future__ import annotations

from dataclasses import dataclass, field

from roboweave_interfaces.hardware import ArmConfig, GripperConfig

from .base import Driver, GripperStatus, JointState


@dataclass
class SimArmState:
    """Internal state for a simulated arm."""

    current_positions: list[float]
    target_positions: list[float]
    velocities: list[float]
    efforts: list[float]
    velocity_scaling: float = 1.0


@dataclass
class SimGripperState:
    """Internal state for a simulated gripper."""

    current_width: float
    target_width: float
    force: float
    speed: float = 0.1  # m/s


class SimDriver(Driver):
    """Simulated driver with velocity-limited interpolation."""

    def __init__(
        self,
        arm_configs: list[ArmConfig],
        gripper_configs: list[GripperConfig],
    ) -> None:
        super().__init__(arm_configs, gripper_configs)
        self._arm_states: dict[str, SimArmState] = {}
        self._gripper_states: dict[str, SimGripperState] = {}

    def connect(self) -> bool:
        """Initialize all arms to zero positions, grippers to max_width."""
        for arm_id, cfg in self._arm_configs.items():
            n = cfg.num_joints
            self._arm_states[arm_id] = SimArmState(
                current_positions=[0.0] * n,
                target_positions=[0.0] * n,
                velocities=[0.0] * n,
                efforts=[0.0] * n,
            )
        for gripper_id, cfg in self._gripper_configs.items():
            speed = cfg.driver_config.get("gripper_speed", 0.1)
            self._gripper_states[gripper_id] = SimGripperState(
                current_width=cfg.max_width,
                target_width=cfg.max_width,
                force=0.0,
                speed=speed,
            )
        return True

    def disconnect(self) -> None:
        """Clear internal state."""
        self._arm_states.clear()
        self._gripper_states.clear()

    def get_joint_state(self, arm_id: str) -> JointState:
        """Return current joint state for an arm."""
        state = self._arm_states[arm_id]
        return JointState(
            positions=list(state.current_positions),
            velocities=list(state.velocities),
            efforts=list(state.efforts),
        )

    def set_joint_positions(
        self, arm_id: str, positions: list[float], velocity_scaling: float = 1.0
    ) -> None:
        """Clamp positions to joint limits and store as target."""
        cfg = self._arm_configs[arm_id]
        state = self._arm_states[arm_id]
        clamped = []
        for i, pos in enumerate(positions):
            lo = cfg.joint_limits_lower[i] if i < len(cfg.joint_limits_lower) else -3.14
            hi = cfg.joint_limits_upper[i] if i < len(cfg.joint_limits_upper) else 3.14
            clamped.append(max(lo, min(hi, pos)))
        state.target_positions = clamped
        state.velocity_scaling = max(0.0, min(1.0, velocity_scaling))

    def get_gripper_state(self, gripper_id: str) -> GripperStatus:
        """Return current gripper state."""
        state = self._gripper_states[gripper_id]
        return GripperStatus(
            width=state.current_width,
            force=state.force,
            is_grasping=False,
        )

    def set_gripper_width(self, gripper_id: str, width: float) -> None:
        """Clamp width to valid range and store as target."""
        cfg = self._gripper_configs[gripper_id]
        state = self._gripper_states[gripper_id]
        state.target_width = max(cfg.min_width, min(cfg.max_width, width))

    def set_gripper_force(self, gripper_id: str, force: float) -> None:
        """Clamp force to [0, max_force] and store."""
        cfg = self._gripper_configs[gripper_id]
        state = self._gripper_states[gripper_id]
        state.force = max(0.0, min(cfg.max_force, force))

    def emergency_stop(self) -> None:
        """Set all targets to current positions, zero all velocities."""
        for state in self._arm_states.values():
            state.target_positions = list(state.current_positions)
            state.velocities = [0.0] * len(state.velocities)
        for state in self._gripper_states.values():
            state.target_width = state.current_width

    def step(self, dt: float) -> None:
        """Advance simulation by dt seconds (deterministic, no wall-clock)."""
        # Advance arm joints
        for arm_id, state in self._arm_states.items():
            cfg = self._arm_configs[arm_id]
            old_positions = list(state.current_positions)
            for i in range(len(state.current_positions)):
                delta = state.target_positions[i] - state.current_positions[i]
                max_vel = cfg.max_joint_velocities[i] if i < len(cfg.max_joint_velocities) else 2.0
                max_step = max_vel * state.velocity_scaling * dt
                step = max(-max_step, min(max_step, delta))
                state.current_positions[i] += step
            # Compute velocities
            if dt > 0:
                state.velocities = [
                    (state.current_positions[i] - old_positions[i]) / dt
                    for i in range(len(state.current_positions))
                ]
            else:
                state.velocities = [0.0] * len(state.current_positions)

        # Advance grippers
        for gripper_id, state in self._gripper_states.items():
            delta = state.target_width - state.current_width
            max_step = state.speed * dt
            step = max(-max_step, min(max_step, delta))
            state.current_width += step
