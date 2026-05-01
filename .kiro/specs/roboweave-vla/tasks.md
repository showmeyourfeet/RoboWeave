# Implementation Plan: roboweave_vla (Phase 5)

## Overview

Implement the `roboweave_vla` ROS2 package providing the VLA (Vision-Language-Action) skill framework. The implementation proceeds bottom-up: pure-Python core components first (monitor, skill base, registry), then the mock skill, converters, safety filter client, and finally the ROS2 node that wires everything together. Each step builds on the previous, with property and unit tests validating correctness incrementally.

## Tasks

- [ ] 1. Scaffold the roboweave_vla package structure
  - Create the `roboweave_vla/` package directory tree matching the design layout: `roboweave_vla/roboweave_vla/`, `roboweave_vla/roboweave_vla/skills/`, `config/`, `launch/`, `resource/`, `tests/`, `tests/integration/`
  - Create `__init__.py` files for `roboweave_vla/roboweave_vla/`, `roboweave_vla/roboweave_vla/skills/`, `tests/`, `tests/integration/`
  - Create `setup.py`, `setup.cfg`, `package.xml`, and `resource/roboweave_vla` following the conventions of existing packages (e.g., `roboweave_control`)
  - Create `config/vla_params.yaml` and `config/vla_skill_registry.yaml` with the default values from the design
  - Create a stub `launch/vla.launch.py`
  - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [ ] 2. Implement VLAMonitor (pure Python core)
  - [ ] 2.1 Implement `VLAMonitor` class and `MonitorStatus` dataclass in `roboweave_vla/roboweave_vla/vla_monitor.py`
    - Implement `__init__` with configurable `max_steps`, `timeout_sec`, `consecutive_low_confidence_limit`, `max_rejection_count`, `min_confidence_threshold`
    - Implement `start()`, `record_step(confidence)`, `record_rejection()`, `check()`, `reset()`
    - Implement properties: `steps_executed`, `mean_confidence`, `consecutive_low_confidence_count`, `rejection_count`, `elapsed_sec`
    - Ensure no `rclpy` imports at the class level
    - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3, 6.4, 15.2_

  - [ ]* 2.2 Write property test for VLAMonitor confidence tracking (Property 3)
    - **Property 3: VLAMonitor confidence tracking and consecutive low-confidence abort**
    - **Validates: Requirements 4.1, 4.2, 4.3**

  - [ ]* 2.3 Write property test for VLAMonitor rejection tracking (Property 4)
    - **Property 4: VLAMonitor rejection tracking and threshold abort**
    - **Validates: Requirements 5.1, 5.2**

  - [ ]* 2.4 Write property test for VLAMonitor step limit termination (Property 5)
    - **Property 5: VLAMonitor step limit termination**
    - **Validates: Requirements 6.1**

  - [ ]* 2.5 Write unit tests for VLAMonitor timeout and reset
    - Test timeout detection with mocked time (`time.monotonic`)
    - Test `reset()` clears all counters
    - Test fallback timeout from `max_duration_sec` when `timeout_sec` is zero
    - _Requirements: 5.3, 6.2, 6.3, 6.4_

- [ ] 3. Implement VLASkillBase (pure Python core)
  - [ ] 3.1 Implement `VLASkillBase` abstract base class in `roboweave_vla/roboweave_vla/vla_skill_base.py`
    - Declare abstract properties: `skill_name`, `supported_instructions`, `action_space`, `default_safety_constraints`
    - Declare abstract methods: `predict(rgb, depth, robot_state, instruction, **kwargs)`, `reset()`
    - Implement concrete `descriptor` property returning `SkillDescriptor` with `category=SkillCategory.VLA`
    - Implement concrete `check_precondition` and `check_postcondition` returning satisfied by default
    - Implement concrete `execute` method that extracts parameters from `SkillCall.inputs` and runs the prediction loop using `VLAMonitor`
    - Implement `cancel()` method setting a cancellation flag
    - Populate `exclusive_resources` with `arm_id` in the descriptor
    - Ensure no `rclpy` imports at the class level
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 8.1, 8.2, 8.3, 8.4, 15.1_

  - [ ]* 3.2 Write property test for VLASkillBase descriptor and SkillProtocol compliance (Property 9)
    - **Property 9: VLASkillBase descriptor and SkillProtocol compliance**
    - **Validates: Requirements 7.4, 8.1**

  - [ ]* 3.3 Write unit tests for VLASkillBase
    - Test abstract method enforcement (cannot instantiate without implementing all abstract members)
    - Test default `check_precondition` and `check_postcondition` return satisfied
    - Test `execute` extracts `instruction`, `arm_id`, `max_steps`, `timeout_sec` from `SkillCall.inputs`
    - _Requirements: 7.1, 7.2, 7.3, 7.5, 7.6, 8.2_

- [ ] 4. Implement SkillRegistry (pure Python core)
  - [ ] 4.1 Implement `SkillRegistry` class in `roboweave_vla/roboweave_vla/skill_registry.py`
    - Implement `register(skill)` with validation: non-empty `skill_name`, at least one `supported_instructions`, at least one `supported_action_types`, duplicate rejection
    - Implement `get(skill_name)` returning the instance or `None`
    - Implement `list_skills()` returning all `SkillDescriptor`s
    - Implement `__len__`
    - Ensure no `rclpy` imports at the class level
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 15.3_

  - [ ]* 4.2 Write property test for SkillRegistry register/lookup/list round-trip (Property 6)
    - **Property 6: SkillRegistry register/lookup/list round-trip**
    - **Validates: Requirements 9.1, 9.3, 9.4**

  - [ ]* 4.3 Write property test for SkillRegistry duplicate registration rejection (Property 7)
    - **Property 7: SkillRegistry duplicate registration rejection**
    - **Validates: Requirements 9.2**

  - [ ]* 4.4 Write property test for SkillRegistry validation rejects invalid metadata (Property 8)
    - **Property 8: SkillRegistry validation rejects invalid metadata**
    - **Validates: Requirements 9.5**

- [ ] 5. Checkpoint — Ensure all pure-Python core tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement MockFoldClothSkill and converters
  - [ ] 6.1 Implement `MockFoldClothSkill` in `roboweave_vla/roboweave_vla/skills/fold_cloth.py`
    - Extend `VLASkillBase` with `skill_name="fold_cloth"`
    - Declare `supported_instructions` as `["fold the cloth", "fold cloth"]`
    - Declare `action_space` with `DELTA_EEF_POSE` and `GRIPPER_COMMAND`, `control_frequency_hz=10.0`
    - Implement `predict()`: return `DELTA_EEF_POSE` with deterministic delta and confidence in [0.7, 0.95] for steps < `fold_sequence_length`; return `GRIPPER_COMMAND` with `{"action": "open"}` for steps >= `fold_sequence_length`
    - Implement `reset()`: reset internal step counter to zero
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [ ] 6.2 Implement converters in `roboweave_vla/roboweave_vla/converters.py`
    - Implement `vla_action_to_msg` / `msg_to_vla_action`
    - Implement `vla_safety_constraints_to_msg` / `msg_to_vla_safety_constraints`
    - Implement `vla_action_space_to_msg` / `msg_to_vla_action_space`
    - Follow the pure-function convention from `roboweave_control/converters.py`
    - _Requirements: 14.1, 14.2, 14.3_

  - [ ]* 6.3 Write property test for VLA data structures JSON round-trip (Property 1)
    - **Property 1: VLA data structures JSON round-trip**
    - **Validates: Requirements 14.1, 14.2, 14.3, 14.4**

  - [ ]* 6.4 Write property test for JsonEnvelope wrap/unwrap round-trip (Property 2)
    - **Property 2: JsonEnvelope wrap/unwrap round-trip**
    - **Validates: Requirements 3.2, 3.3**

  - [ ]* 6.5 Write property test for MockFoldClothSkill predict action correctness (Property 10)
    - **Property 10: MockFoldClothSkill predict action correctness**
    - **Validates: Requirements 10.4**

  - [ ]* 6.6 Write property test for MockFoldClothSkill reset restores initial state (Property 11)
    - **Property 11: MockFoldClothSkill reset restores initial state**
    - **Validates: Requirements 10.6**

  - [ ]* 6.7 Write unit tests for MockFoldClothSkill and converters
    - Test gripper_command after fold_sequence_length steps
    - Test converter round-trip with concrete examples
    - _Requirements: 10.5_

- [ ] 7. Implement SafetyFilterClient
  - [ ] 7.1 Implement `SafetyFilterClient` and `FilterResult` dataclass in `roboweave_vla/roboweave_vla/safety_filter.py`
    - Implement `__init__` accepting a ROS2 `Node` and `service_name`
    - Implement `filter(action, constraints, arm_id)` that serializes via `JsonEnvelope.wrap()`, calls the `FilterVLAAction` service, and deserializes the response
    - Return `FilterResult(approved=False, rejection_reason="safety_service_unavailable")` when the service is unreachable
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 7.2 Write unit tests for SafetyFilterClient
    - Test rejection reason passthrough when `approved=false`
    - Test service unavailability returns `safety_service_unavailable`
    - Mock the ROS2 service client
    - _Requirements: 3.4, 3.5_

- [ ] 8. Implement VLANode (ROS2 node)
  - [ ] 8.1 Implement `VLANode` in `roboweave_vla/roboweave_vla/vla_node.py`
    - Create `RunVLASkill` action server on `/roboweave/vla/run_skill`
    - Implement `_execute_callback`: look up skill in registry, abort with `VLA_SKILL_NOT_FOUND` if missing, reset skill, create `VLAMonitor`, run prediction loop (predict → filter → dispatch/skip → check monitor → publish feedback)
    - Implement `_cancel_callback`: accept cancel, set cancellation flag
    - Wait `Control_Period` between prediction steps
    - On cancel: stop loop after current step, reset skill, set result status to "cancelled"
    - On safety service unavailable: abort with `VLA_SAFETY_UNAVAILABLE`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 11.1, 11.2, 11.3_

  - [ ] 8.2 Implement configuration loading in `VLANode`
    - Load `vla_params.yaml` for monitor thresholds, default constraints, safety filter service name
    - Load `vla_skill_registry.yaml` for dynamic skill import and registration
    - Accept config file paths as ROS2 parameters for launch file override
    - Use default values and log warnings if config files are missing or invalid
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

  - [ ] 8.3 Implement VLA execution logging in `VLANode`
    - Log start of each execution with `skill_name`, `instruction`, `arm_id`, `safety_constraints` at INFO
    - Log each prediction step with `step_number`, `action_type`, `confidence`, `approved`, `rejection_reason` at INFO/WARN
    - Log completion with `status`, `failure_code`, `steps_executed`, elapsed time at INFO/ERROR
    - Use `rclpy` logger with appropriate severity levels
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [ ] 8.4 Create `roboweave_vla/roboweave_vla/__main__.py` entry point
    - Wire up `rclpy.init`, create `VLANode`, spin
    - _Requirements: 1.1_

- [ ] 9. Checkpoint — Ensure all unit and property tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Implement launch file and wire package entry points
  - [ ] 10.1 Implement `launch/vla.launch.py`
    - Launch `VLANode` with config file path parameters pointing to `vla_params.yaml` and `vla_skill_registry.yaml`
    - Follow the convention from `roboweave_control/launch/control.launch.py`
    - _Requirements: 12.6_

  - [ ]* 10.2 Write unit tests for VLANode prediction loop
    - Test skill lookup failure returns `VLA_SKILL_NOT_FOUND`
    - Test reset is called before prediction loop starts
    - Test approved action is dispatched, rejected action is skipped
    - Test control period timing between steps
    - Mock `SafetyFilterClient` and skill instances
    - _Requirements: 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 10.3 Write unit tests for cancellation
    - Test cancel stops loop after current step
    - Test reset is called on cancelled skill
    - Test result status is "cancelled" with correct `steps_executed`
    - _Requirements: 11.1, 11.2, 11.3_

  - [ ]* 10.4 Write unit tests for configuration loading
    - Test YAML loading with valid files
    - Test missing file uses defaults and logs warning
    - Test ROS2 parameter override of config paths
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

  - [ ]* 10.5 Write unit tests for VLA execution logging
    - Test log messages at correct severity levels
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [ ]* 10.6 Write pure-Python import tests
    - Verify `VLASkillBase`, `VLAMonitor`, and `SkillRegistry` do not import `rclpy` at the class level
    - _Requirements: 15.1, 15.2, 15.3, 15.4_

- [ ] 11. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (Properties 1–11)
- Unit tests validate specific examples, edge cases, and ROS2 integration behavior
- The pure-Python core (tasks 2–4) is testable without ROS2 infrastructure
- All Python commands use `.venv/bin/python` per project convention
- Test execution: `.venv/bin/python -m pytest roboweave_vla/tests/ -x --ignore=roboweave_vla/tests/integration`
