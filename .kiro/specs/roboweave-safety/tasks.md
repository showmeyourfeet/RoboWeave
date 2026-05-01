# Implementation Plan: roboweave_safety (Phase 1.2)

## Overview

Implement the independent safety supervisor package as an ament_python ROS2 package. The implementation proceeds bottom-up: package scaffolding → pure Python components (SafetyMonitor, SafetyGuard, VLASafetyFilter) → ROS2 msg↔Pydantic converters → ROS2 node wiring → configuration files → launch file. Property-based tests validate the 13 correctness properties from the design; unit and integration tests cover remaining requirements.

## Tasks

- [ ] 1. Scaffold the roboweave_safety ament_python package
  - [x] 1.1 Create package structure with setup.py, setup.cfg, package.xml, and resource marker
    - Create `roboweave_safety/` top-level directory with `setup.py`, `setup.cfg`, `package.xml`
    - Create `roboweave_safety/roboweave_safety/__init__.py`
    - Create `roboweave_safety/resource/roboweave_safety` (empty ament resource index marker)
    - `package.xml` must declare dependencies on `roboweave_msgs`, `rclpy`, `std_msgs`, `geometry_msgs` and exec_depend on `roboweave_interfaces`
    - `setup.py` must register the `safety_supervisor` console_scripts entry point and include `config/` and `launch/` data files
    - _Requirements: 15.1, 15.2_

  - [x] 1.2 Create test directory skeleton
    - Create `roboweave_safety/tests/__init__.py`
    - Create empty test files: `test_safety_monitor.py`, `test_safety_guard.py`, `test_vla_safety_filter.py`, `test_converters.py`, `test_serialization.py`
    - _Requirements: 15.2_

- [ ] 2. Implement SafetyMonitor (pure Python)
  - [x] 2.1 Implement SafetyMonitor class with velocity, force/torque, and workspace checks
    - Create `roboweave_safety/roboweave_safety/safety_monitor.py`
    - Implement `__init__(self, config: SafetyConfig, workspace: WorkspaceLimits)`
    - Implement `check(self, arms: list[ArmState]) -> list[SafetyEvent]` that delegates to the three check methods
    - Implement `check_velocity(self, arm: ArmState) -> list[SafetyEvent]`: compare each joint velocity against `config.max_joint_velocity[i]`, compute EEF linear velocity magnitude against `config.max_eef_velocity`, compute EEF angular velocity magnitude against `config.max_eef_angular_velocity`; return `SafetyEvent(violation_type="velocity_exceeded")` for each violation
    - Implement `check_force_torque(self, arm: ArmState) -> list[SafetyEvent]`: compare each joint effort against `config.torque_limit`; return `SafetyEvent(violation_type="torque_exceeded")` with joint identifier, measured value, and limit in the message
    - Implement `check_workspace(self, arm: ArmState) -> list[SafetyEvent]`: check EEF position `[x, y, z]` against `WorkspaceLimits` bounds; return `SafetyEvent(violation_type="workspace_violation")` if any axis is out of bounds
    - Implement `update_config(self, config: SafetyConfig)` and `update_workspace(self, workspace: WorkspaceLimits)` for runtime updates
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 5.1, 5.2, 9.3, 9.4, 9.5_

  - [ ]* 2.2 Write property test: Velocity violation detection (Property 1)
    - **Property 1: Velocity violation detection**
    - Use Hypothesis to generate random `ArmState` with joint velocities in `[-10, 10]` rad/s and random `SafetyConfig` with positive velocity limits
    - Assert `check_velocity` returns a violation iff at least one joint velocity magnitude exceeds its limit, or EEF linear velocity exceeds `max_eef_velocity`, or EEF angular velocity exceeds `max_eef_angular_velocity`
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4**

  - [ ]* 2.3 Write property test: Torque violation detection (Property 2)
    - **Property 2: Torque violation detection**
    - Use Hypothesis to generate random `ArmState` with joint efforts in `[-100, 100]` Nm and random positive `torque_limit`
    - Assert `check_force_torque` returns a violation iff at least one joint effort magnitude exceeds `torque_limit`
    - **Validates: Requirements 4.1, 4.2**

  - [ ]* 2.4 Write property test: Workspace violation detection (Property 3)
    - **Property 3: Workspace violation detection**
    - Use Hypothesis to generate random EEF position in `[-5, 5]` m per axis and random `WorkspaceLimits` with valid `min < max`
    - Assert `check_workspace` returns a violation iff any position component falls outside bounds
    - **Validates: Requirements 5.1, 5.2**

  - [ ]* 2.5 Write property test: Runtime limit updates take effect (Property 8)
    - **Property 8: Runtime limit updates take effect**
    - Use Hypothesis to generate a valid config update, apply it via `update_config`, then generate a random `ArmState` and verify `check()` uses the updated limits
    - **Validates: Requirements 9.3, 9.4, 9.5**

  - [ ]* 2.6 Write unit tests for SafetyMonitor
    - Test force/torque violation event contains joint ID, measured value, and configured limit in the message (Req 4.3)
    - Test that `check()` aggregates violations from all three check methods
    - Test edge cases: empty joint lists, zero limits, exactly-at-limit values
    - _Requirements: 3.1–3.4, 4.1–4.3, 5.1–5.2_

- [ ] 3. Implement SafetyGuard (pure Python)
  - [x] 3.1 Implement SafetyGuard class with state machine, e-stop, and safe mode
    - Create `roboweave_safety/roboweave_safety/safety_guard.py`
    - Implement `__init__` initializing `_level=NORMAL`, `_e_stop_active=False`, `_e_stop_latched=False`, `_active_violations=[]`
    - Expose read-only properties: `level`, `e_stop_active`, `e_stop_latched`, `active_violations`
    - Implement `process_violations(violations: list[SafetyEvent]) -> SafetyLevel`: escalate one level per violation severity, track consecutive violation counts for escalation (WARNING→CRITICAL after 2 consecutive, CRITICAL→EMERGENCY_STOP after 3 consecutive workspace violations)
    - Implement `emergency_stop()`: immediately set level to EMERGENCY_STOP, `e_stop_active=True`, `e_stop_latched=True`
    - Implement `release_stop(operator_id: str) -> tuple[bool, str]`: validate non-empty `operator_id` (stripped), reset e-stop state and level to NORMAL; return `(False, message)` if operator_id is empty/whitespace
    - Implement `enter_safe_mode()`: transition to WARNING, add safe mode indicator to active violations
    - Implement `clear_violations() -> SafetyLevel`: clear violations, auto-recover (WARNING→NORMAL, CRITICAL→WARNING) unless e-stop is latched
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 8.1, 8.2, 8.3_

  - [ ]* 3.2 Write property test: State machine valid transitions (Property 4)
    - **Property 4: State machine valid transitions**
    - Use Hypothesis to generate random sequences of `(violation_severity, clear)` events (length 1–50)
    - Assert the state machine only moves at most one level upward per violation event and downward only when violations are cleared; never skips levels upward from violations alone
    - **Validates: Requirements 6.2, 6.3, 6.4**

  - [ ]* 3.3 Write property test: Explicit emergency stop from any state (Property 5)
    - **Property 5: Explicit emergency stop from any state**
    - Use Hypothesis to generate a random starting `SafetyLevel`
    - Assert `emergency_stop()` always transitions to EMERGENCY_STOP with `e_stop_active=True` and `e_stop_latched=True`
    - **Validates: Requirements 6.5, 7.1**

  - [ ]* 3.4 Write property test: Latched e-stop invariant (Property 6)
    - **Property 6: Latched e-stop invariant**
    - Use Hypothesis to generate random event sequences (length 1–20) while `e_stop_latched=True`
    - Assert the guard maintains EMERGENCY_STOP and `e_stop_active=True` throughout; only `release_stop` with valid operator_id can change state
    - **Validates: Requirements 7.2**

  - [ ]* 3.5 Write property test: Release stop requires operator_id (Property 7)
    - **Property 7: Release stop requires operator_id and resets state**
    - Use Hypothesis to generate random strings including empty, whitespace-only, and valid operator IDs
    - Assert `release_stop` returns `(True, ...)` and resets state iff operator_id is non-empty after stripping; returns `(False, ...)` and leaves state unchanged otherwise
    - **Validates: Requirements 7.3, 7.4, 7.5**

  - [ ]* 3.6 Write unit tests for SafetyGuard
    - Test state machine has all four SafetyLevel states (Req 6.1)
    - Test e-stop activation and release are logged as SafetyEvent (Req 7.6)
    - Test safe mode enters WARNING and auto-recovers on clear (Req 8.1, 8.2, 8.3)
    - Test explicit e-stop from each starting state
    - _Requirements: 6.1–6.5, 7.1–7.6, 8.1–8.3_

- [x] 4. Checkpoint — Verify pure Python components
  - Ensure all tests pass for SafetyMonitor and SafetyGuard, ask the user if questions arise.

- [ ] 5. Implement VLASafetyFilter (pure Python)
  - [x] 5.1 Implement VLASafetyFilter class with clamping and rejection pipeline
    - Create `roboweave_safety/roboweave_safety/vla_safety_filter.py`
    - Implement `__init__(self, config: SafetyConfig, default_workspace: WorkspaceLimits, guard: SafetyGuard, workspaces: dict[str, WorkspaceLimits] | None = None)`
    - Implement `filter_action(self, action: VLAAction, constraints: VLASafetyConstraints, arm_id: str, current_eef_pose: SE3 | None = None) -> tuple[bool, VLAAction | None, str, str]`
    - Filter pipeline in order: (1) e-stop check → reject if `guard.e_stop_active`, (2) confidence check → reject if `action.confidence < constraints.min_confidence_threshold`, (3) velocity clamping → clamp `delta_pose` linear magnitude to `max_velocity / control_frequency_hz` preserving direction; clamp each joint delta to `max_joint_delta` preserving sign, (4) workspace check → compute resulting EEF position and reject if outside bounds, (5) approve with clamped action
    - Implement workspace selection: use `constraints.workspace_limit_id` to look up workspace, fall back to `default_workspace` if ID is empty or not found
    - _Requirements: 10.1–10.5, 11.1–11.3, 12.1–12.2_

  - [ ]* 5.2 Write property test: VLA delta_pose clamping preserves direction (Property 9)
    - **Property 9: VLA delta_pose clamping preserves direction**
    - Use Hypothesis to generate random 3D displacement vectors with magnitudes in `[0, 1]` m and random velocity limits
    - Assert clamped magnitude equals `max_velocity / control_frequency_hz` when original exceeds limit, and direction (unit vector) is preserved; unchanged when within limit
    - **Validates: Requirements 10.3**

  - [ ]* 5.3 Write property test: VLA joint delta clamping preserves sign (Property 10)
    - **Property 10: VLA joint delta clamping preserves sign**
    - Use Hypothesis to generate random joint delta arrays (length 1–10, values in `[-1, 1]` rad) and a positive `max_joint_delta`
    - Assert each output `abs(output[i]) <= max_joint_delta` and `sign(output[i]) == sign(input[i])`; unchanged when within limit
    - **Validates: Requirements 10.4**

  - [ ]* 5.4 Write property test: VLA workspace rejection (Property 11)
    - **Property 11: VLA workspace rejection**
    - Use Hypothesis to generate random `(current_pose, delta_pose)` pairs and random `WorkspaceLimits`
    - Assert `approved=False` with `violation_type="workspace_violation"` iff resulting position falls outside bounds on any axis
    - **Validates: Requirements 11.1, 11.2**

  - [ ]* 5.5 Write property test: VLA confidence rejection (Property 12)
    - **Property 12: VLA confidence rejection**
    - Use Hypothesis to generate random confidence in `[0, 1]` and random threshold in `[0, 1]`
    - Assert `approved=False` with `violation_type="confidence_below_threshold"` iff `confidence < threshold`
    - **Validates: Requirements 12.1, 12.2**

  - [ ]* 5.6 Write unit tests for VLASafetyFilter
    - Test e-stop rejection returns `approved=False` with reason "emergency_stop_active"
    - Test workspace selection by ID with fallback to default (Req 11.3)
    - Test all SafetyControl actions are recognized (Req 9.2)
    - Test unrecognized action returns `success=false` (Req 9.6)
    - Test invalid VLAAction JSON returns `approved=False` with `rejection_reason="deserialization_error"`
    - _Requirements: 9.2, 9.6, 10.1–10.5, 11.1–11.3, 12.1–12.2_

- [x] 6. Checkpoint — Verify VLASafetyFilter
  - Ensure all tests pass for VLASafetyFilter, ask the user if questions arise.

- [ ] 7. Implement converters and serialization round-trip
  - [x] 7.1 Implement ROS2 msg ↔ Pydantic converters
    - Create `roboweave_safety/roboweave_safety/converters.py`
    - Implement `robot_state_msg_to_arms(msg: RobotStateMsg) -> list[ArmState]`: convert ROS2 `ArmState` msg (with `geometry_msgs/Pose` EEF) to Pydantic `ArmState` (with `SE3` EEF)
    - Implement `safety_status_to_msg(level: SafetyLevel, guard: SafetyGuard, heartbeat: float) -> SafetyStatus`: build the ROS2 `SafetyStatus` message from guard state
    - Implement `json_envelope_to_vla_action(json_str: str) -> VLAAction`: deserialize `JsonEnvelope` payload to `VLAAction`
    - Implement `json_envelope_to_vla_constraints(json_str: str) -> VLASafetyConstraints`: deserialize `JsonEnvelope` payload to `VLASafetyConstraints`
    - Implement `vla_action_to_json_envelope(action: VLAAction) -> str`: serialize `VLAAction` to `JsonEnvelope` JSON string
    - _Requirements: 1.2, 2.1, 10.2, 16.1, 16.2, 16.3_

  - [ ]* 7.2 Write property test: Safety model serialization round-trip (Property 13)
    - **Property 13: Safety model serialization round-trip**
    - Use Hypothesis `builds()` to generate random `SafetyConfig`, `VLASafetyConstraints`, and `VLAAction` objects
    - Assert `JsonEnvelope.wrap(obj)` → deserialize from `payload_json` produces an equal object for each type
    - **Validates: Requirements 16.1, 16.2, 16.3**

  - [ ]* 7.3 Write unit tests for converters
    - Test `robot_state_msg_to_arms` correctly maps all fields including `geometry_msgs/Pose` → `SE3`
    - Test `safety_status_to_msg` includes all required fields (level, e_stop_active, e_stop_latched, violations, safe_zones, heartbeat)
    - Test JSON envelope deserialization error handling (invalid JSON returns descriptive error)
    - _Requirements: 1.2, 2.1, 10.2_

- [ ] 8. Implement SafetySupervisorNode (ROS2 node wiring)
  - [x] 8.1 Implement SafetySupervisorNode class
    - Create `roboweave_safety/roboweave_safety/safety_supervisor_node.py`
    - Subclass `rclpy.node.Node` with name `"safety_supervisor"`
    - Declare ROS2 parameters: `safety_params_file`, `workspace_limits_file`, `publish_rate_hz` (default 10.0), `watchdog_timeout_sec` (default 0.5)
    - Implement `_load_safety_config()`: load from YAML file path parameter, fall back to `SafetyConfig()` defaults if missing/invalid, log warning
    - Implement `_load_workspace_limits()`: load from YAML file path parameter, support multiple named workspaces, fall back to `WorkspaceLimits()` defaults if missing/invalid, log warning
    - Instantiate `SafetyMonitor`, `SafetyGuard`, `VLASafetyFilter` with loaded config
    - Create publisher on `/roboweave/safety/status` with QoS Reliable, depth=1, Transient Local
    - Create subscription on `/roboweave/robot_state`
    - Create timer for status publishing at `publish_rate_hz`
    - Implement watchdog: track last robot state timestamp, escalate to WARNING with "robot_state_timeout" violation if no message within `watchdog_timeout_sec`, clear when messages resume
    - Create SafetyControl service on `/roboweave/safety/control`: dispatch to `emergency_stop`, `release_stop`, `enter_safe_mode`, `set_speed_limit`, `set_force_limit`, `set_workspace`; return `success=false` for unrecognized actions
    - Create FilterVLAAction service on `/roboweave/safety/filter_vla_action`: deserialize request via converters, call `VLASafetyFilter.filter_action`, serialize response
    - Log all safety events, service calls, and VLA filter decisions via `rclpy` logger at appropriate severity levels
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 10.1, 10.2, 13.1, 13.2, 13.3, 13.4, 14.1, 14.2, 14.3, 14.4, 15.1, 15.3, 15.4_

  - [x] 8.2 Create the main entry point
    - Add `main()` function in `safety_supervisor_node.py` that initializes rclpy, spins the node, and handles shutdown
    - Ensure `setup.py` console_scripts entry point maps `safety_supervisor = roboweave_safety.safety_supervisor_node:main`
    - _Requirements: 15.1_

  - [ ]* 8.3 Write unit tests for SafetySupervisorNode
    - Test watchdog timeout triggers WARNING + "robot_state_timeout" violation (Req 2.3)
    - Test watchdog recovery clears timeout violation (Req 2.4)
    - Test missing config file uses defaults and logs warning (Req 14.3)
    - _Requirements: 2.3, 2.4, 14.3_

- [x] 9. Checkpoint — Verify node wiring
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Create configuration files and launch file
  - [x] 10.1 Create safety_params.yaml and workspace_limits.yaml
    - Create `roboweave_safety/config/safety_params.yaml` with default values matching `SafetyConfig` defaults: `max_joint_velocity: [2.0, 2.0, 2.0, 2.0, 3.0, 3.0, 3.0]`, `max_eef_velocity: 1.0`, `max_eef_angular_velocity: 2.0`, `force_limit: 50.0`, `torque_limit: 20.0`, `min_human_distance: 0.3`, `enable_self_collision_check: true`, `enable_environment_collision_check: true`, `cloud_disconnect_timeout_sec: 30.0`
    - Create `roboweave_safety/config/workspace_limits.yaml` with `default` workspace and example named workspace
    - _Requirements: 5.3, 14.1, 14.2_

  - [x] 10.2 Create launch file
    - Create `roboweave_safety/launch/safety.launch.py`
    - Launch `safety_supervisor` node as an independent process
    - Pass `safety_params_file` and `workspace_limits_file` as ROS2 parameters pointing to the config files
    - Pass `publish_rate_hz` and `watchdog_timeout_sec` as configurable launch arguments
    - _Requirements: 1.1, 14.4, 15.1_

- [x] 11. Final checkpoint — Ensure all tests pass
  - Run the full test suite (`pytest roboweave_safety/tests/`), ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each major component
- Property tests validate the 13 universal correctness properties from the design document
- Unit tests validate specific examples, edge cases, and error conditions
- All pure Python components (SafetyMonitor, SafetyGuard, VLASafetyFilter) are testable without ROS2
- The implementation language is Python, matching the design document and existing `roboweave_interfaces` package
