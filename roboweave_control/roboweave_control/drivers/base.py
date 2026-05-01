"""Driver ABC and internal data models for hardware abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from roboweave_interfaces.hardware import ArmConfig, GripperConfig


@dataclass
class JointState:
    """Snapshot of an arm's joint state."""

    positions: list[float]
    velocities: list[float]
    efforts: list[float]


@dataclass
class GripperStatus:
    """Snapshot of a gripper's state."""

    width: float
    force: float
    is_grasping: bool


class Driver(ABC):
    """Hardware abstraction for robot arms and grippers."""

    def __init__(
        self,
        arm_configs: list[ArmConfig],
        gripper_configs: list[GripperConfig],
    ) -> None:
        self._arm_configs: dict[str, ArmConfig] = {ac.arm_id: ac for ac in arm_configs}
        self._gripper_configs: dict[str, GripperConfig] = {
            gc.gripper_id: gc for gc in gripper_configs
        }

    @abstractmethod
    def connect(self) -> bool:
        """Connect to hardware. Returns True on success."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from hardware."""
        ...

    @abstractmethod
    def get_joint_state(self, arm_id: str) -> JointState:
        """Get current joint state for an arm."""
        ...

    @abstractmethod
    def set_joint_positions(
        self, arm_id: str, positions: list[float], velocity_scaling: float = 1.0
    ) -> None:
        """Set target joint positions for an arm."""
        ...

    @abstractmethod
    def get_gripper_state(self, gripper_id: str) -> GripperStatus:
        """Get current gripper state."""
        ...

    @abstractmethod
    def set_gripper_width(self, gripper_id: str, width: float) -> None:
        """Set target gripper width."""
        ...

    @abstractmethod
    def set_gripper_force(self, gripper_id: str, force: float) -> None:
        """Set gripper force."""
        ...

    @abstractmethod
    def emergency_stop(self) -> None:
        """Emergency stop all motion."""
        ...
