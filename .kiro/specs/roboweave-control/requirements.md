# Requirements Document

## Introduction

The `roboweave_control` package is the control execution layer of the RoboWeave hybrid robotics system. It provides a hardware abstraction layer (driver base class and simulation driver), a trajectory executor (ROS2 action server), a gripper controller (ROS2 service server), a robot state publisher (ROS2 topic), and Pydantic ↔ ROS2 msg converters. This package does NOT include safety monitoring (handled by `roboweave_safety`). The MVP target is simulation-only operation with no real hardware dependency.

This is Phase 1.1 of the RoboWeave project, building on the already-implemented `roboweave_interfaces` (Pydantic models) and `roboweave_msgs` (ROS2 msg/srv/action definitions).

## Glossary

- **Driver**: A hardware abstraction that implements a uniform interface for commanding a robot arm and gripper, regardless of whether the underlying hardware is real or simulated.
- **Sim_Driver**: A concrete Driver implementation that simulates joint motion and gripper actuation in software, with no real hardware dependency.
- **Control_Node**: The main ROS2 node that hosts the Trajectory_Executor, Gripper_Controller, and Robot_State_Publisher, and manages the Driver lifecycle.
- **Trajectory_Executor**: A component that accepts joint trajectories via the `ExecuteTrajectory` ROS2 action and executes them through the Driver.
- **Gripper_Controller**: A component that accepts gripper commands via the `GripperCommand` ROS2 service and executes them through the Driver.
- **Robot_State_Publisher**: A component within Control_Node that periodically publishes `RobotStateMsg` on the `/roboweave/robot_state` topic.
- **Converter**: A set of functions that translate between `roboweave_interfaces` Pydantic models and `roboweave_msgs` ROS2 message types for the control domain.
- **HardwareConfig**: A Pydantic model (from `roboweave_interfaces`) describing the full robot hardware configuration including arms, grippers, and driver types.
- **ArmConfig**: A Pydantic model describing a single arm's joint limits, velocity limits, driver type, and driver-specific configuration.
- **GripperConfig**: A Pydantic model describing a single gripper's width range, max force, driver type, and driver-specific configuration.
- **RobotStateMsg**: A ROS2 message containing the current state of all arms and grippers, the base pose, motion status, and control mode.
- **ExecuteTrajectory**: A ROS2 action defined in `roboweave_msgs` with goal (arm_id, trajectory, velocity_scaling, monitor_force), result (success, error_code, message, max_tracking_error), and feedback (progress, tracking_error, current_joint_positions).
- **GripperCommand**: A ROS2 service defined in `roboweave_msgs` with request (gripper_id, action, width, force, speed) and response (success, achieved_width, error_code, message).
- **Velocity_Scaling**: A factor in the range [0.0, 1.0] that scales the commanded joint velocities relative to the configured maximum velocities.

## Requirements

### Requirement 1: Driver Abstract Interface

**User Story:** As a robotics developer, I want a hardware-agnostic driver interface, so that I can swap between simulation and real hardware without changing the control logic.

#### Acceptance Criteria

1. THE Driver SHALL define abstract methods: `connect`, `disconnect`, `get_joint_state`, `set_joint_positions`, `get_gripper_state`, `set_gripper_width`, `set_gripper_force`, and `emergency_stop`.
2. WHEN `connect` is called, THE Driver SHALL establish a connection to the underlying hardware or simulation and return a boolean indicating success.
3. WHEN `disconnect` is called, THE Driver SHALL release all hardware or simulation resources.
4. WHEN `get_joint_state` is called with an arm_id, THE Driver SHALL return the current joint positions, velocities, and efforts for the specified arm.
5. WHEN `set_joint_positions` is called with an arm_id and a list of target joint positions, THE Driver SHALL command the arm to move toward those positions.
6. WHEN `get_gripper_state` is called with a gripper_id, THE Driver SHALL return the current width, force, and grasping status of the specified gripper.
7. WHEN `set_gripper_width` is called with a gripper_id and a target width, THE Driver SHALL command the gripper to move to the specified width.
8. WHEN `set_gripper_force` is called with a gripper_id and a target force, THE Driver SHALL set the maximum grip force for the specified gripper.
9. WHEN `emergency_stop` is called, THE Driver SHALL immediately halt all motion on all arms and grippers.
10. THE Driver SHALL accept an ArmConfig list and a GripperConfig list during initialization to configure the hardware abstraction.

### Requirement 2: Simulation Driver

**User Story:** As a robotics developer, I want a simulation driver that mimics real hardware behavior, so that I can develop and test the control stack without physical hardware.

#### Acceptance Criteria

1. THE Sim_Driver SHALL implement all abstract methods defined by the Driver interface.
2. WHEN `connect` is called, THE Sim_Driver SHALL initialize simulated joint states for each configured arm to zero positions and simulated gripper states for each configured gripper to the maximum width.
3. WHEN `set_joint_positions` is called, THE Sim_Driver SHALL simulate joint motion by interpolating from the current positions toward the target positions at a rate limited by the configured maximum joint velocities from ArmConfig.
4. WHEN `set_gripper_width` is called, THE Sim_Driver SHALL simulate gripper motion by interpolating from the current width toward the target width over a configurable duration.
5. WHEN `get_joint_state` is called, THE Sim_Driver SHALL return the current simulated joint positions, zero velocities when stationary, and zero efforts.
6. WHEN `get_gripper_state` is called, THE Sim_Driver SHALL return the current simulated width, the last commanded force, and a grasping status of false.
7. WHEN `emergency_stop` is called, THE Sim_Driver SHALL immediately set all simulated joint velocities to zero and stop all in-progress motions.
8. IF `set_joint_positions` is called with positions outside the joint limits defined in ArmConfig, THEN THE Sim_Driver SHALL clamp the target positions to the joint limits.
9. IF `set_gripper_width` is called with a width outside the range [GripperConfig.min_width, GripperConfig.max_width], THEN THE Sim_Driver SHALL clamp the target width to the valid range.
10. IF `set_gripper_force` is called with a force exceeding GripperConfig.max_force, THEN THE Sim_Driver SHALL clamp the force to GripperConfig.max_force.

### Requirement 3: Trajectory Executor

**User Story:** As a skill developer, I want to send joint trajectories to the robot via a ROS2 action, so that I can execute planned motions with progress feedback and cancellation support.

#### Acceptance Criteria

1. THE Trajectory_Executor SHALL host a ROS2 action server for the `ExecuteTrajectory` action on the `/roboweave/control/execute_trajectory` endpoint.
2. WHEN an ExecuteTrajectory goal is received, THE Trajectory_Executor SHALL execute the joint trajectory points sequentially through the Driver using the specified arm_id.
3. WHILE executing a trajectory, THE Trajectory_Executor SHALL publish feedback containing the execution progress as a fraction in [0.0, 1.0], the current tracking error in radians, and the current joint positions.
4. WHEN trajectory execution completes successfully, THE Trajectory_Executor SHALL return a result with `success=true` and the maximum tracking error observed during execution.
5. THE Trajectory_Executor SHALL apply the velocity_scaling factor from the goal to scale the commanded velocities, clamping the factor to the range [0.0, 1.0].
6. WHEN a cancel request is received during trajectory execution, THE Trajectory_Executor SHALL stop the current motion via the Driver and return a result with `success=false` and error_code `CTL_CANCELLED`.
7. IF the tracking error exceeds a configurable threshold during execution, THEN THE Trajectory_Executor SHALL abort the trajectory and return a result with `success=false` and error_code `CTL_TRACKING_ERROR`.
8. IF the Driver reports a failure during trajectory execution, THEN THE Trajectory_Executor SHALL abort the trajectory and return a result with the corresponding error_code from the Driver.
9. WHILE a trajectory is already executing for a given arm_id, THE Trajectory_Executor SHALL reject new goals for the same arm_id with an appropriate error message.

### Requirement 4: Gripper Controller

**User Story:** As a skill developer, I want to command the gripper via a ROS2 service, so that I can open, close, or set the gripper to a specific width during task execution.

#### Acceptance Criteria

1. THE Gripper_Controller SHALL host a ROS2 service server for the `GripperCommand` service on the `/roboweave/control/gripper_command` endpoint.
2. WHEN a GripperCommand request with action `open` is received, THE Gripper_Controller SHALL command the Driver to move the specified gripper to its maximum width from GripperConfig.
3. WHEN a GripperCommand request with action `close` is received, THE Gripper_Controller SHALL command the Driver to move the specified gripper to its minimum width from GripperConfig.
4. WHEN a GripperCommand request with action `move_to_width` is received, THE Gripper_Controller SHALL command the Driver to move the specified gripper to the requested width.
5. WHEN a GripperCommand request includes a non-zero force value, THE Gripper_Controller SHALL command the Driver to set the grip force before executing the width command.
6. WHEN the gripper command completes, THE Gripper_Controller SHALL return a response with `success=true` and the achieved width as reported by the Driver.
7. IF the specified gripper_id does not match any configured gripper, THEN THE Gripper_Controller SHALL return a response with `success=false` and error_code `CTL_GRIPPER_FAILED`.
8. IF an unrecognized action string is received, THEN THE Gripper_Controller SHALL return a response with `success=false`, error_code `CTL_GRIPPER_FAILED`, and a message indicating the valid actions.

### Requirement 5: Robot State Publisher

**User Story:** As a system integrator, I want the control node to publish the robot's current state at a configurable rate, so that other nodes (world model, safety supervisor, data recorder) can consume up-to-date robot state.

#### Acceptance Criteria

1. THE Robot_State_Publisher SHALL publish `RobotStateMsg` on the `/roboweave/robot_state` topic.
2. THE Robot_State_Publisher SHALL query the Driver for the current state of all configured arms and grippers at a configurable publish rate (default 50 Hz).
3. WHEN the Driver reports joint positions, velocities, and efforts for an arm, THE Robot_State_Publisher SHALL populate the corresponding ArmState fields in the RobotStateMsg.
4. WHEN the Driver reports width, force, and grasping status for a gripper, THE Robot_State_Publisher SHALL populate the corresponding GripperState fields in the RobotStateMsg.
5. THE Robot_State_Publisher SHALL set the `is_moving` field to true WHEN any arm joint velocity magnitude exceeds a configurable threshold (default 0.01 rad/s).
6. THE Robot_State_Publisher SHALL set the `current_control_mode` field to the active control mode of the Control_Node.

### Requirement 6: Control Node Lifecycle

**User Story:** As a system integrator, I want a single ROS2 node that initializes the driver, hosts all control services, and manages configuration, so that I can launch the control subsystem with a single command.

#### Acceptance Criteria

1. THE Control_Node SHALL load HardwareConfig from a YAML file path specified by a ROS2 parameter.
2. THE Control_Node SHALL instantiate the appropriate Driver implementation based on the `driver_type` field in the loaded ArmConfig (e.g., `sim` instantiates Sim_Driver).
3. WHEN the Control_Node starts, THE Control_Node SHALL call `connect` on the Driver and log the connection status.
4. WHEN the Control_Node shuts down, THE Control_Node SHALL call `disconnect` on the Driver to release resources.
5. THE Control_Node SHALL instantiate and host the Trajectory_Executor, Gripper_Controller, and Robot_State_Publisher as sub-components.
6. THE Control_Node SHALL expose the publish rate and default velocity scaling as configurable ROS2 parameters.
7. IF the Driver fails to connect during startup, THEN THE Control_Node SHALL log an error and shut down gracefully.

### Requirement 7: Pydantic ↔ ROS2 Message Converters

**User Story:** As a developer, I want reliable conversion functions between Pydantic models and ROS2 messages for control types, so that the control node can interoperate with both the Pydantic-based interfaces package and the ROS2 message layer.

#### Acceptance Criteria

1. THE Converter SHALL provide a function to convert a `roboweave_interfaces.hardware.ArmConfig` Pydantic model to and from a dictionary representation suitable for YAML loading.
2. THE Converter SHALL provide a function to convert a `roboweave_interfaces.hardware.GripperConfig` Pydantic model to and from a dictionary representation suitable for YAML loading.
3. THE Converter SHALL provide a function to convert a `roboweave_interfaces.control.ControlCommand` Pydantic model to a `roboweave_msgs/msg` equivalent and vice versa.
4. THE Converter SHALL provide a function to convert a `roboweave_interfaces.control.ControlStatus` Pydantic model to a `roboweave_msgs/msg` equivalent and vice versa.
5. THE Converter SHALL provide functions to build `RobotStateMsg`, `ArmState`, and `GripperState` ROS2 messages from the corresponding Pydantic models in `roboweave_interfaces`.
6. FOR ALL valid Pydantic control models, converting to a ROS2 message and back SHALL produce an equivalent Pydantic model (round-trip property).

### Requirement 8: Configuration Files

**User Story:** As a system integrator, I want well-defined YAML configuration files for control parameters and simulated hardware, so that I can tune the control subsystem without code changes.

#### Acceptance Criteria

1. THE control_params.yaml file SHALL define the robot state publish rate in Hz, the default velocity scaling factor, and the tracking error threshold.
2. THE sim_arm.yaml file SHALL define a simulated arm configuration conforming to the ArmConfig schema, including arm_id, joint names, joint limits, max velocities, and driver_type set to `sim`.
3. THE sim_gripper.yaml file SHALL define a simulated gripper configuration conforming to the GripperConfig schema, including gripper_id, width range, max force, and driver_type set to `sim`.
4. THE Control_Node SHALL accept a ROS2 parameter specifying the path to the hardware configuration YAML file.
5. THE Control_Node SHALL accept ROS2 parameters that override values from control_params.yaml at launch time.

### Requirement 9: Launch File

**User Story:** As a system integrator, I want a ROS2 launch file that starts the control node with configurable parameters, so that I can integrate the control subsystem into the full system launch.

#### Acceptance Criteria

1. THE control.launch.py file SHALL launch the Control_Node with default parameters from control_params.yaml.
2. THE control.launch.py file SHALL accept launch arguments for the hardware config file path, publish rate, and default velocity scaling.
3. WHEN launch arguments are provided, THE control.launch.py file SHALL pass them as ROS2 parameter overrides to the Control_Node.
