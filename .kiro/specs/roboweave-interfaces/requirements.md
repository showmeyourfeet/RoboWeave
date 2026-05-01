# Requirements Document: roboweave-interfaces

## Introduction

The `roboweave_interfaces` package is the foundational pure-Python data structure library for the RoboWeave hybrid robotics system (VLM-Agent + Skill + VLA). It defines all Pydantic v2 data models used across the entire system — from task planning and world state representation to skill execution, VLA actions, safety, and episode logging. This package has zero ROS2 dependency and serves as the single source of truth for data contracts between all RoboWeave packages. It corresponds to Phase 0.1 of the RoboWeave development roadmap.

## Glossary

- **Package**: The `roboweave_interfaces` pip-installable Python package
- **VersionedModel**: Pydantic v2 BaseModel subclass carrying a `schema_version` field for schema evolution
- **JsonEnvelope**: A wrapper model that serializes any VersionedModel into a JSON string with schema name, version, and integrity hash
- **DataRef**: A base reference type pointing to large binary data (images, point clouds, trajectories) by URI instead of embedding the data inline
- **TimestampedData**: A VersionedModel subclass adding timestamp, frame_id, valid_until, source_module, and confidence fields
- **SE3**: A model representing a rigid-body pose as a 3D position vector and a quaternion in [x, y, z, w] order
- **PlanGraph**: A directed acyclic graph of PlanNode objects representing a decomposed task execution plan
- **SkillCall**: A request to execute a named skill with specific inputs and constraints
- **SkillResult**: The outcome of a skill execution including status, outputs, and failure information
- **WorldState**: A snapshot of the robot, all tracked objects, environment, and current task state
- **ObjectObservation**: Raw per-frame detection output for an object (camera-frame pose, bounding box, mask reference)
- **ObjectBelief**: Fused belief state for an object (base-frame pose, covariance, velocity, reachability)
- **VLAAction**: A single-step action output from a Vision-Language-Action model with action type, pose data, and safety metadata
- **EpisodeLog**: A complete record of one task execution including skill logs, frame logs, labels, and system versions
- **ErrorCode**: An enumeration of all system error codes organized by module prefix (PER_, GRP_, IK_, MOT_, CTL_, VLA_, SAF_, COM_, TSK_)
- **ErrorCodeSpec**: Metadata for each ErrorCode specifying module, severity, recoverability, retry policy, and escalation rules
- **HITLRequest**: A human-in-the-loop request from the system to a human operator for confirmation, disambiguation, or teleoperation
- **Serializer**: The Pydantic v2 JSON serialization/deserialization mechanism (model_dump_json / model_validate_json)
- **Round_Trip**: The property that serializing then deserializing a model produces an equivalent object

## Requirements

### Requirement 1: Package Structure and Installation

**User Story:** As a RoboWeave developer, I want to install roboweave_interfaces via pip from a pyproject.toml, so that all other packages can declare it as a dependency without requiring ROS2.

#### Acceptance Criteria

1. THE Package SHALL be installable via `pip install .` from the package root directory containing pyproject.toml
2. THE Package SHALL declare Python >= 3.10 and pydantic >= 2.0 as its only runtime dependencies
3. THE Package SHALL have zero ROS2 dependencies in its runtime dependency list
4. WHEN imported, THE Package SHALL expose all public data models from a top-level `roboweave_interfaces` namespace
5. THE Package SHALL contain a `_version.py` module defining the constant `SCHEMA_VERSION = "roboweave.v1"`

### Requirement 2: VersionedModel Base Class

**User Story:** As a RoboWeave developer, I want all cross-process data structures to carry a schema version, so that I can detect and handle schema evolution across system components.

#### Acceptance Criteria

1. THE VersionedModel SHALL inherit from pydantic.BaseModel and include a `schema_version` field defaulting to `SCHEMA_VERSION`
2. WHEN a VersionedModel subclass is instantiated without an explicit schema_version, THE subclass instance SHALL have schema_version equal to "roboweave.v1"
3. WHEN a VersionedModel subclass is serialized to JSON and deserialized back, THE Round_Trip SHALL produce a model instance with all fields equal to the original

### Requirement 3: JsonEnvelope Wrap and Unwrap

**User Story:** As a RoboWeave developer, I want a uniform JSON transport envelope, so that any serialized model can be identified by schema name and version and verified by hash.

#### Acceptance Criteria

1. THE JsonEnvelope SHALL contain fields: schema_name (str), schema_version (str), payload_json (str), payload_hash (str, default empty)
2. WHEN `JsonEnvelope.wrap(model)` is called with a VersionedModel instance, THE JsonEnvelope SHALL set schema_name to the model class name, schema_version to the model's schema_version, payload_json to the model's JSON serialization, and payload_hash to the SHA-256 hex digest of payload_json
3. WHEN a JsonEnvelope with a non-empty payload_hash is received, THE consumer SHALL be able to verify integrity by comparing SHA-256 of payload_json against payload_hash
4. FOR ALL valid VersionedModel instances, wrapping into a JsonEnvelope then parsing payload_json back SHALL produce an equivalent model (round-trip property)

### Requirement 4: TimestampedData Base Class

**User Story:** As a RoboWeave developer, I want a base class for time-sensitive data, so that all sensor and state data carry consistent temporal metadata.

#### Acceptance Criteria

1. THE TimestampedData SHALL inherit from VersionedModel and include fields: timestamp (float, default 0.0), frame_id (str, default ""), valid_until (float, default 0.0), source_module (str, default ""), confidence (float, default 1.0)
2. WHEN TimestampedData is instantiated with default values, THE instance SHALL have timestamp=0.0, frame_id="", valid_until=0.0, source_module="", confidence=1.0

### Requirement 5: DataRef Hierarchy

**User Story:** As a RoboWeave developer, I want typed references to large binary data, so that control-plane messages remain lightweight while pointing to data-plane resources.

#### Acceptance Criteria

1. THE DataRef SHALL inherit from VersionedModel and include fields: uri (str), timestamp (float), frame_id (str, default ""), valid_until (float, default 0.0), source_module (str, default "")
2. THE ImageRef SHALL inherit from DataRef and add fields: encoding (str, default "rgb8"), width (int, default 0), height (int, default 0)
3. THE DepthRef SHALL inherit from DataRef and add fields: encoding (str, default "16UC1"), width (int, default 0), height (int, default 0), depth_unit (str, default "mm")
4. THE PointCloudRef SHALL inherit from DataRef and add fields: num_points (int, default 0), has_color (bool, default False), has_normals (bool, default False), format (str, default "ply")
5. THE MaskRef SHALL inherit from DataRef and add fields: object_id (str, default ""), mask_confidence (float, default 0.0), pixel_count (int, default 0)
6. THE TrajectoryRef SHALL inherit from DataRef and add fields: num_points (int, default 0), duration_sec (float, default 0.0), arm_id (str, default "")
7. THE WorldStateRef SHALL inherit from DataRef and add fields: num_objects (int, default 0), robot_id (str, default "")
8. FOR ALL DataRef subclasses, serializing to JSON and deserializing back SHALL produce an equivalent instance (round-trip property)

### Requirement 6: Geometric Primitives (SE3, BoundingBox3D)

**User Story:** As a RoboWeave developer, I want standard geometric types, so that all modules use consistent pose and bounding box representations.

#### Acceptance Criteria

1. THE SE3 SHALL inherit from pydantic.BaseModel and include fields: position (list[float], default [0.0, 0.0, 0.0], constrained to length 3) and quaternion (list[float], default [0.0, 0.0, 0.0, 1.0], constrained to length 4, in [x, y, z, w] order)
2. THE BoundingBox3D SHALL inherit from pydantic.BaseModel and include fields: center (SE3, default factory) and size (list[float], default [0.0, 0.0, 0.0], constrained to length 3)
3. IF an SE3 is constructed with a position list not of length 3, THEN THE SE3 SHALL raise a validation error
4. IF an SE3 is constructed with a quaternion list not of length 4, THEN THE SE3 SHALL raise a validation error

### Requirement 7: Task Types

**User Story:** As a RoboWeave developer, I want structured task request and plan graph types, so that the cloud agent and runtime can exchange well-defined task execution plans.

#### Acceptance Criteria

1. THE TaskPriority SHALL be a string enum with values: LOW, NORMAL, HIGH, URGENT
2. THE TaskStatus SHALL be a string enum with values: PENDING, RUNNING, PAUSED, SUCCEEDED, FAILED, CANCELLED
3. THE RetryPolicy SHALL include fields: max_retries (int, default 3), backoff_ms (int, default 500), backoff_strategy (str, default "fixed")
4. THE PlanNode SHALL inherit from VersionedModel and include fields: node_id (str), node_type (str), skill_name (str, default ""), inputs (dict, default_factory), depends_on (list[str], default_factory), constraints (dict, default_factory), preconditions (list[str], default_factory), postconditions (list[str], default_factory), retry_policy (RetryPolicy or None, default None), timeout_ms (int, default 0), on_success (list[str], default_factory), on_failure (list[str], default_factory), rollback_action (str, default ""), recovery_policy_id (str, default ""), required_resources (list[str], default_factory), interruptible (bool, default True), safety_level (str, default "normal")
5. THE PlanGraph SHALL inherit from VersionedModel and include fields: plan_id (str), task_id (str), nodes (list[PlanNode], default_factory), success_condition (SuccessCondition, default_factory), failure_policy (FailurePolicy, default_factory)
6. THE TaskRequest SHALL inherit from VersionedModel and include fields: task_id (str), user_id (str), instruction (str), input_type (str, default "text"), context (SceneContext, default_factory), attachment_refs (list[DataRef], default_factory), priority (TaskPriority, default NORMAL), require_confirmation (bool, default False)
7. THE SceneContext SHALL include fields: scene_id (str, default ""), robot_id (str, default ""), world_state_ref_uri (str, default ""), world_state_timestamp (float, default 0.0)
8. WHEN any task type with list or dict fields is instantiated multiple times, THE instances SHALL have independent mutable defaults (no shared mutable state)

### Requirement 8: World State Types

**User Story:** As a RoboWeave developer, I want a world state model with observation/belief separation for objects, so that the system distinguishes raw sensor output from fused state estimates.

#### Acceptance Criteria

1. THE ObjectLifecycle SHALL be a string enum with values: ACTIVE, OCCLUDED, LOST, REMOVED, HELD
2. THE ObjectObservation SHALL inherit from TimestampedData and include fields: bbox_2d (list[int], default_factory), mask_ref (MaskRef or None), pose_in_camera (SE3 or None), point_cloud_ref (PointCloudRef or None), detection_confidence (float, default 0.0), segmentation_confidence (float, default 0.0)
3. THE ObjectBelief SHALL inherit from TimestampedData and include fields: pose_in_base (SE3 or None), bbox_3d (BoundingBox3D or None), pose_covariance (list[float], default_factory), velocity (list[float], default_factory), is_static (bool, default True), grasp_candidates (list[str], default_factory), reachable (bool or None, default None)
4. THE ObjectState SHALL inherit from VersionedModel and include fields: object_id (str), category (str), description (str, default ""), observed (ObjectObservation or None), belief (ObjectBelief or None), lifecycle_state (ObjectLifecycle, default ACTIVE), last_seen (float, default 0.0), confidence (float, default 0.0), ttl_sec (float, default 5.0), properties (dict, default_factory)
5. THE ArmState SHALL inherit from VersionedModel and include fields for arm_id, joint_positions, joint_velocities, eef_pose, and is_moving
6. THE GripperState SHALL inherit from VersionedModel and include fields for gripper_id, position, force, is_grasping, and grasped_object_id
7. THE RobotState SHALL inherit from VersionedModel and include fields: robot_id (str), arms (list[ArmState], default_factory), grippers (list[GripperState], default_factory), base_pose (SE3 or None), is_moving (bool, default False), current_control_mode (str, default "position")
8. THE EnvironmentState SHALL inherit from VersionedModel and include fields for safe_zones (list[SafeZone], default_factory) and forbidden_zones (list[ForbiddenZone], default_factory)
9. THE WorldState SHALL inherit from VersionedModel and include fields: timestamp (float), robot (RobotState), objects (list[ObjectState], default_factory), environment (EnvironmentState, default_factory), task (TaskState or None)
10. FOR ALL WorldState instances, serializing to JSON and deserializing back SHALL produce an equivalent instance (round-trip property)

### Requirement 9: Skill Types

**User Story:** As a RoboWeave developer, I want skill call, result, and descriptor types with resource declarations, so that the skill orchestrator can schedule skills with proper resource locking and precondition/postcondition checking.

#### Acceptance Criteria

1. THE SkillCategory SHALL be a string enum with values representing skill categories (e.g., PICK, PLACE, MOVE, INSPECT, VLA, COMPOSITE)
2. THE SkillStatus SHALL be a string enum with values: PENDING, RUNNING, SUCCEEDED, FAILED, CANCELLED, TIMEOUT
3. THE SkillDescriptor SHALL inherit from VersionedModel and include fields: name (str), category (SkillCategory), description (str), version (str), input_schema (dict, default_factory), output_schema (dict, default_factory), preconditions (list[str], default_factory), postconditions (list[str], default_factory), timeout_ms (int, default 5000), retry_limit (int, default 2), fallback_skills (list[str], default_factory), safety_requirements (list[str], default_factory), required_resources (list[str], default_factory), exclusive_resources (list[str], default_factory), estimated_duration_ms (int, default 0), realtime_level (str, default "non_realtime"), side_effects (list[str], default_factory)
4. THE SkillCall SHALL inherit from VersionedModel and include fields: skill_call_id (str), skill_name (str), task_id (str), inputs (dict, default_factory), constraints (dict, default_factory), timeout_ms (int, default 5000)
5. THE SkillResult SHALL inherit from VersionedModel and include fields: skill_call_id (str), status (SkillStatus), outputs (dict, default_factory), failure_code (str, default ""), failure_message (str, default ""), logs (SkillLogs or None)
6. THE PreconditionResult SHALL include fields indicating whether preconditions passed and a list of failure reasons
7. THE PostconditionResult SHALL include fields indicating whether postconditions passed and a list of failure reasons
8. WHEN any skill type with list or dict fields is instantiated multiple times, THE instances SHALL have independent mutable defaults

### Requirement 10: Perception Types

**User Story:** As a RoboWeave developer, I want structured perception result types, so that detection, segmentation, point cloud, and pose estimation outputs have consistent schemas.

#### Acceptance Criteria

1. THE DetectionResult SHALL inherit from TimestampedData and include fields for detected objects with bounding boxes, class labels, and confidence scores
2. THE SegmentationResult SHALL inherit from TimestampedData and include fields for segmentation masks with associated object identifiers and mask references
3. THE PointCloudResult SHALL inherit from TimestampedData and include fields for point cloud data references and metadata
4. THE PoseEstimationResult SHALL inherit from TimestampedData and include fields for estimated SE3 poses with confidence and object identifiers

### Requirement 11: Grasp Types

**User Story:** As a RoboWeave developer, I want grasp candidate and constraint types, so that the grasp planner can output ranked candidates with approach parameters.

#### Acceptance Criteria

1. THE GraspCandidate SHALL inherit from VersionedModel and include fields for grasp pose (SE3), approach direction, grasp width, quality score, and arm_id
2. THE GraspConstraints SHALL inherit from VersionedModel and include fields for force limits, approach constraints, and allowed grasp types

### Requirement 12: Motion Types

**User Story:** As a RoboWeave developer, I want motion request and trajectory types, so that the planner and controller can exchange trajectory data with consistent structure.

#### Acceptance Criteria

1. THE TrajectoryPoint SHALL inherit from pydantic.BaseModel and include fields for positions, velocities, accelerations, and time_from_start
2. THE MotionRequest SHALL inherit from VersionedModel and include fields for target pose, arm_id, constraints, and motion type
3. THE TrajectoryResult SHALL inherit from VersionedModel and include fields for trajectory points (list[TrajectoryPoint], default_factory), success status, and planning time

### Requirement 13: Control Types

**User Story:** As a RoboWeave developer, I want control command and status types, so that the controller can receive commands and report execution status.

#### Acceptance Criteria

1. THE ControlCommand SHALL inherit from VersionedModel and include fields for command type, arm_id, trajectory reference, and gripper command
2. THE ControlStatus SHALL inherit from VersionedModel and include fields for execution state, tracking error, and completion percentage

### Requirement 14: VLA Types

**User Story:** As a RoboWeave developer, I want VLA action types with action space constraints and safety metadata, so that VLA model outputs can be validated and filtered before execution.

#### Acceptance Criteria

1. THE VLAActionType SHALL be a string enum with values: DELTA_EEF_POSE, TARGET_EEF_POSE, JOINT_DELTA, GRIPPER_COMMAND, SKILL_SUBGOAL
2. THE VLAActionSpace SHALL include fields: supported_action_types (list[VLAActionType], default_factory), max_delta_position (float, default 0.05), max_delta_rotation (float, default 0.1), max_joint_delta (float, default 0.1), control_frequency_hz (float, default 10.0)
3. THE VLAAction SHALL inherit from TimestampedData and include fields: action_type (VLAActionType), frame_id (str, default "base_link"), delta_pose (SE3 or None), target_pose (SE3 or None), joint_delta (list[float], default_factory), gripper_command (dict, default_factory), confidence (float, default 0.0), horizon_steps (int, default 1), requires_safety_filter (bool, default True)
4. THE VLASafetyConstraints SHALL inherit from VersionedModel and include fields: max_velocity (float, default 0.25), max_angular_velocity (float, default 0.5), force_limit (float, default 20.0), torque_limit (float, default 10.0), workspace_limit_id (str, default ""), max_duration_sec (float, default 60.0), allow_contact (bool, default False), min_confidence_threshold (float, default 0.3)
5. WHEN a VLAAction is constructed with requires_safety_filter=True, THE VLAAction instance SHALL retain that value for downstream safety filter enforcement

### Requirement 15: Event Types

**User Story:** As a RoboWeave developer, I want execution event and recovery action types, so that the execution monitor can emit structured events and the recovery system can act on them.

#### Acceptance Criteria

1. THE EventType SHALL be a string enum with values representing event categories (e.g., SKILL_STARTED, SKILL_COMPLETED, SKILL_FAILED, RECOVERY_STARTED, RECOVERY_COMPLETED, SAFETY_EVENT, TASK_COMPLETED)
2. THE Severity SHALL be a string enum with values: DEBUG, INFO, WARNING, ERROR, CRITICAL
3. THE ExecutionEvent SHALL inherit from VersionedModel and include fields: event_id (str), task_id (str), node_id (str, default ""), event_type (EventType), failure_code (str, default ""), severity (Severity), message (str, default ""), recovery_candidates (list[str], default_factory), timestamp (float)
4. THE RecoveryAction SHALL inherit from VersionedModel and include fields for action name, parameters, and target node

### Requirement 16: Episode and Data Logging Types

**User Story:** As a RoboWeave developer, I want episode, skill log, and frame log types with structured labels, so that all task executions are recorded for replay, debugging, and training data generation.

#### Acceptance Criteria

1. THE EpisodeStatus SHALL be a string enum with values: RECORDING, COMPLETED, FAILED, ABORTED
2. THE EpisodeLabels SHALL inherit from VersionedModel and include fields: task_type (str, default ""), object_categories (list[str], default_factory), scene_type (str, default ""), success (bool, default False), failure_stage (str, default ""), failure_code (str, default ""), recovery_used (bool, default False), human_intervention (bool, default False), data_quality (str, default "normal"), tags (list[str], default_factory)
3. THE SystemVersions SHALL inherit from VersionedModel and include fields for package versions, model versions, and configuration hashes
4. THE SkillLog SHALL inherit from VersionedModel and include fields for skill_call_id, skill_name, start_time, end_time, status, inputs, outputs, and failure information
5. THE FrameLog SHALL inherit from VersionedModel and include fields: timestamp (float), episode_id (str), rgb_ref (ImageRef or None), depth_ref (DepthRef or None), point_cloud_ref (PointCloudRef or None), mask_ref (MaskRef or None), robot_state_ref (DataRef or None), world_state_ref (WorldStateRef or None), control_command_ref (DataRef or None), labels (dict, default_factory)
6. THE EpisodeLog SHALL inherit from VersionedModel and include fields: episode_id (str), task_id (str), status (EpisodeStatus), start_time (float), end_time (float, default 0.0), duration_sec (float, default 0.0), task_instruction (str, default ""), plan_ref (DataRef or None), skill_logs (list[SkillLog], default_factory), labels (EpisodeLabels, default_factory), failure_code (str, default ""), notes (str, default ""), system_versions (SystemVersions or None)
7. FOR ALL EpisodeLog instances, serializing to JSON and deserializing back SHALL produce an equivalent instance (round-trip property)

### Requirement 17: Safety Types

**User Story:** As a RoboWeave developer, I want safety configuration and event types, so that the safety supervisor can be configured and can emit structured safety events.

#### Acceptance Criteria

1. THE SafetyLevel SHALL be a string enum with values: NORMAL, WARNING, CRITICAL, EMERGENCY_STOP
2. THE WorkspaceLimits SHALL inherit from VersionedModel and include fields for min/max position bounds in x, y, z axes
3. THE SafetyConfig SHALL inherit from VersionedModel and include fields for max_eef_velocity, force_limit, torque_limit, min_human_distance, workspace_limits, and enable flags
4. THE SafetyEvent SHALL inherit from VersionedModel and include fields for event type, severity, violation details, timestamp, and arm_id

### Requirement 18: Hardware Configuration Types

**User Story:** As a RoboWeave developer, I want hardware configuration types, so that robot hardware can be described declaratively and loaded from YAML profiles.

#### Acceptance Criteria

1. THE ArmConfig SHALL inherit from VersionedModel and include fields for arm_id, num_joints, joint_names, joint_limits, and driver configuration
2. THE GripperConfig SHALL inherit from VersionedModel and include fields for gripper_id, gripper_type, max_width, max_force, and driver configuration
3. THE CameraConfig SHALL inherit from VersionedModel and include fields for camera_id, camera_type, resolution, frame_rate, and intrinsics reference
4. THE MobileBaseConfig SHALL inherit from VersionedModel and include fields for base_type, max_linear_velocity, and max_angular_velocity
5. THE HardwareConfig SHALL inherit from VersionedModel and include fields: arms (list[ArmConfig], default_factory), grippers (list[GripperConfig], default_factory), cameras (list[CameraConfig], default_factory), mobile_base (MobileBaseConfig or None)

### Requirement 19: Error Code System

**User Story:** As a RoboWeave developer, I want a comprehensive error code enum with associated metadata, so that the execution monitor can automatically route failures to appropriate recovery strategies.

#### Acceptance Criteria

1. THE ErrorCode SHALL be a string enum with values organized by module prefix: PER_ (perception), GRP_ (grasp), IK_ (inverse kinematics), MOT_ (motion), CTL_ (control), VLA_ (VLA), SAF_ (safety), COM_ (communication), TSK_ (task)
2. THE ErrorCodeSpec SHALL include fields: code (ErrorCode), module (str), severity (Severity), recoverable (bool), retryable (bool), default_recovery_policy (str, default ""), escalate_to_cloud (bool, default False), escalate_to_user (bool, default False), safety_related (bool, default False)
3. THE Package SHALL provide an ERROR_CODE_SPECS registry (dict[ErrorCode, ErrorCodeSpec]) mapping every ErrorCode to its ErrorCodeSpec
4. WHEN a new ErrorCode is added to the enum, THE ERROR_CODE_SPECS registry SHALL contain a corresponding ErrorCodeSpec entry (enforced by test)
5. THE FailureInfo SHALL inherit from VersionedModel and include fields for error_code, message, timestamp, context, and recovery_attempts

### Requirement 20: HITL (Human-in-the-Loop) Types

**User Story:** As a RoboWeave developer, I want HITL request and response types, so that the system can request human operator input for confirmation, disambiguation, and teleoperation.

#### Acceptance Criteria

1. THE HITLRequestType SHALL be a string enum with values: CONFIRM_TARGET, DISAMBIGUATE_TARGET, CONFIRM_ACTION, TELEOP_ASSIST, MANUAL_CORRECTION, SAFETY_RELEASE
2. THE HITLRequest SHALL inherit from VersionedModel and include fields: request_id (str), task_id (str), request_type (HITLRequestType), message (str), options (list[str], default_factory), image_refs (list[ImageRef], default_factory), timeout_sec (float, default 60.0), priority (str, default "normal")
3. THE HITLResponse SHALL inherit from VersionedModel and include fields: request_id (str), response_type (str), selected_option (str, default ""), text_input (str, default ""), click_point (list[float], default_factory), correction_data (dict, default_factory), operator_id (str, default "")

### Requirement 21: Mutable Default Safety

**User Story:** As a RoboWeave developer, I want all mutable default values to use Field(default_factory=...), so that no two model instances accidentally share mutable state.

#### Acceptance Criteria

1. FOR ALL models in the Package that have list-typed fields, THE field definitions SHALL use `Field(default_factory=list)` or an equivalent lambda factory
2. FOR ALL models in the Package that have dict-typed fields, THE field definitions SHALL use `Field(default_factory=dict)` or an equivalent lambda factory
3. FOR ALL models in the Package that have model-typed fields with defaults, THE field definitions SHALL use `Field(default_factory=ModelClass)` or an equivalent factory
4. WHEN two instances of the same model class are created with default values, THE instances SHALL have independent mutable fields (mutating one does not affect the other)

### Requirement 22: Serialization Round-Trip Integrity

**User Story:** As a RoboWeave developer, I want all models to survive JSON round-trips without data loss, so that cross-process and cross-network communication preserves data fidelity.

#### Acceptance Criteria

1. FOR ALL VersionedModel subclasses in the Package, calling `model_validate_json(instance.model_dump_json())` SHALL produce a model equal to the original instance
2. FOR ALL VersionedModel subclasses with nested model fields, THE round-trip property SHALL hold for deeply nested structures
3. FOR ALL enum fields in any model, THE round-trip serialization SHALL preserve the enum value as a string and deserialize back to the correct enum member

### Requirement 23: Schema Version Consistency

**User Story:** As a RoboWeave developer, I want all VersionedModel subclasses to default to the same schema version constant, so that version checks are reliable across the system.

#### Acceptance Criteria

1. THE `_version.py` module SHALL define `SCHEMA_VERSION = "roboweave.v1"`
2. FOR ALL VersionedModel subclasses in the Package, THE default schema_version SHALL equal the value of SCHEMA_VERSION
3. WHEN a model is deserialized with a different schema_version value, THE deserialized instance SHALL retain that different schema_version value (no silent overwrite)
