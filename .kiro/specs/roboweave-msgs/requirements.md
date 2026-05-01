# Requirements Document

## Introduction

The `roboweave_msgs` package is a ROS2 interface package (Phase 0.2) that defines all `.msg`, `.srv`, and `.action` types used for inter-node communication in the RoboWeave hybrid robotics system. It provides the ROS2 IDL counterparts to the Pydantic models already defined in `roboweave_interfaces` (Phase 0.1). The package uses `ament_cmake` for building and depends on standard ROS2 packages (`std_msgs`, `geometry_msgs`, `sensor_msgs`, `trajectory_msgs`, `action_msgs`).

## Glossary

- **Package**: The `roboweave_msgs` ROS2 interface package containing all `.msg`, `.srv`, and `.action` definitions
- **Builder**: The `ament_cmake` / `colcon` build system that compiles the IDL files into language-specific bindings
- **DataRef_Msg**: A ROS2 message type that mirrors the `DataRef` Pydantic base class, carrying a URI reference to large binary data instead of the data itself
- **JsonEnvelope_Msg**: A ROS2 message type that mirrors the `JsonEnvelope` Pydantic class, providing a uniform JSON transport wrapper with integrity hashing
- **Converter**: A Python module (in downstream packages) that translates between Pydantic models and their ROS2 msg counterparts
- **IDL_File**: A `.msg`, `.srv`, or `.action` file written in ROS2 Interface Definition Language
- **Pydantic_Model**: A Python data class defined in `roboweave_interfaces` that the corresponding ROS2 message must mirror
- **Control_Plane**: Lightweight metadata, commands, status, and references exchanged via ROS2 service/action/topic
- **Data_Plane**: Large binary data (images, point clouds, trajectories) referenced by URI through DataRef types

## Requirements

### Requirement 1: Package Structure and Build

**User Story:** As a RoboWeave developer, I want the `roboweave_msgs` package to follow standard ROS2 ament_cmake conventions, so that it integrates with the existing colcon workspace and all downstream packages can depend on it.

#### Acceptance Criteria

1. THE Package SHALL contain a `CMakeLists.txt` that uses `ament_cmake` as the build type and declares all `.msg`, `.srv`, and `.action` files via `rosidl_generate_interfaces`
2. THE Package SHALL contain a `package.xml` that declares build and runtime dependencies on `std_msgs`, `geometry_msgs`, `sensor_msgs`, `trajectory_msgs`, and `action_msgs`
3. THE Package SHALL organize IDL_Files into three directories: `msg/`, `srv/`, and `action/`
4. WHEN a developer runs `colcon build --packages-select roboweave_msgs`, THE Builder SHALL compile all IDL_Files without errors and generate Python and C++ bindings
5. THE Package SHALL declare `<buildtool_depend>rosidl_default_generators</buildtool_depend>` and `<exec_depend>rosidl_default_runtime</exec_depend>` in `package.xml`

### Requirement 2: DataRef Message Family

**User Story:** As a RoboWeave developer, I want ROS2 message equivalents for all DataRef Pydantic models, so that control-plane interfaces can pass lightweight references to large data instead of the data itself.

#### Acceptance Criteria

1. THE Package SHALL define a `DataRef.msg` base message containing fields: `string schema_version`, `string uri`, `float64 timestamp`, `string frame_id`, `float64 valid_until`, `string source_module`
2. THE Package SHALL define `ImageRef.msg` containing all `DataRef.msg` fields plus `string encoding`, `uint32 width`, `uint32 height`
3. THE Package SHALL define `DepthRef.msg` containing all `DataRef.msg` fields plus `string encoding`, `uint32 width`, `uint32 height`, `string depth_unit`
4. THE Package SHALL define `PointCloudRef.msg` containing all `DataRef.msg` fields plus `uint32 num_points`, `bool has_color`, `bool has_normals`, `string format`
5. THE Package SHALL define `MaskRef.msg` containing all `DataRef.msg` fields plus `string object_id`, `float64 mask_confidence`, `uint32 pixel_count`
6. THE Package SHALL define `TrajectoryRef.msg` containing all `DataRef.msg` fields plus `uint32 num_points`, `float64 duration_sec`, `string arm_id`
7. THE Package SHALL define `WorldStateRef.msg` containing all `DataRef.msg` fields plus `uint32 num_objects`, `string robot_id`
8. FOR ALL DataRef Pydantic_Models in `roboweave_interfaces/refs.py`, the corresponding ROS2 message SHALL contain one field per Pydantic field with an equivalent ROS2 IDL type

### Requirement 3: JsonEnvelope Message

**User Story:** As a RoboWeave developer, I want a ROS2 message for the JsonEnvelope wrapper, so that all JSON-over-ROS2 transport uses a consistent, versioned, integrity-checked format.

#### Acceptance Criteria

1. THE Package SHALL define `JsonEnvelope.msg` containing fields: `string schema_name`, `string schema_version`, `string payload_json`, `string payload_hash`
2. WHEN a downstream node publishes a JsonEnvelope_Msg, THE JsonEnvelope_Msg SHALL carry the SHA-256 hash of `payload_json` in the `payload_hash` field

### Requirement 4: Detection and Perception Messages

**User Story:** As a perception module developer, I want ROS2 message types for detection and perception results, so that perception services can return structured results over ROS2 interfaces.

#### Acceptance Criteria

1. THE Package SHALL define `Detection.msg` containing fields: `string object_id`, `string category`, `string matched_query`, `int32[] bbox_2d`, `float64 confidence`, `geometry_msgs/Pose pose_camera`, `std_msgs/Header header`
2. THE Package SHALL define `BoundingBox3D.msg` containing fields: `geometry_msgs/Pose center`, `float64[3] size`
3. THE Package SHALL define `GraspConstraints.msg` containing fields: `string[] preferred_regions`, `string[] avoid_regions`, `float64 max_force`, `float64 min_gripper_width`, `float64 max_gripper_width`, `float64[] approach_direction_hint`
4. THE Package SHALL define `GraspCandidate.msg` containing fields: `string grasp_id`, `geometry_msgs/Pose grasp_pose`, `float64[] approach_direction`, `float64 gripper_width`, `float64 grasp_score`, `float64 collision_score`, `bool reachable`, `string[] matched_regions`, `float64[] ik_solution`
5. THE Package SHALL define `ReachabilityResult.msg` containing fields: `bool reachable`, `string failure_code`, `float64[] ik_solution`, `float64 manipulability`
6. THE Package SHALL define `CollisionPair.msg` containing fields: `string object_a`, `string object_b`, `float64 min_distance`, `geometry_msgs/Point contact_point`

### Requirement 5: Safety and Control Messages

**User Story:** As a safety and control module developer, I want ROS2 message types for safety constraints, safety status, and robot state, so that the independent safety supervisor can communicate with all nodes via standard ROS2 topics and services.

#### Acceptance Criteria

1. THE Package SHALL define `VLASafetyConstraints.msg` containing fields: `float64 max_velocity`, `float64 max_angular_velocity`, `float64 force_limit`, `float64 torque_limit`, `string workspace_limit_id`, `float64 max_duration_sec`, `bool allow_contact`, `float64 min_confidence_threshold`
2. THE Package SHALL define `SafetyStatus.msg` containing fields: `std_msgs/Header header`, `string safety_level`, `bool e_stop_active`, `bool e_stop_latched`, `bool collision_detected`, `float32 min_human_distance`, `string[] active_violations`, `string[] active_safe_zones`, `float64 last_heartbeat`
3. THE Package SHALL define `RobotStateMsg.msg` containing fields: `string robot_id`, `ArmState[] arms`, `GripperState[] grippers`, `geometry_msgs/Pose base_pose`, `bool is_moving`, `string current_control_mode`
4. THE Package SHALL define `ArmState.msg` containing fields: `string arm_id`, `float64[] joint_positions`, `float64[] joint_velocities`, `float64[] joint_efforts`, `geometry_msgs/Pose eef_pose`, `float64 manipulability`
5. THE Package SHALL define `GripperState.msg` containing fields: `string gripper_id`, `string type`, `float64 width`, `float64 force`, `bool is_grasping`, `string grasped_object_id`

### Requirement 6: Runtime Messages

**User Story:** As a runtime module developer, I want ROS2 message types for task status, execution events, and world state updates, so that the execution monitor, world model, and data recorder can exchange structured information.

#### Acceptance Criteria

1. THE Package SHALL define `TaskStatus.msg` containing fields: `string task_id`, `string status`, `float64 progress`, `string current_node_id`, `string failure_code`, `string message`
2. THE Package SHALL define `ExecutionEvent.msg` containing fields: `string event_id`, `string task_id`, `string node_id`, `string event_type`, `string failure_code`, `string severity`, `string message`, `string[] recovery_candidates`, `float64 timestamp`
3. THE Package SHALL define `WorldStateUpdate.msg` containing fields: `std_msgs/Header header`, `string update_type`, `string object_id`, `string payload_json`
4. THE Package SHALL define `WorldStateStamped.msg` containing fields: `std_msgs/Header header`, `string world_state_json`

### Requirement 7: HITL Messages

**User Story:** As a human-in-the-loop module developer, I want ROS2 message types for HITL requests and teleop commands, so that the system can request human intervention and receive teleop input over standard ROS2 interfaces.

#### Acceptance Criteria

1. THE Package SHALL define `HITLRequestMsg.msg` containing fields: `string request_json`
2. THE Package SHALL define `TeleopCommand.msg` containing fields: `std_msgs/Header header`, `string arm_id`, `geometry_msgs/Twist twist`, `string gripper_action`

### Requirement 8: Perception Services

**User Story:** As a perception module developer, I want ROS2 service definitions for object detection, segmentation, point cloud building, and pose estimation, so that downstream nodes can invoke perception capabilities through standard ROS2 service calls.

#### Acceptance Criteria

1. THE Package SHALL define `DetectObjects.srv` with request fields (`string query`, `string camera_id`, `ImageRef rgb_ref`, `float64 confidence_threshold`) and response fields (`Detection[] detections`, `bool success`, `string error_code`, `string message`)
2. THE Package SHALL define `SegmentObject.srv` with request fields (`string object_id`, `string camera_id`, `ImageRef rgb_ref`, `DepthRef depth_ref`) and response fields (`MaskRef mask_ref`, `bool success`, `string error_code`, `string message`)
3. THE Package SHALL define `BuildPointCloud.srv` with request fields (`string object_id`, `DepthRef depth_ref`, `MaskRef mask_ref`) and response fields (`PointCloudRef point_cloud_ref`, `BoundingBox3D bbox_3d`, `bool success`, `string error_code`, `string message`)
4. THE Package SHALL define `EstimatePose.srv` with request fields (`string object_id`, `PointCloudRef point_cloud_ref`, `string method`) and response fields (`geometry_msgs/PoseStamped pose`, `float64 confidence`, `float64[] covariance`, `bool success`, `string error_code`, `string message`)

### Requirement 9: Planning Services

**User Story:** As a planning module developer, I want ROS2 service definitions for grasp planning, reachability checking, and collision checking, so that the skill orchestrator can invoke planning capabilities through standard ROS2 service calls.

#### Acceptance Criteria

1. THE Package SHALL define `PlanGrasp.srv` with request fields (`string object_id`, `PointCloudRef point_cloud_ref`, `GraspConstraints constraints`, `string arm_id`) and response fields (`GraspCandidate[] candidates`, `bool success`, `string error_code`, `string message`)
2. THE Package SHALL define `CheckReachability.srv` with request fields (`geometry_msgs/Pose target_pose`, `string arm_id`, `float64[] current_joint_state`) and response fields (`ReachabilityResult result`, `bool success`, `string error_code`, `string message`)
3. THE Package SHALL define `CheckCollision.srv` with request fields (`float64[] joint_state`, `string arm_id`, `string[] ignore_objects`) and response fields (`bool in_collision`, `CollisionPair[] collision_pairs`, `bool success`, `string error_code`, `string message`)

### Requirement 10: Control Services

**User Story:** As a control module developer, I want ROS2 service definitions for gripper commands and safety control, so that the skill orchestrator and safety supervisor can issue control commands through standard ROS2 service calls.

#### Acceptance Criteria

1. THE Package SHALL define `GripperCommand.srv` with request fields (`string gripper_id`, `string action`, `float64 width`, `float64 force`, `float64 speed`) and response fields (`bool success`, `float64 achieved_width`, `string error_code`, `string message`)
2. THE Package SHALL define `SafetyControl.srv` with request fields (`string action`, `string operator_id`, `string params_json`) and response fields (`bool success`, `string message`)

### Requirement 11: Runtime Services

**User Story:** As a runtime module developer, I want ROS2 service definitions for task dispatch, task control, world state management, skill listing, skill health, and recovery, so that the runtime can orchestrate task execution and manage system state.

#### Acceptance Criteria

1. THE Package SHALL define `DispatchPlan.srv` with request fields (`string task_id`, `string plan_json`) and response fields (`bool accepted`, `string message`)
2. THE Package SHALL define `TaskControl.srv` with request fields (`string task_id`, `string action`) and response fields (`bool success`, `string message`)
3. THE Package SHALL define `UpdateWorldState.srv` with request fields (`string update_type`, `string object_id`, `string payload_json`) and response fields (`bool success`, `string message`)
4. THE Package SHALL define `QueryWorldState.srv` with request fields (`string query_type`, `string object_id`) and response fields (`string result_json`, `bool success`, `string message`)
5. THE Package SHALL define `ListSkills.srv` with request fields (`string category_filter`) and response fields (`string[] skill_names`, `string[] skill_descriptors_json`, `bool success`)
6. THE Package SHALL define `SkillHealth.srv` with request fields (`string skill_name`) and response fields (`string status`, `string diagnostics_json`, `bool success`)
7. THE Package SHALL define `RequestRecovery.srv` with request fields (`string task_id`, `string failure_code`, `string context_json`) and response fields (`string recovery_action_json`, `bool success`, `string message`)

### Requirement 12: Data and Episode Services

**User Story:** As a data module developer, I want ROS2 service definitions for episode control and system version queries, so that the data recorder can manage episode lifecycle and track system versions.

#### Acceptance Criteria

1. THE Package SHALL define `EpisodeControl.srv` with request fields (`string action`, `string episode_id`, `string task_id`, `string labels_json`) and response fields (`string episode_id`, `bool success`, `string message`)
2. THE Package SHALL define `GetSystemVersions.srv` with an empty request and response fields (`string versions_json`, `bool success`)

### Requirement 13: Safety Services

**User Story:** As a safety module developer, I want a ROS2 service definition for VLA action filtering, so that the safety supervisor can approve or reject VLA actions before they reach the control layer.

#### Acceptance Criteria

1. THE Package SHALL define `FilterVLAAction.srv` with request fields (`string vla_action_json`, `string safety_constraints_json`, `string arm_id`) and response fields (`bool approved`, `string filtered_action_json`, `string rejection_reason`, `string violation_type`)

### Requirement 14: HITL Services

**User Story:** As a HITL module developer, I want a ROS2 service definition for HITL responses, so that human operators can submit responses to intervention requests.

#### Acceptance Criteria

1. THE Package SHALL define `HITLRespond.srv` with request fields (`string response_json`) and response fields (`bool accepted`, `string message`)

### Requirement 15: Planning Action

**User Story:** As a planning module developer, I want a ROS2 action definition for motion planning, so that long-running planning requests can provide progress feedback and support cancellation.

#### Acceptance Criteria

1. THE Package SHALL define `PlanMotion.action` with goal fields (`string arm_id`, `geometry_msgs/Pose goal_pose`, `float64[] goal_joint_state`, `string planning_mode`, `float64 max_velocity_scaling`, `float64 max_acceleration_scaling`, `string[] ignore_collision_objects`, `int32 max_planning_time_ms`), result fields (`trajectory_msgs/JointTrajectory trajectory`, `float64 duration_sec`, `bool collision_free`, `string failure_code`, `string message`), and feedback fields (`string status`, `float64 progress`)

### Requirement 16: Perception Action

**User Story:** As a perception module developer, I want a ROS2 action definition for pose tracking, so that continuous pose tracking can provide real-time feedback and support cancellation.

#### Acceptance Criteria

1. THE Package SHALL define `TrackPose.action` with goal fields (`string object_id`, `string camera_id`, `float64 tracking_frequency_hz`), result fields (`string final_status`, `string error_code`, `string message`), and feedback fields (`geometry_msgs/PoseStamped current_pose`, `float64 confidence`, `float64 tracking_age_sec`)

### Requirement 17: VLA Action

**User Story:** As a VLA module developer, I want a ROS2 action definition for running VLA skills, so that long-running VLA skill executions can provide step-by-step feedback and support cancellation.

#### Acceptance Criteria

1. THE Package SHALL define `RunVLASkill.action` with goal fields (`string skill_name`, `string instruction`, `string arm_id`, `VLASafetyConstraints safety_constraints`, `int32 max_steps`, `float64 timeout_sec`), result fields (`string status`, `string failure_code`, `string message`, `int32 steps_executed`), and feedback fields (`int32 current_step`, `float64 confidence`, `string action_type`, `string status`)

### Requirement 18: Control Action

**User Story:** As a control module developer, I want a ROS2 action definition for trajectory execution, so that long-running trajectory executions can provide progress feedback and support cancellation.

#### Acceptance Criteria

1. THE Package SHALL define `ExecuteTrajectory.action` with goal fields (`string arm_id`, `trajectory_msgs/JointTrajectory trajectory`, `float64 velocity_scaling`, `bool monitor_force`), result fields (`bool success`, `string error_code`, `string message`, `float64 max_tracking_error`), and feedback fields (`float64 progress`, `float64 tracking_error`, `float64[] current_joint_positions`)

### Requirement 19: Runtime Action

**User Story:** As a runtime module developer, I want a ROS2 action definition for calling skills, so that the skill orchestrator can invoke skills with progress feedback and cancellation support.

#### Acceptance Criteria

1. THE Package SHALL define `CallSkill.action` with goal fields (`string skill_call_id`, `string skill_name`, `string task_id`, `string inputs_json`, `string constraints_json`, `int32 timeout_ms`), result fields (`string status`, `string outputs_json`, `string failure_code`, `string failure_message`), and feedback fields (`string phase`, `float64 progress`, `string status_message`)

### Requirement 20: Field Documentation

**User Story:** As a RoboWeave developer, I want every field in every IDL_File to have a comment explaining its purpose, so that the message definitions are self-documenting and new contributors can understand the interfaces without consulting external documentation.

#### Acceptance Criteria

1. FOR ALL IDL_Files in the Package, every field declaration SHALL be preceded or accompanied by a comment describing the field purpose and expected values
2. WHEN a field uses an enumerated string value (such as `safety_level` or `action_type`), THE comment SHALL list the valid values

### Requirement 21: Naming Convention Compliance

**User Story:** As a RoboWeave developer, I want all message, service, and action names to follow the naming conventions from the architecture spec, so that the ROS2 interface names are consistent with the topic and service naming scheme.

#### Acceptance Criteria

1. THE Package SHALL use CamelCase for all `.msg`, `.srv`, and `.action` file names
2. THE Package SHALL use `snake_case` for all field names within IDL_Files
3. WHEN a message is used on a ROS2 topic, THE message name SHALL match the topic type referenced in the architecture spec Section 6.3

### Requirement 22: Pydantic Model Field Parity

**User Story:** As a RoboWeave developer, I want each ROS2 message to have field-level parity with its corresponding Pydantic model, so that lossless round-trip conversion between Pydantic and ROS2 msg is possible.

#### Acceptance Criteria

1. FOR ALL message types that have a corresponding Pydantic_Model in `roboweave_interfaces`, the ROS2 message SHALL contain one field per Pydantic field with a semantically equivalent ROS2 IDL type
2. WHEN a Pydantic field uses `list[float]` for a 3D position, THE corresponding ROS2 message SHALL use `geometry_msgs/Point` or `float64[3]` as appropriate
3. WHEN a Pydantic field uses `SE3` (position + quaternion), THE corresponding ROS2 message SHALL use `geometry_msgs/Pose`
4. WHEN a Pydantic field uses `dict[str, Any]` for extensible data, THE corresponding ROS2 message SHALL use a `string` field carrying JSON (wrapped in JsonEnvelope_Msg where applicable)
5. WHEN a Pydantic field uses an `Enum` type, THE corresponding ROS2 message SHALL use a `string` field with a comment listing valid values
6. FOR ALL Pydantic_Models that inherit from `VersionedModel`, the corresponding ROS2 message SHALL include a `string schema_version` field
