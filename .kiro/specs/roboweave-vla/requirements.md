# Requirements Document — roboweave_vla (Phase 5)

## Introduction

The `roboweave_vla` package provides Vision-Language-Action (VLA) skill capabilities for the RoboWeave hybrid robotics system. VLA skills are complex manipulation skills (e.g., cloth folding, cable arrangement) that use learned models to generate actions from visual observations and language instructions. The package hosts a ROS2 action server (`RunVLASkill`), an abstract base class for VLA skills (`VLASkillBase`), a runtime monitor (`VLAMonitor`) for confidence/safety/timeout tracking, a safety filter integration that calls `roboweave_safety`'s `FilterVLAAction` service, a skill registry for discovering and managing VLA skills, and a mock `fold_cloth` skill for integration testing. VLA skills implement `SkillProtocol` from `roboweave_runtime` so they participate in the unified skill orchestration lifecycle (precondition → execute → postcondition, resource locking, cancellation). The package depends on `roboweave_interfaces`, `roboweave_msgs`, `rclpy`, and `numpy`. The pure-Python core (skill base, monitor, registry) is testable without a running ROS2 graph.

## Glossary

- **VLA_Node**: The top-level ROS2 node (`VLANode`) that hosts the `RunVLASkill` action server, manages the VLA skill registry, and coordinates prediction–filter–execute loops.
- **VLA_Skill_Base**: The abstract base class (`VLASkillBase`) that all VLA skills must extend. Declares `predict`, `reset`, `action_space`, `skill_name`, `supported_instructions`, and `default_safety_constraints`.
- **VLA_Monitor**: The component that monitors VLA execution in real time, tracking per-step confidence, cumulative safety filter rejections, step count against `max_steps`, and elapsed time against `timeout_sec`.
- **Safety_Filter_Client**: The component within VLA_Node that calls `roboweave_safety`'s `FilterVLAAction` service on `/roboweave/safety/filter_vla_action` to validate and clamp each predicted VLA action before execution.
- **Skill_Registry**: An in-process registry that maps skill names to `VLASkillBase` instances, supports registration, lookup, listing, and validation of skill metadata.
- **VLA_Action**: A single action output from a VLA model, as defined in `roboweave_interfaces.vla.VLAAction`.
- **VLA_Action_Space**: The action space declaration for a VLA skill, as defined in `roboweave_interfaces.vla.VLAActionSpace`.
- **VLA_Safety_Constraints**: Safety constraints applied to VLA actions, as defined in `roboweave_interfaces.vla.VLASafetyConstraints`.
- **RunVLASkill_Action**: The ROS2 action defined in `roboweave_msgs/action/RunVLASkill.action` with goal fields (`skill_name`, `instruction`, `arm_id`, `safety_constraints`, `max_steps`, `timeout_sec`), result fields (`status`, `failure_code`, `message`, `steps_executed`), and feedback fields (`current_step`, `confidence`, `action_type`, `status`).
- **Skill_Protocol**: The `SkillProtocol` from `roboweave_runtime` that all skills must implement (`descriptor`, `execute`, `check_precondition`, `check_postcondition`).
- **Skill_Descriptor**: The `SkillDescriptor` from `roboweave_interfaces.skill` that declares a skill's metadata, resource requirements, and capabilities.
- **Skill_Call**: The `SkillCall` from `roboweave_interfaces.skill` representing a request to execute a skill.
- **Skill_Result**: The `SkillResult` from `roboweave_interfaces.skill` representing the outcome of a skill execution.
- **Mock_Fold_Cloth_Skill**: A concrete `VLASkillBase` implementation that generates synthetic `delta_eef_pose` actions for cloth folding, used for integration testing without a real VLA model.
- **Control_Period**: The inverse of `VLAActionSpace.control_frequency_hz`, representing the time interval between consecutive VLA predictions.
- **Prediction_Loop**: The iterative cycle within a VLA skill execution: observe → predict → filter → execute → check termination.

## Requirements

### Requirement 1: VLA Node Action Server

**User Story:** As a task executor, I want the VLA_Node to host a RunVLASkill action server, so that the skill orchestrator can invoke VLA skills through the standard ROS2 action interface.

#### Acceptance Criteria

1. THE VLA_Node SHALL host a `RunVLASkill` action server on the `/roboweave/vla/run_skill` topic.
2. WHEN a `RunVLASkill` goal is received, THE VLA_Node SHALL look up the requested `skill_name` in the Skill_Registry.
3. IF the requested `skill_name` is not found in the Skill_Registry, THEN THE VLA_Node SHALL abort the goal with `status` set to "failed" and `failure_code` set to "VLA_SKILL_NOT_FOUND".
4. WHEN a valid goal is accepted, THE VLA_Node SHALL reset the requested skill by calling `VLA_Skill_Base.reset()` before starting the Prediction_Loop.
5. THE VLA_Node SHALL publish `RunVLASkill` feedback after each prediction step with the `current_step`, `confidence`, `action_type`, and step `status`.

### Requirement 2: Prediction Loop Execution

**User Story:** As a system integrator, I want the VLA_Node to execute the predict–filter–execute loop for each VLA step, so that VLA actions are generated, safety-checked, and dispatched in a controlled cycle.

#### Acceptance Criteria

1. WHEN a VLA skill execution is active, THE VLA_Node SHALL call `VLA_Skill_Base.predict()` with the current RGB observation, depth observation (if available), robot state, and instruction on each step of the Prediction_Loop.
2. WHEN `VLA_Skill_Base.predict()` returns a VLA_Action, THE VLA_Node SHALL send the action to the Safety_Filter_Client for validation before execution.
3. IF the Safety_Filter_Client returns `approved=true`, THEN THE VLA_Node SHALL dispatch the filtered action for execution.
4. IF the Safety_Filter_Client returns `approved=false`, THEN THE VLA_Node SHALL report the rejection to the VLA_Monitor and skip execution of that step.
5. THE VLA_Node SHALL wait for the Control_Period duration between consecutive prediction steps to maintain the declared control frequency.

### Requirement 3: Safety Filter Integration

**User Story:** As a safety engineer, I want every VLA action to pass through the safety filter service before execution, so that unsafe actions are blocked or clamped regardless of the VLA model's output.

#### Acceptance Criteria

1. THE Safety_Filter_Client SHALL call the `FilterVLAAction` service on `/roboweave/safety/filter_vla_action` for every VLA_Action produced by the Prediction_Loop.
2. THE Safety_Filter_Client SHALL serialize the VLA_Action and VLA_Safety_Constraints into JSON (JsonEnvelope format) for the service request.
3. WHEN the `FilterVLAAction` service returns `approved=true`, THE Safety_Filter_Client SHALL deserialize the `filtered_action_json` and return the clamped VLA_Action.
4. WHEN the `FilterVLAAction` service returns `approved=false`, THE Safety_Filter_Client SHALL return the `rejection_reason` and `violation_type` to the caller.
5. IF the `FilterVLAAction` service is unavailable, THEN THE Safety_Filter_Client SHALL treat the action as rejected with `rejection_reason` "safety_service_unavailable" and THE VLA_Node SHALL abort the current skill execution with `failure_code` "VLA_SAFETY_UNAVAILABLE".

### Requirement 4: VLA Monitor — Confidence Tracking

**User Story:** As a system integrator, I want the VLA_Monitor to track per-step confidence and detect sustained low-confidence predictions, so that unreliable VLA executions are stopped before causing harm.

#### Acceptance Criteria

1. WHEN a VLA_Action is produced, THE VLA_Monitor SHALL record the `confidence` value for the current step.
2. IF the VLA_Action `confidence` falls below the `min_confidence_threshold` from VLA_Safety_Constraints for a configurable number of consecutive steps (default 3), THEN THE VLA_Monitor SHALL signal the VLA_Node to abort the execution with `failure_code` "VLA_CONFIDENCE_LOW".
3. THE VLA_Monitor SHALL expose the current mean confidence and the count of consecutive low-confidence steps for feedback reporting.

### Requirement 5: VLA Monitor — Safety Rejection Tracking

**User Story:** As a safety engineer, I want the VLA_Monitor to track cumulative safety filter rejections, so that a VLA skill that repeatedly produces unsafe actions is terminated.

#### Acceptance Criteria

1. WHEN the Safety_Filter_Client returns `approved=false`, THE VLA_Monitor SHALL increment a rejection counter for the current execution.
2. IF the cumulative rejection count exceeds a configurable threshold (default 5), THEN THE VLA_Monitor SHALL signal the VLA_Node to abort the execution with `failure_code` "VLA_SAFETY_REJECTED".
3. THE VLA_Monitor SHALL reset the rejection counter when a new VLA skill execution begins.

### Requirement 6: VLA Monitor — Step and Timeout Limits

**User Story:** As a task executor, I want the VLA_Monitor to enforce step count and time limits, so that VLA executions do not run indefinitely.

#### Acceptance Criteria

1. WHEN `max_steps` in the RunVLASkill goal is greater than zero, THE VLA_Monitor SHALL terminate the Prediction_Loop after the specified number of steps and set the result `status` to "success" with `steps_executed` equal to `max_steps`.
2. WHEN `timeout_sec` in the RunVLASkill goal is greater than zero, THE VLA_Monitor SHALL terminate the Prediction_Loop if the elapsed time exceeds `timeout_sec` and set the result `status` to "timeout" with `failure_code` "VLA_TIMEOUT".
3. WHEN `timeout_sec` is zero or not provided, THE VLA_Monitor SHALL use `VLA_Safety_Constraints.max_duration_sec` as the timeout.
4. THE VLA_Monitor SHALL track elapsed time from the moment the first prediction step begins.

### Requirement 7: VLA Skill Base — Abstract Interface

**User Story:** As a VLA skill developer, I want a well-defined abstract base class, so that I can implement new VLA skills with a consistent interface for prediction, reset, and metadata declaration.

#### Acceptance Criteria

1. THE VLA_Skill_Base SHALL declare abstract properties: `skill_name` (str), `supported_instructions` (list of str), `action_space` (VLA_Action_Space), and `default_safety_constraints` (VLA_Safety_Constraints).
2. THE VLA_Skill_Base SHALL declare an abstract method `predict(rgb, depth, robot_state, instruction, **kwargs)` that returns a VLA_Action.
3. THE VLA_Skill_Base SHALL declare an abstract method `reset()` that returns None.
4. THE VLA_Skill_Base SHALL provide a concrete `descriptor` property that returns a Skill_Descriptor with `category` set to `SkillCategory.VLA`, populated from the skill's abstract properties.
5. THE VLA_Skill_Base SHALL provide concrete `check_precondition` and `check_postcondition` methods that return satisfied results by default, allowing subclasses to override.
6. THE VLA_Skill_Base SHALL provide a concrete `execute` method that integrates with the Prediction_Loop, so that subclasses only need to implement `predict` and `reset`.

### Requirement 8: Skill Protocol Compliance

**User Story:** As a runtime integrator, I want VLA skills to implement Skill_Protocol, so that the skill orchestrator can manage VLA skills through the same lifecycle as all other skills (precondition, execute, postcondition, resource locking, cancellation).

#### Acceptance Criteria

1. THE VLA_Skill_Base SHALL implement the Skill_Protocol interface (`descriptor`, `execute`, `check_precondition`, `check_postcondition`).
2. WHEN `execute` is called with a Skill_Call, THE VLA_Skill_Base SHALL extract the `instruction`, `arm_id`, `max_steps`, and `timeout_sec` from `Skill_Call.inputs` and run the Prediction_Loop.
3. WHEN `execute` is called, THE VLA_Skill_Base SHALL return a Skill_Result with `status` reflecting the outcome of the Prediction_Loop (SUCCESS, FAILED, TIMEOUT, CANCELLED, SAFETY_STOP).
4. THE VLA_Skill_Base SHALL declare `exclusive_resources` including the `arm_id` in its Skill_Descriptor, so that the resource manager prevents concurrent use of the same arm.

### Requirement 9: Skill Registry

**User Story:** As a system integrator, I want a skill registry that manages VLA skill instances, so that skills can be registered at startup, discovered by name, and validated for metadata consistency.

#### Acceptance Criteria

1. THE Skill_Registry SHALL support registering a VLA_Skill_Base instance by its `skill_name`.
2. IF a skill with the same `skill_name` is already registered, THEN THE Skill_Registry SHALL reject the registration and raise an error.
3. THE Skill_Registry SHALL support looking up a registered skill by `skill_name`, returning the VLA_Skill_Base instance or None if not found.
4. THE Skill_Registry SHALL support listing all registered skills with their Skill_Descriptors.
5. THE Skill_Registry SHALL validate that each registered skill has a non-empty `skill_name`, at least one entry in `supported_instructions`, and a valid `action_space` with at least one `supported_action_types` entry.

### Requirement 10: Mock Fold Cloth Skill

**User Story:** As a developer, I want a mock VLA skill that simulates cloth folding, so that the VLA framework can be integration-tested without a real VLA model.

#### Acceptance Criteria

1. THE Mock_Fold_Cloth_Skill SHALL extend VLA_Skill_Base with `skill_name` set to "fold_cloth".
2. THE Mock_Fold_Cloth_Skill SHALL declare `supported_instructions` including "fold the cloth" and "fold cloth".
3. THE Mock_Fold_Cloth_Skill SHALL declare an `action_space` with `supported_action_types` containing `DELTA_EEF_POSE` and `GRIPPER_COMMAND`.
4. WHEN `predict` is called, THE Mock_Fold_Cloth_Skill SHALL return a synthetic VLA_Action of type `DELTA_EEF_POSE` with a small deterministic delta and a `confidence` value between 0.7 and 0.95.
5. WHEN `predict` is called with step count exceeding a configurable fold sequence length (default 10), THE Mock_Fold_Cloth_Skill SHALL return a VLA_Action of type `GRIPPER_COMMAND` with `gripper_command` set to `{"action": "open"}` to signal completion.
6. WHEN `reset` is called, THE Mock_Fold_Cloth_Skill SHALL reset its internal step counter to zero.

### Requirement 11: Goal Cancellation

**User Story:** As a task executor, I want to cancel a running VLA skill execution, so that the robot can stop the current VLA task and free resources when a higher-priority task arrives or the user requests cancellation.

#### Acceptance Criteria

1. WHEN a cancel request is received for an active RunVLASkill goal, THE VLA_Node SHALL stop the Prediction_Loop after the current step completes.
2. WHEN a VLA skill execution is cancelled, THE VLA_Node SHALL call `VLA_Skill_Base.reset()` on the active skill.
3. WHEN a VLA skill execution is cancelled, THE VLA_Node SHALL set the result `status` to "cancelled" and `steps_executed` to the number of steps completed before cancellation.

### Requirement 12: Configuration Loading

**User Story:** As a system integrator, I want the VLA_Node to load VLA parameters and skill registry configuration from YAML files, so that control frequency, monitor thresholds, and skill registration can be tuned per deployment.

#### Acceptance Criteria

1. THE VLA_Node SHALL load VLA parameters from a `vla_params.yaml` configuration file at startup.
2. THE VLA_Node SHALL load skill registry entries from a `vla_skill_registry.yaml` configuration file at startup.
3. THE `vla_params.yaml` SHALL support configuring: default control frequency, default safety constraints, monitor thresholds (consecutive low-confidence limit, max rejection count), and the safety filter service name.
4. THE `vla_skill_registry.yaml` SHALL support declaring skill entries with `skill_name`, `module_path`, and `class_name` for dynamic loading.
5. IF a configuration file is missing or contains invalid values, THEN THE VLA_Node SHALL use default values and log a warning.
6. THE VLA_Node SHALL accept configuration file paths as ROS2 parameters, allowing override via launch files.

### Requirement 13: VLA Execution Logging

**User Story:** As a data engineer, I want VLA executions to produce structured logs, so that VLA skill performance can be analyzed and VLA models can be improved through offline training.

#### Acceptance Criteria

1. THE VLA_Node SHALL log the start of each VLA skill execution with the `skill_name`, `instruction`, `arm_id`, and `safety_constraints`.
2. THE VLA_Node SHALL log each prediction step with the `step_number`, `action_type`, `confidence`, safety filter `approved` status, and `rejection_reason` (if rejected).
3. THE VLA_Node SHALL log the completion of each VLA skill execution with the `status`, `failure_code`, `steps_executed`, and elapsed time.
4. THE VLA_Node SHALL use the ROS2 logging infrastructure (`rclpy` logger) for all VLA execution logs at appropriate severity levels (INFO for normal operations, WARN for low confidence or rejections, ERROR for failures).

### Requirement 14: VLA Data Structures Serialization Round-Trip

**User Story:** As a developer, I want VLA data structures to survive serialization and deserialization without data loss, so that VLA actions and configurations are faithfully transmitted across ROS2 service and action boundaries.

#### Acceptance Criteria

1. FOR ALL valid VLA_Action objects, serializing to JSON and deserializing back SHALL produce an equivalent VLA_Action object (round-trip property).
2. FOR ALL valid VLA_Action_Space objects, serializing to JSON and deserializing back SHALL produce an equivalent VLA_Action_Space object (round-trip property).
3. FOR ALL valid VLA_Safety_Constraints objects, serializing to JSON and deserializing back SHALL produce an equivalent VLA_Safety_Constraints object (round-trip property).
4. FOR ALL valid Skill_Descriptor objects with `category` VLA, serializing to JSON and deserializing back SHALL produce an equivalent Skill_Descriptor object (round-trip property).

### Requirement 15: Pure Python Testability

**User Story:** As a developer, I want the VLA_Skill_Base, VLA_Monitor, and Skill_Registry to be testable without a running ROS2 graph, so that unit tests run fast and do not require ROS2 infrastructure.

#### Acceptance Criteria

1. THE VLA_Skill_Base SHALL not import `rclpy` or any ROS2 module at the class level.
2. THE VLA_Monitor SHALL not import `rclpy` or any ROS2 module at the class level.
3. THE Skill_Registry SHALL not import `rclpy` or any ROS2 module at the class level.
4. THE VLA_Skill_Base, VLA_Monitor, and Skill_Registry SHALL depend only on `roboweave_interfaces` and `numpy` for their core logic.
