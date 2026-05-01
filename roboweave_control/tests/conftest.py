"""Shared pytest fixtures for roboweave_control tests."""

from __future__ import annotations

import pytest

from roboweave_interfaces.hardware import ArmConfig, GripperConfig, HardwareConfig
from roboweave_control.drivers.sim_driver import SimDriver


@pytest.fixture
def sample_arm_config() -> ArmConfig:
    """A 7-DOF simulated arm configuration."""
    return ArmConfig(
        arm_id="test_arm",
        name="Test Arm",
        num_joints=7,
        joint_names=["j1", "j2", "j3", "j4", "j5", "j6", "j7"],
        joint_limits_lower=[-3.14, -2.09, -3.14, -2.09, -3.14, -2.09, -3.14],
        joint_limits_upper=[3.14, 2.09, 3.14, 2.09, 3.14, 2.09, 3.14],
        max_joint_velocities=[2.0, 2.0, 2.0, 2.0, 2.5, 2.5, 2.5],
        max_joint_efforts=[87.0, 87.0, 87.0, 87.0, 12.0, 12.0, 12.0],
        driver_type="sim",
    )


@pytest.fixture
def sample_gripper_config() -> GripperConfig:
    """A parallel gripper configuration."""
    return GripperConfig(
        gripper_id="test_gripper",
        name="Test Gripper",
        type="parallel",
        min_width=0.0,
        max_width=0.08,
        max_force=20.0,
        driver_type="sim",
    )


@pytest.fixture
def sample_hardware_config(
    sample_arm_config: ArmConfig,
    sample_gripper_config: GripperConfig,
) -> HardwareConfig:
    """Complete hardware config with one arm and one gripper."""
    return HardwareConfig(
        robot_id="test_robot",
        robot_name="Test Robot",
        arms=[sample_arm_config],
        grippers=[sample_gripper_config],
    )


@pytest.fixture
def connected_sim_driver(
    sample_arm_config: ArmConfig,
    sample_gripper_config: GripperConfig,
) -> SimDriver:
    """A SimDriver instance that is already connected."""
    driver = SimDriver([sample_arm_config], [sample_gripper_config])
    driver.connect()
    return driver
