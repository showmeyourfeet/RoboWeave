# Requirements Document — roboweave_safety (Phase 1.2)

## Introduction

The `roboweave_safety` package is an independent ROS2 safety supervisor that runs as a separate process within the RoboWeave hybrid robotics system. It implements Layer 2 (execution-level safety) of the four-layer safety architecture defined in the architecture spec Section 7. The package monitors robot state in real time, enforces velocity/force/torque/workspace limits, manages emergency stop semantics, and filters VLA actions before execution. It depends only on `roboweave_interfaces` (pure Python models) and `roboweave_msgs` (ROS2 messages) — it does NOT depend on `roboweave_runtime`, ensuring it continues to function even if the runtime, cloud agent, or other nodes crash.

## Glossary

- **Safety_Supervisor_Node**: The top-level ROS2 node (`SafetySupervisorNode`) running as an independent process. Publishes safety status, hosts safety control and VLA filter services, and subscribes to robot state.
- **Safety_Monitor**: The component responsible for real-time monitoring of velocity, force/torque, and workspace limits against the incoming robot state.
- **Safety_Guard**: The component managing emergency stop (latched), safe mode (auto-recoverable), and the safety level state machine (NORMAL → WARNING → CRITICAL → EMERGENCY_STOP).
- **VLA_Safety_Filter**: The component that filters VLA actions before execution by clamping velocities/forces, checking workspace boundaries, and verifying confidence thresholds.
- **Safety_Level**: An enumeration of safety states: NORMAL, WARNING, CRITICAL, EMERGENCY_STOP — as defined in `roboweave_interfaces.safety.SafetyLevel`.
- **Emergency_Stop**: A latched safety state where all robot motion is halted immediately. Requires explicit release via `release_stop` with an `operator_id`.
- **Safe_Mode**: A non-latched safety state where the robot operates at reduced speed and new tasks are prohibited. Auto-recovers when violations clear.
- **Workspace_Limits**: Axis-aligned bounding box defining the allowed operational volume for the end-effector, as defined in `roboweave_interfaces.safety.WorkspaceLimits`.
- **Heartbeat**: A periodically updated timestamp (`last_heartbeat`) in the `SafetyStatus` message indicating the Safety_Supervisor_Node is alive.
- **Robot_State**: The `RobotStateMsg` published on `/roboweave/robot_state`, containing joint positions, velocities, efforts, and end-effector poses for all arms.
- **VLA_Action**: A single action output from a VLA model, as defined in `roboweave_interfaces.vla.VLAAction`.
- **VLA_Safety_Constraints**: Safety constraints applied to VLA actions, as defined in `roboweave_interfaces.vla.VLASafetyConstraints`.
- **Safety_Config**: Configuration parameters for the safety supervisor, as defined in `roboweave_interfaces.safety.SafetyConfig`.
- **Safety_Event**: A structured event raised when a safety violation occurs, as defined in `roboweave_interfaces.safety.SafetyEvent`.
- **Operator_ID**: A string identifier for the human operator performing safety-critical actions such as releasing an emergency stop, used for audit logging.

## Requirements

### Requirement 1: Safety Status Publishing

**User Story:** As a system integrator, I want the Safety_Supervisor_Node to continuously publish its safety status, so that all other nodes can monitor the current safety level and react accordingly.

#### Acceptance Criteria

1. THE Safety_Supervisor_Node SHALL publish `SafetyStatus` messages on the `/roboweave/safety/status` topic at a configurable rate (default 10 Hz).
2. THE Safety_Supervisor_Node SHALL include the current Safety_Level, emergency stop state (`e_stop_active`, `e_stop_latched`), list of active violations, list of active safe zones, and the `last_heartbeat` timestamp in each `SafetyStatus` message.
3. THE Safety_Supervisor_Node SHALL use QoS profile Reliable, depth=1, Transient Local for the `/roboweave/safety/status` topic.
4. THE Safety_Supervisor_Node SHALL update the `last_heartbeat` field with the current ROS2 time on every publish cycle.

### Requirement 2: Robot State Subscription and Watchdog

**User Story:** As a safety engineer, I want the Safety_Supervisor_Node to monitor incoming robot state and detect communication loss, so that the system escalates to a warning when state data stops arriving.

#### Acceptance Criteria

1. THE Safety_Supervisor_Node SHALL subscribe to the `/roboweave/robot_state` topic to receive `RobotStateMsg` messages.
2. WHEN a `RobotStateMsg` is received, THE Safety_Monitor SHALL validate the message against configured safety limits.
3. IF no `RobotStateMsg` is received within a configurable watchdog timeout (default 500 ms), THEN THE Safety_Monitor SHALL escalate the Safety_Level to WARNING and add a "robot_state_timeout" entry to the active violations list.
4. WHEN `RobotStateMsg` messages resume after a watchdog timeout, THE Safety_Monitor SHALL clear the "robot_state_timeout" violation.

### Requirement 3: Velocity Limit Checking

**User Story:** As a safety engineer, I want the Safety_Monitor to check joint and end-effector velocities against configured limits, so that over-speed conditions are detected and reported.

#### Acceptance Criteria

1. WHEN a `RobotStateMsg` is received, THE Safety_Monitor SHALL compare each joint velocity in each arm against the corresponding per-joint velocity limit from Safety_Config.`max_joint_velocity`.
2. WHEN a `RobotStateMsg` is received, THE Safety_Monitor SHALL compute the end-effector linear velocity magnitude and compare it against Safety_Config.`max_eef_velocity`.
3. WHEN a `RobotStateMsg` is received, THE Safety_Monitor SHALL compute the end-effector angular velocity magnitude and compare it against Safety_Config.`max_eef_angular_velocity`.
4. IF any velocity exceeds its configured limit, THEN THE Safety_Monitor SHALL raise a Safety_Event with `violation_type` "velocity_exceeded" and escalate the Safety_Level according to the state machine rules.

### Requirement 4: Force and Torque Limit Checking

**User Story:** As a safety engineer, I want the Safety_Monitor to check joint efforts against configured force and torque limits, so that excessive contact forces are detected.

#### Acceptance Criteria

1. WHEN a `RobotStateMsg` is received, THE Safety_Monitor SHALL compare each joint effort against Safety_Config.`torque_limit`.
2. IF any joint effort exceeds the configured torque limit, THEN THE Safety_Monitor SHALL raise a Safety_Event with `violation_type` "torque_exceeded" and escalate the Safety_Level according to the state machine rules.
3. THE Safety_Monitor SHALL log every force/torque violation as a Safety_Event with the violating joint identifier, measured value, and configured limit.

### Requirement 5: Workspace Boundary Checking

**User Story:** As a safety engineer, I want the Safety_Monitor to verify that the end-effector remains within the configured workspace boundaries, so that out-of-bounds motion is detected.

#### Acceptance Criteria

1. WHEN a `RobotStateMsg` is received, THE Safety_Monitor SHALL check each arm's end-effector position against the configured Workspace_Limits (x_min, x_max, y_min, y_max, z_min, z_max).
2. IF any end-effector position component falls outside the configured Workspace_Limits, THEN THE Safety_Monitor SHALL raise a Safety_Event with `violation_type` "workspace_violation" and escalate the Safety_Level according to the state machine rules.
3. THE Safety_Monitor SHALL load Workspace_Limits from the `workspace_limits.yaml` configuration file at startup.

### Requirement 6: Safety Level State Machine

**User Story:** As a system integrator, I want the Safety_Guard to manage safety level transitions through a well-defined state machine, so that the system responds proportionally to the severity of violations.

#### Acceptance Criteria

1. THE Safety_Guard SHALL maintain a safety level state machine with states: NORMAL, WARNING, CRITICAL, EMERGENCY_STOP.
2. THE Safety_Guard SHALL support the following transitions: NORMAL → WARNING, WARNING → CRITICAL, CRITICAL → EMERGENCY_STOP, WARNING → NORMAL (when violations clear), CRITICAL → WARNING (when violations clear), and EMERGENCY_STOP → NORMAL (only via explicit `release_stop`).
3. WHEN a safety violation is raised, THE Safety_Guard SHALL transition the Safety_Level upward based on the violation severity.
4. THE Safety_Guard SHALL prohibit direct transitions that skip levels in the upward direction (NORMAL cannot transition directly to EMERGENCY_STOP without passing through WARNING and CRITICAL), except when an emergency stop is explicitly triggered via the SafetyControl service.
5. WHEN an explicit `emergency_stop` command is received via the SafetyControl service, THE Safety_Guard SHALL transition immediately to EMERGENCY_STOP regardless of the current state.

### Requirement 7: Emergency Stop Management

**User Story:** As an operator, I want the emergency stop to be latched so that the robot cannot resume motion until I explicitly confirm it is safe, providing an auditable record of who released the stop.

#### Acceptance Criteria

1. WHEN an `emergency_stop` action is received via the SafetyControl service, THE Safety_Guard SHALL immediately set `e_stop_active` to true and `e_stop_latched` to true.
2. WHILE `e_stop_latched` is true, THE Safety_Guard SHALL reject all motion-related commands and maintain the EMERGENCY_STOP Safety_Level.
3. WHEN a `release_stop` action is received via the SafetyControl service, THE Safety_Guard SHALL verify that the request includes a non-empty `operator_id`.
4. IF a `release_stop` request does not include a non-empty `operator_id`, THEN THE Safety_Guard SHALL reject the request and return `success=false` with a descriptive message.
5. WHEN a valid `release_stop` action is received, THE Safety_Guard SHALL set `e_stop_active` to false, set `e_stop_latched` to false, transition the Safety_Level to NORMAL, and log the release event with the Operator_ID.
6. THE Safety_Guard SHALL log every emergency stop activation and release as a Safety_Event including the Operator_ID and timestamp.

### Requirement 8: Safe Mode Management

**User Story:** As a system integrator, I want the Safety_Guard to support an auto-recoverable safe mode, so that the system can reduce operational capability during minor violations and automatically resume normal operation when conditions improve.

#### Acceptance Criteria

1. WHEN an `enter_safe_mode` action is received via the SafetyControl service, THE Safety_Guard SHALL transition the Safety_Level to WARNING.
2. WHILE the Safety_Level is WARNING due to safe mode, THE Safety_Guard SHALL indicate reduced operational capability in the SafetyStatus active_violations list.
3. WHEN all active violations are cleared while in safe mode, THE Safety_Guard SHALL automatically transition the Safety_Level back to NORMAL.

### Requirement 9: SafetyControl Service

**User Story:** As a system integrator, I want a service interface to control safety parameters at runtime, so that operators and other nodes can trigger emergency stops, release stops, and adjust safety limits.

#### Acceptance Criteria

1. THE Safety_Supervisor_Node SHALL host the SafetyControl service on `/roboweave/safety/control`.
2. THE SafetyControl service SHALL support the following actions: `emergency_stop`, `release_stop`, `enter_safe_mode`, `set_speed_limit`, `set_force_limit`, `set_workspace`.
3. WHEN a `set_speed_limit` action is received, THE Safety_Supervisor_Node SHALL update the active velocity limits using the parameters provided in `params_json`.
4. WHEN a `set_force_limit` action is received, THE Safety_Supervisor_Node SHALL update the active force and torque limits using the parameters provided in `params_json`.
5. WHEN a `set_workspace` action is received, THE Safety_Supervisor_Node SHALL update the active Workspace_Limits using the parameters provided in `params_json`.
6. IF an unrecognized action is received, THEN THE SafetyControl service SHALL return `success=false` with a message describing the supported actions.

### Requirement 10: VLA Action Filtering — Velocity and Force Clamping

**User Story:** As a safety engineer, I want the VLA_Safety_Filter to clamp VLA action velocities and forces to safe limits, so that VLA models cannot command unsafe motions.

#### Acceptance Criteria

1. THE Safety_Supervisor_Node SHALL host the FilterVLAAction service on `/roboweave/safety/filter_vla_action`.
2. WHEN a FilterVLAAction request is received, THE VLA_Safety_Filter SHALL deserialize the `vla_action_json` and `safety_constraints_json` fields from JsonEnvelope format.
3. WHEN the VLA_Action contains a `delta_pose` with a linear magnitude exceeding VLA_Safety_Constraints.`max_velocity` scaled by the control period, THE VLA_Safety_Filter SHALL clamp the delta to the maximum allowed magnitude while preserving direction.
4. WHEN the VLA_Action contains joint deltas exceeding safe limits, THE VLA_Safety_Filter SHALL clamp each joint delta to the maximum allowed value while preserving sign.
5. THE VLA_Safety_Filter SHALL return `approved=true` with the clamped action in `filtered_action_json` when clamping is sufficient to bring the action within safe limits.

### Requirement 11: VLA Action Filtering — Workspace Boundary Check

**User Story:** As a safety engineer, I want the VLA_Safety_Filter to reject VLA actions that would move the end-effector outside the workspace boundary, so that workspace violations are prevented before execution.

#### Acceptance Criteria

1. WHEN a FilterVLAAction request is received, THE VLA_Safety_Filter SHALL compute the resulting end-effector position after applying the VLA_Action.
2. IF the resulting end-effector position falls outside the configured Workspace_Limits, THEN THE VLA_Safety_Filter SHALL return `approved=false` with `rejection_reason` describing the boundary violation and `violation_type` set to "workspace_violation".
3. WHEN the VLA_Safety_Filter uses workspace limits, THE VLA_Safety_Filter SHALL use the workspace identified by VLA_Safety_Constraints.`workspace_limit_id`, falling back to the default workspace if the ID is empty.

### Requirement 12: VLA Action Filtering — Confidence Threshold Check

**User Story:** As a safety engineer, I want the VLA_Safety_Filter to reject VLA actions with low confidence scores, so that uncertain model predictions do not reach the robot.

#### Acceptance Criteria

1. WHEN a FilterVLAAction request is received, THE VLA_Safety_Filter SHALL compare the VLA_Action.`confidence` against VLA_Safety_Constraints.`min_confidence_threshold`.
2. IF the VLA_Action.`confidence` is below VLA_Safety_Constraints.`min_confidence_threshold`, THEN THE VLA_Safety_Filter SHALL return `approved=false` with `rejection_reason` describing the low confidence and `violation_type` set to "confidence_below_threshold".

### Requirement 13: Safety Event Logging

**User Story:** As a safety auditor, I want all safety events to be logged with structured information, so that safety incidents can be reviewed and analyzed.

#### Acceptance Criteria

1. THE Safety_Supervisor_Node SHALL log every Safety_Event with the event_id, safety_level, violation_type, message, and timestamp.
2. THE Safety_Supervisor_Node SHALL log every SafetyControl service call with the action, operator_id (if provided), and result.
3. THE Safety_Supervisor_Node SHALL log every VLA action filter decision with the approval status, violation_type (if rejected), and arm_id.
4. THE Safety_Supervisor_Node SHALL use the ROS2 logging infrastructure (rclpy logger) for all safety event logs at appropriate severity levels (INFO for normal operations, WARN for warnings, ERROR for critical events).

### Requirement 14: Configuration Loading

**User Story:** As a system integrator, I want the Safety_Supervisor_Node to load safety parameters and workspace limits from YAML configuration files, so that safety thresholds can be tuned per deployment without code changes.

#### Acceptance Criteria

1. THE Safety_Supervisor_Node SHALL load safety parameters from a `safety_params.yaml` configuration file at startup.
2. THE Safety_Supervisor_Node SHALL load workspace limit definitions from a `workspace_limits.yaml` configuration file at startup.
3. IF a configuration file is missing or contains invalid values, THEN THE Safety_Supervisor_Node SHALL use the default values defined in Safety_Config and Workspace_Limits and log a warning.
4. THE Safety_Supervisor_Node SHALL accept configuration file paths as ROS2 parameters, allowing override via launch files.

### Requirement 15: Independence Guarantee

**User Story:** As a safety architect, I want the Safety_Supervisor_Node to operate independently of all other RoboWeave nodes, so that safety monitoring continues even if the runtime, cloud agent, or other nodes crash.

#### Acceptance Criteria

1. THE Safety_Supervisor_Node SHALL run as a separate ROS2 process, not co-located with any other RoboWeave node.
2. THE Safety_Supervisor_Node SHALL depend only on `roboweave_interfaces` and `roboweave_msgs` as Python/ROS2 dependencies, and SHALL NOT depend on `roboweave_runtime`.
3. IF the Safety_Supervisor_Node loses communication with all other nodes, THEN THE Safety_Supervisor_Node SHALL continue publishing SafetyStatus messages with the watchdog timeout violation active.
4. THE Safety_Supervisor_Node SHALL maintain its safety level state machine and emergency stop state independently of any external node lifecycle.

### Requirement 16: SafetyConfig and VLASafetyConstraints Serialization Round-Trip

**User Story:** As a developer, I want safety configuration and VLA constraint objects to survive serialization and deserialization without data loss, so that configuration values are faithfully transmitted across ROS2 service boundaries.

#### Acceptance Criteria

1. FOR ALL valid Safety_Config objects, serializing to JSON via JsonEnvelope and deserializing back SHALL produce an equivalent Safety_Config object (round-trip property).
2. FOR ALL valid VLA_Safety_Constraints objects, serializing to JSON via JsonEnvelope and deserializing back SHALL produce an equivalent VLA_Safety_Constraints object (round-trip property).
3. FOR ALL valid VLA_Action objects, serializing to JSON via JsonEnvelope and deserializing back SHALL produce an equivalent VLA_Action object (round-trip property).
