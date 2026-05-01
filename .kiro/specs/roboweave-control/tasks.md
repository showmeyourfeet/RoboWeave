# Implementation Plan: roboweave-control

## Overview

Implement the `roboweave_control` ROS2 Python package (ament_python) providing a hardware abstraction layer, simulation driver, trajectory executor, gripper controller, robot state publisher, and control node. The implementation builds on the existing `roboweave_interfaces` Pydantic models and `roboweave_msgs` ROS2 message definitions. MVP scope is simulation-only (no real hardware drivers).

Implementation proceeds bottom-up: internal data models and driver ABC first, then the SimDriver, then converters, then the ROS2-facing components (trajectory executor, gripper controller), then the control node that wires everything together, and finally configuration files and launch.

## Tasks

- [x] 1. Set up package structure and Driver ABC
  - [x] 1.1 Create the `roboweave_control` ament_python package scaffold
    - Create `roboweave_control/` directory with `__init__.py`, `roboweave_control/drivers/__init__.py`
    - Create `setup.py` with ament_python build type, entry point for `control_node`
    - Create `package.xml` with dependencies: `rclpy`, `roboweave_msgs`, `trajectory_msgs`, `geometry_msgs`
    - Create empty `config/`, `launch/`, `tests/` directories with `__init__.py` where needed
    - _Requirements: 6.1, 6.5_

  - [x] 1.2 Implement the Driver ABC and internal data models (`drivers/base.py`)
    - Define `JointState` and `GripperStatus` dataclasses as specified in the design
    - Define `Driver(ABC)` with `__init__` accepting `list[ArmConfig]` and `list[GripperConfig]`
    - Implement all abstract methods: `connect`, `disconnect`, `get_joint_state`, `set_joint_positions`, `get_gripper_state`, `set_gripper_width`, `set_gripper_force`, `emergency_stop`
    - Import `ArmConfig` and `GripperConfig` from `roboweave_interfaces.hardware`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10_

  - [ ]* 1.3 Write unit tests for Driver ABC (`tests/test_driver.py`)
    - Test that `Driver` cannot be instantiated directly (raises `TypeError`)
    - Test that a minimal concrete subclass implementing all abstract methods can be instantiated
    - Test that a subclass missing any abstract method raises `TypeError`
    - Test that `__init__` correctly stores arm and gripper configs as dictionaries keyed by ID
    - _Requirements: 1.1, 1.10_

- [x] 2. Implement SimDriver
  - [x] 2.1 Implement SimDriver internal state models and core logic (`drivers/sim_driver.py`)
    - Define `SimArmState` and `SimGripperState` dataclasses for internal tracking
    - Implement `SimDriver(Driver)` with all abstract methods
    - `connect()`: initialize all arms to zero positions, all grippers to `max_width`, return `True`
    - `disconnect()`: clear internal state dictionaries
    - `get_joint_state(arm_id)`: return current positions, computed velocities (non-zero during motion), zero efforts
    - `set_joint_positions(arm_id, positions)`: clamp to joint limits, store as target
    - `get_gripper_state(gripper_id)`: return current width, last commanded force, `is_grasping=False`
    - `set_gripper_width(gripper_id, width)`: clamp to `[min_width, max_width]`, store as target
    - `set_gripper_force(gripper_id, force)`: clamp to `[0, max_force]`, store
    - `emergency_stop()`: set all targets to current positions, zero all velocities
    - _Requirements: 2.1, 2.2, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_

  - [x] 2.2 Implement the `step(dt)` simulation tick method
    - For each arm: interpolate each joint toward target at rate bounded by `max_joint_velocities[i] * velocity_scaling * dt`
    - For each gripper: interpolate width toward target at configurable gripper speed (default 0.1 m/s) * dt
    - Compute and store velocities as `(new_position - old_position) / dt`
    - Ensure deterministic behavior (no wall-clock dependency)
    - _Requirements: 2.3, 2.4_

  - [ ]* 2.3 Write unit tests for SimDriver (`tests/test_sim_driver.py`)
    - Test `connect()` initializes arms to zero positions and grippers to max width
    - Test `set_joint_positions` clamps to joint limits
    - Test `set_gripper_width` clamps to valid range
    - Test `set_gripper_force` clamps to max force
    - Test `step(dt)` moves joints toward target respecting velocity limits
    - Test `step(dt)` moves gripper width toward target
    - Test `emergency_stop()` freezes all motion (targets = current, velocities = 0)
    - Test `get_joint_state` returns zero velocities when stationary
    - Test `disconnect()` clears state
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_

- [x] 3. Checkpoint — Verify driver layer
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement Pydantic ↔ ROS2 message converters
  - [x] 4.1 Implement converter functions (`converters.py`)
    - `arm_state_to_msg(arm: ArmState) -> ArmState msg` and `msg_to_arm_state(msg) -> ArmState`
    - `gripper_state_to_msg(gs: GripperState) -> GripperState msg` and `msg_to_gripper_state(msg) -> GripperState`
    - `robot_state_to_msg(rs: RobotState) -> RobotStateMsg` and `msg_to_robot_state(msg) -> RobotState`
    - `hardware_config_from_yaml(data: dict) -> HardwareConfig` and `hardware_config_to_yaml(config: HardwareConfig) -> dict`
    - Map `SE3` ↔ `geometry_msgs/Pose` (position → [x,y,z], quaternion → [x,y,z,w])
    - All functions are pure (stateless, no ROS2 node dependency)
    - _Requirements: 7.1, 7.2, 7.5, 7.6_

  - [ ]* 4.2 Write unit tests for converters (`tests/test_converters.py`)
    - Test round-trip: `ArmState` → msg → `ArmState` produces equivalent model
    - Test round-trip: `GripperState` → msg → `GripperState` produces equivalent model
    - Test round-trip: `RobotState` → msg → `RobotState` produces equivalent model
    - Test round-trip: `HardwareConfig` → YAML dict → `HardwareConfig` produces equivalent model
    - Test SE3 ↔ Pose conversion preserves position and quaternion values
    - _Requirements: 7.1, 7.2, 7.5, 7.6_

- [x] 5. Implement TrajectoryExecutor
  - [x] 5.1 Implement the TrajectoryExecutor class (`trajectory_executor.py`)
    - Create `TrajectoryExecutor` that hosts an `ExecuteTrajectory` action server on `/roboweave/control/execute_trajectory`
    - Accept a `Driver` instance and node reference in constructor
    - Implement goal callback: validate `arm_id` exists in driver config, reject if arm is busy
    - Implement execution loop: iterate trajectory points, call `driver.set_joint_positions()`, step driver at control rate, compute tracking error
    - Clamp `velocity_scaling` to `[0.0, 1.0]`, default to node parameter if 0
    - Abort with `CTL_TRACKING_ERROR` if tracking error exceeds threshold
    - Handle cancellation: call `driver.emergency_stop()`, return `CTL_CANCELLED`
    - Publish feedback (progress fraction, tracking_error, current_joint_positions)
    - Return result with `success=True` and `max_tracking_error` on completion
    - Track active executions per arm_id with a `dict[str, bool]`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_

  - [ ]* 5.2 Write unit tests for TrajectoryExecutor (`tests/test_trajectory_executor.py`)
    - Test successful trajectory execution with SimDriver returns `success=True`
    - Test feedback contains progress, tracking_error, and current_joint_positions
    - Test rejection of goal for unknown arm_id
    - Test rejection of concurrent goal for same arm_id
    - Test velocity_scaling is clamped to [0.0, 1.0]
    - Test abort on tracking error exceeding threshold
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.7, 3.9_

- [x] 6. Implement GripperController
  - [x] 6.1 Implement the GripperController class (`gripper_controller.py`)
    - Create `GripperController` that hosts a `GripperCommand` service on `/roboweave/control/gripper_command`
    - Accept a `Driver` instance and node reference in constructor
    - Resolve action: `"open"` → max_width, `"close"` → min_width, `"move_to_width"` → request width
    - Return `success=False`, `error_code="CTL_GRIPPER_FAILED"` for unknown gripper_id or unrecognized action
    - If `request.force > 0`, call `driver.set_gripper_force()` before width command
    - Call `driver.set_gripper_width()`, step driver until target reached or timeout
    - Query final state, return `success=True` with `achieved_width`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

  - [ ]* 6.2 Write unit tests for GripperController (`tests/test_gripper_controller.py`)
    - Test `open` action sets gripper to max width
    - Test `close` action sets gripper to min width
    - Test `move_to_width` action sets gripper to requested width
    - Test force is applied before width command when non-zero
    - Test unknown gripper_id returns `CTL_GRIPPER_FAILED`
    - Test unrecognized action returns `CTL_GRIPPER_FAILED` with valid actions message
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

- [x] 7. Checkpoint — Verify executor and controller
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement ControlNode and state publisher
  - [x] 8.1 Implement the ControlNode (`control_node.py`)
    - Create `ControlNode(rclpy.node.Node)` as the main ROS2 node
    - Declare ROS2 parameters: `hardware_config_path`, `publish_rate_hz` (default 50.0), `default_velocity_scaling` (default 0.5), `tracking_error_threshold` (default 0.1)
    - Load `HardwareConfig` from YAML file path via `hardware_config_from_yaml` converter
    - Instantiate `SimDriver` based on `driver_type == "sim"` in arm configs
    - Call `driver.connect()` on startup; if fails, log error and shut down
    - Instantiate `TrajectoryExecutor` and `GripperController` as sub-components
    - Create timer-based robot state publisher at `publish_rate_hz` on `/roboweave/robot_state`
    - In timer callback: query driver for all arm/gripper states, build `RobotStateMsg` via converters, set `is_moving` based on velocity threshold (default 0.01 rad/s), publish
    - Call `driver.disconnect()` on shutdown
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [ ]* 8.2 Write unit tests for ControlNode (`tests/test_control_node.py`)
    - Test node creates with valid hardware config
    - Test node shuts down gracefully when driver connect fails
    - Test state publisher publishes `RobotStateMsg` with correct arm and gripper states
    - Test `is_moving` is set correctly based on joint velocity threshold
    - Test ROS2 parameters are declared with correct defaults
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [x] 9. Create configuration files
  - [x] 9.1 Create control parameter and hardware config YAML files
    - Create `config/control_params.yaml` with `publish_rate_hz: 50.0`, `default_velocity_scaling: 0.5`, `tracking_error_threshold: 0.1`
    - Create `config/sim_arm.yaml` with a 7-DOF simulated arm config conforming to `ArmConfig` schema (arm_id, joint_names, joint_limits, max_velocities, driver_type: sim)
    - Create `config/sim_gripper.yaml` with a parallel gripper config conforming to `GripperConfig` schema (gripper_id, width range, max_force, driver_type: sim)
    - _Requirements: 8.1, 8.2, 8.3_

- [x] 10. Create launch file
  - [x] 10.1 Create the ROS2 launch file (`launch/control.launch.py`)
    - Launch `ControlNode` with default parameters from `control_params.yaml`
    - Accept launch arguments: `hardware_config_path`, `publish_rate_hz`, `default_velocity_scaling`
    - Pass launch arguments as ROS2 parameter overrides to the node
    - _Requirements: 8.4, 8.5, 9.1, 9.2, 9.3_

- [x] 11. Checkpoint — Verify full integration
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Final wiring and test configuration
  - [x] 12.1 Create test fixtures and conftest (`tests/conftest.py`)
    - Create shared pytest fixtures: sample `ArmConfig`, `GripperConfig`, `HardwareConfig`
    - Create a fixture that provides a connected `SimDriver` instance
    - Create a fixture for a minimal ROS2 node context (for action/service tests)
    - _Requirements: 1.10, 2.1, 2.2_

  - [ ]* 12.2 Write integration tests (`tests/test_integration.py`)
    - Test full flow: ControlNode starts → SimDriver connects → trajectory executes → state publishes
    - Test gripper command through ControlNode service endpoint
    - Test that state publisher reflects SimDriver state changes after trajectory execution
    - _Requirements: 3.2, 4.6, 5.1, 5.2, 6.3, 6.5_

- [x] 13. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirement acceptance criteria for traceability
- The design has no Correctness Properties section, so property-based tests are not included
- All code is Python 3.10+ targeting ROS2 Humble with ament_python build
- Safety monitoring is explicitly out of scope (handled by `roboweave_safety`)
- The SimDriver uses `step(dt)` for deterministic, wall-clock-independent simulation
