# Implementation Plan: roboweave-interfaces

## Overview

Implement the `roboweave_interfaces` pure-Python package providing all Pydantic v2 data models for the RoboWeave hybrid robotics system. The implementation follows the dependency graph: project scaffolding → base layer → refs → domain modules → public API → tests. All code is Python 3.10+ with Pydantic v2 as the only runtime dependency.

## Tasks

- [x] 1. Set up project scaffolding
  - [x] 1.1 Create `pyproject.toml` with build-system, project metadata, dependencies (`pydantic>=2.0,<3.0`), optional dev dependencies (`pytest>=7.0`, `hypothesis>=6.0`), and setuptools package discovery
    - _Requirements: 1.1, 1.2, 1.3_
  - [x] 1.2 Create `roboweave_interfaces/__init__.py` (empty placeholder, will be populated in task 8) and `roboweave_interfaces/_version.py` defining `SCHEMA_VERSION = "roboweave.v1"`
    - _Requirements: 1.5, 23.1_
  - [x] 1.3 Create `tests/__init__.py` (empty)

- [x] 2. Implement base layer (`base.py`)
  - [x] 2.1 Implement `VersionedModel(pydantic.BaseModel)` with `schema_version: str = SCHEMA_VERSION` field, `TimestampedData(VersionedModel)` with fields `timestamp`, `frame_id`, `valid_until`, `source_module`, `confidence`, and `JsonEnvelope(BaseModel)` with fields `schema_name`, `schema_version`, `payload_json`, `payload_hash` and `wrap()` classmethod computing SHA-256 hash
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 4.1, 4.2_
  - [ ]* 2.2 Write unit tests in `tests/test_base.py` for VersionedModel default schema_version, TimestampedData default field values, JsonEnvelope.wrap() producing correct schema_name/version/hash, and JsonEnvelope field existence
    - _Requirements: 2.2, 3.1, 3.2, 3.3, 4.1, 4.2_

- [x] 3. Implement DataRef hierarchy (`refs.py`)
  - [x] 3.1 Implement `DataRef(VersionedModel)` with fields `uri`, `timestamp`, `frame_id`, `valid_until`, `source_module`, and all subclasses: `ImageRef`, `DepthRef`, `PointCloudRef`, `MaskRef`, `TrajectoryRef`, `WorldStateRef` with their domain-specific extra fields as specified in the design
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_
  - [ ]* 3.2 Write unit tests in `tests/test_refs.py` for DataRef and all subclass field defaults, inheritance from DataRef/VersionedModel, and domain-specific field existence
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

- [x] 4. Implement core domain modules (part 1: world_state, task, skill)
  - [x] 4.1 Implement `world_state.py`: `SE3(BaseModel)` with position (length-3 constrained) and quaternion (length-4 constrained), `BoundingBox3D(BaseModel)`, `ObjectObservation(TimestampedData)`, `ObjectBelief(TimestampedData)`, `ObjectLifecycle(str, Enum)`, `ObjectState(VersionedModel)`, `ArmState(VersionedModel)`, `GripperState(VersionedModel)`, `RobotState(VersionedModel)`, `SafeZone`, `ForbiddenZone`, `EnvironmentState(VersionedModel)`, `TaskState`, `WorldState(VersionedModel)`. All mutable defaults must use `Field(default_factory=...)`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9_
  - [ ]* 4.2 Write unit tests in `tests/test_world_state.py` for SE3 default values, SE3 validation rejection (wrong-length position/quaternion), BoundingBox3D defaults, ObjectLifecycle enum values, ObjectState field existence and defaults, RobotState/WorldState structure
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.10_
  - [x] 4.3 Implement `task.py`: `TaskPriority(str, Enum)`, `TaskStatus(str, Enum)`, `RetryPolicy(BaseModel)`, `SuccessCondition`, `FailurePolicy`, `SceneContext`, `PlanNode(VersionedModel)`, `PlanGraph(VersionedModel)`, `TaskRequest(VersionedModel)`. All mutable defaults must use `Field(default_factory=...)`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_
  - [ ]* 4.4 Write unit tests in `tests/test_task.py` for TaskPriority/TaskStatus enum values, RetryPolicy defaults, PlanNode field existence and defaults, PlanGraph structure, TaskRequest structure and mutable default independence
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_
  - [x] 4.5 Implement `skill.py`: `SkillCategory(str, Enum)`, `SkillStatus(str, Enum)`, `SkillLogs`, `PreconditionResult`, `PostconditionResult`, `SkillDescriptor(VersionedModel)` with resource lock fields, `SkillCall(VersionedModel)`, `SkillResult(VersionedModel)`. All mutable defaults must use `Field(default_factory=...)`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_
  - [ ]* 4.6 Write unit tests in `tests/test_skill.py` for SkillCategory/SkillStatus enum values, SkillDescriptor field existence and resource lock fields, SkillCall/SkillResult structure, mutable default independence
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement domain modules (part 2: perception, grasp, motion, control, vla)
  - [x] 6.1 Implement `perception.py`: `DetectionResult(TimestampedData)`, `SegmentationResult(TimestampedData)`, `PointCloudResult(TimestampedData)`, `PoseEstimationResult(TimestampedData)` with fields as specified in the design
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  - [ ]* 6.2 Write unit tests in `tests/test_perception.py` for all perception types inheriting TimestampedData, field existence, and default values
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  - [x] 6.3 Implement `grasp.py`: `GraspCandidate(VersionedModel)` with SE3 pose, approach direction, grasp width, quality score, arm_id; `GraspConstraints(VersionedModel)` with force limits, approach constraints, allowed grasp types
    - _Requirements: 11.1, 11.2_
  - [ ]* 6.4 Write unit tests in `tests/test_grasp.py` for GraspCandidate and GraspConstraints field existence, defaults, and inheritance
    - _Requirements: 11.1, 11.2_
  - [x] 6.5 Implement `motion.py`: `TrajectoryPoint(BaseModel)` with positions, velocities, accelerations, time_from_start; `MotionRequest(VersionedModel)`; `TrajectoryResult(VersionedModel)` with list[TrajectoryPoint] default_factory
    - _Requirements: 12.1, 12.2, 12.3_
  - [ ]* 6.6 Write unit tests in `tests/test_motion.py` for TrajectoryPoint as plain BaseModel, MotionRequest/TrajectoryResult structure and defaults
    - _Requirements: 12.1, 12.2, 12.3_
  - [x] 6.7 Implement `control.py`: `ControlCommand(VersionedModel)` with command type, arm_id, trajectory reference, gripper command; `ControlStatus(VersionedModel)` with execution state, tracking error, completion percentage
    - _Requirements: 13.1, 13.2_
  - [ ]* 6.8 Write unit tests in `tests/test_control.py` for ControlCommand and ControlStatus field existence and defaults
    - _Requirements: 13.1, 13.2_
  - [x] 6.9 Implement `vla.py`: `VLAActionType(str, Enum)`, `VLAActionSpace(VersionedModel)`, `VLAAction(TimestampedData)` with action_type, delta_pose, target_pose, joint_delta, gripper_command, confidence, requires_safety_filter; `VLASafetyConstraints(VersionedModel)` with velocity/force/torque limits
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_
  - [ ]* 6.10 Write unit tests in `tests/test_vla.py` for VLAActionType enum values, VLAActionSpace defaults, VLAAction structure and requires_safety_filter retention, VLASafetyConstraints defaults
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

- [x] 7. Implement domain modules (part 3: event, episode, safety, hardware, errors, hitl)
  - [x] 7.1 Implement `errors.py`: `ErrorCode(str, Enum)` with all module-prefixed values (PER_, GRP_, IK_, MOT_, CTL_, VLA_, SAF_, COM_, TSK_), `ErrorCodeSpec` with code, module, severity, recoverable, retryable, default_recovery_policy, escalation flags; `FailureInfo(VersionedModel)`; `ERROR_CODE_SPECS` registry dict mapping every ErrorCode to its ErrorCodeSpec
    - _Requirements: 19.1, 19.2, 19.3, 19.5_
  - [x] 7.2 Implement `event.py`: `EventType(str, Enum)`, `Severity(str, Enum)`, `ExecutionEvent(VersionedModel)` with event_id, task_id, node_id, event_type, failure_code, severity, message, recovery_candidates, timestamp; `RecoveryAction(VersionedModel)`
    - _Requirements: 15.1, 15.2, 15.3, 15.4_
  - [ ]* 7.3 Write unit tests in `tests/test_errors.py` for ErrorCode enum members, ErrorCodeSpec field existence, FailureInfo structure, and ERROR_CODE_SPECS registry completeness (every ErrorCode has an entry)
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5_
  - [ ]* 7.4 Write unit tests in `tests/test_event.py` for EventType/Severity enum values, ExecutionEvent field existence and defaults, RecoveryAction structure
    - _Requirements: 15.1, 15.2, 15.3, 15.4_
  - [x] 7.5 Implement `episode.py`: `EpisodeStatus(str, Enum)`, `EpisodeLabels(VersionedModel)`, `SystemVersions(VersionedModel)`, `SkillLog(VersionedModel)`, `FrameLog(VersionedModel)` with ImageRef/DepthRef/PointCloudRef/MaskRef/WorldStateRef/DataRef optional refs, `EpisodeLog(VersionedModel)` with all fields and mutable default_factory usage
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6_
  - [ ]* 7.6 Write unit tests in `tests/test_episode.py` for EpisodeStatus enum values, EpisodeLabels defaults, FrameLog ref fields, EpisodeLog structure and mutable defaults
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7_
  - [x] 7.7 Implement `safety.py`: `SafetyLevel(str, Enum)`, `WorkspaceLimits(VersionedModel)`, `SafetyConfig(VersionedModel)`, `SafetyEvent(VersionedModel)`
    - _Requirements: 17.1, 17.2, 17.3, 17.4_
  - [ ]* 7.8 Write unit tests in `tests/test_safety.py` for SafetyLevel enum values, WorkspaceLimits fields, SafetyConfig fields, SafetyEvent structure
    - _Requirements: 17.1, 17.2, 17.3, 17.4_
  - [x] 7.9 Implement `hardware.py`: `ArmConfig(VersionedModel)`, `GripperConfig(VersionedModel)`, `CameraConfig(VersionedModel)`, `MobileBaseConfig(VersionedModel)`, `HardwareConfig(VersionedModel)` with list default_factory for arms, grippers, cameras and optional mobile_base
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5_
  - [ ]* 7.10 Write unit tests in `tests/test_hardware.py` for all hardware config types field existence, defaults, and HardwareConfig list defaults
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5_
  - [x] 7.11 Implement `hitl.py`: `HITLRequestType(str, Enum)`, `HITLRequest(VersionedModel)` with request_id, task_id, request_type, message, options, image_refs, timeout_sec, priority; `HITLResponse(VersionedModel)` with request_id, response_type, selected_option, text_input, click_point, correction_data, operator_id
    - _Requirements: 20.1, 20.2, 20.3_
  - [ ]* 7.12 Write unit tests in `tests/test_hitl.py` for HITLRequestType enum values, HITLRequest field existence and defaults, HITLResponse field existence and defaults
    - _Requirements: 20.1, 20.2, 20.3_

- [x] 8. Wire up public API re-exports (`__init__.py`)
  - [x] 8.1 Populate `roboweave_interfaces/__init__.py` with re-exports of all public types from all modules (base, refs, task, world_state, skill, perception, grasp, motion, control, vla, event, episode, safety, hardware, errors, hitl). Verify all types are importable from the top-level namespace
    - _Requirements: 1.4_

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement test infrastructure and cross-cutting property tests
  - [x] 10.1 Create `tests/conftest.py` with a helper that discovers all VersionedModel subclasses in the package via recursive `__subclasses__()`. Provide fixtures for model discovery used by cross-cutting property tests
    - _Requirements: 22.1, 22.2_
  - [ ]* 10.2 Write property test for serialization round-trip in `tests/test_round_trip.py`
    - **Property 1: Serialization round-trip** — For any VersionedModel subclass and any valid instance, `model_validate_json(instance.model_dump_json())` produces an equal instance
    - **Validates: Requirements 2.3, 5.8, 8.10, 16.7, 22.1, 22.2, 22.3**
  - [ ]* 10.3 Write property test for default schema version consistency in `tests/test_round_trip.py`
    - **Property 2: Default schema version consistency** — For any VersionedModel subclass, instantiating with minimal required fields produces schema_version equal to SCHEMA_VERSION
    - **Validates: Requirements 2.2, 23.2**
  - [ ]* 10.4 Write property test for JsonEnvelope wrap correctness in `tests/test_round_trip.py`
    - **Property 3: JsonEnvelope wrap correctness** — For any valid VersionedModel instance, `JsonEnvelope.wrap(instance)` produces correct schema_name, schema_version, payload_json, and payload_hash
    - **Validates: Requirements 3.2, 3.3**
  - [ ]* 10.5 Write property test for JsonEnvelope round-trip in `tests/test_round_trip.py`
    - **Property 4: JsonEnvelope round-trip** — For any valid VersionedModel instance, wrapping into JsonEnvelope then parsing payload_json back produces an equal model
    - **Validates: Requirements 3.4**
  - [ ]* 10.6 Write property test for SE3 validation rejection in `tests/test_world_state.py`
    - **Property 5: SE3 validation rejects invalid dimensions** — For any list of floats with length ≠ 3, SE3(position=...) raises ValidationError; for length ≠ 4, SE3(quaternion=...) raises ValidationError
    - **Validates: Requirements 6.3, 6.4**
  - [ ]* 10.7 Write property test for mutable default independence in `tests/test_mutable_defaults.py`
    - **Property 6: Mutable default independence** — For any model with list/dict/model-typed defaults, creating two instances and mutating one does not affect the other
    - **Validates: Requirements 7.8, 9.8, 21.1, 21.2, 21.3, 21.4**
  - [ ]* 10.8 Write property test for error code registry completeness in `tests/test_errors.py`
    - **Property 7: Error code registry completeness** — For every ErrorCode enum member, ERROR_CODE_SPECS contains a corresponding entry with matching code field
    - **Validates: Requirements 19.3, 19.4**
  - [ ]* 10.9 Write property test for schema version preservation on deserialization in `tests/test_round_trip.py`
    - **Property 8: Schema version preservation on deserialization** — For any VersionedModel subclass and any non-default schema_version string, serializing and deserializing retains the custom schema_version
    - **Validates: Requirements 23.3**

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each major phase
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific structural requirements (field existence, defaults, enums)
- The `conftest.py` model discovery helper ensures new models are automatically covered by cross-cutting property tests
- All code is Python 3.10+ with Pydantic v2; no ROS2 dependency
