# Implementation Plan: roboweave-msgs

## Overview

Create the `roboweave_msgs` ROS2 ament_cmake interface package containing 25 `.msg`, 19 `.srv`, and 5 `.action` IDL files. The package has no executable code — only IDL definitions compiled by `rosidl_generate_interfaces`. Tasks are ordered so that base messages are created first (since services and actions reference them), followed by services, actions, and finally build verification.

**Note:** This package requires a ROS2 environment to build. If ROS2 is not available, create all IDL files but skip the `colcon build` step.

## Tasks

- [x] 1. Set up package scaffolding
  - [x] 1.1 Create `roboweave_msgs/package.xml` with ament_cmake build type
    - Declare `buildtool_depend` on `ament_cmake` and `rosidl_default_generators`
    - Declare `depend` on `std_msgs`, `geometry_msgs`, `sensor_msgs`, `trajectory_msgs`, `action_msgs`
    - Declare `exec_depend` on `rosidl_default_runtime`
    - Add `member_of_group` for `rosidl_interface_packages`
    - _Requirements: 1.2, 1.5_

  - [x] 1.2 Create `roboweave_msgs/CMakeLists.txt` with rosidl_generate_interfaces
    - Use `cmake_minimum_required(VERSION 3.8)` and `project(roboweave_msgs)`
    - `find_package` for all dependencies
    - List all 25 msg, 19 srv, and 5 action files in `rosidl_generate_interfaces`
    - Call `ament_package()` at the end
    - _Requirements: 1.1, 1.3_

  - [x] 1.3 Create empty directory structure: `msg/`, `srv/`, `action/`
    - _Requirements: 1.3_

- [x] 2. Create DataRef message family (msg/)
  - [x] 2.1 Create `msg/DataRef.msg` — base reference message
    - Fields: `schema_version`, `uri`, `timestamp`, `frame_id`, `valid_until`, `source_module`
    - Every field must have a preceding comment describing purpose and valid values
    - _Requirements: 2.1, 20.1, 22.6_

  - [x] 2.2 Create `msg/ImageRef.msg` — image reference
    - All DataRef fields plus `encoding`, `width`, `height`
    - Comment on `encoding` must list valid values: "rgb8", "bgr8", "16UC1", "32FC1"
    - _Requirements: 2.2, 20.1, 20.2_

  - [x] 2.3 Create `msg/DepthRef.msg` — depth image reference
    - All DataRef fields plus `encoding`, `width`, `height`, `depth_unit`
    - Comment on `depth_unit` must list valid values: "mm", "m"
    - _Requirements: 2.3, 20.1, 20.2_

  - [x] 2.4 Create `msg/PointCloudRef.msg` — point cloud reference
    - All DataRef fields plus `num_points`, `has_color`, `has_normals`, `format`
    - Comment on `format` must list valid values: "ply", "pcd", "ros_pc2"
    - _Requirements: 2.4, 20.1, 20.2_

  - [x] 2.5 Create `msg/MaskRef.msg` — segmentation mask reference
    - All DataRef fields plus `object_id`, `mask_confidence`, `pixel_count`
    - _Requirements: 2.5, 20.1_

  - [x] 2.6 Create `msg/TrajectoryRef.msg` — trajectory reference
    - All DataRef fields plus `num_points`, `duration_sec`, `arm_id`
    - _Requirements: 2.6, 20.1_

  - [x] 2.7 Create `msg/WorldStateRef.msg` — world state snapshot reference
    - All DataRef fields plus `num_objects`, `robot_id`
    - _Requirements: 2.7, 20.1_

  - [x] 2.8 Create `msg/JsonEnvelope.msg` — JSON transport wrapper
    - Fields: `schema_name`, `schema_version`, `payload_json`, `payload_hash`
    - Comment on `payload_hash` must note SHA-256 hex digest
    - _Requirements: 3.1, 20.1_

- [x] 3. Create Detection and Perception messages (msg/)
  - [x] 3.1 Create `msg/Detection.msg` — single object detection result
    - Fields: `object_id`, `category`, `matched_query`, `bbox_2d` (int32[]), `confidence`, `pose_camera` (geometry_msgs/Pose), `header` (std_msgs/Header)
    - _Requirements: 4.1, 20.1, 22.1_

  - [x] 3.2 Create `msg/BoundingBox3D.msg` — 3D bounding box
    - Fields: `center` (geometry_msgs/Pose), `size` (float64[3])
    - _Requirements: 4.2, 20.1_

  - [x] 3.3 Create `msg/GraspConstraints.msg` — grasp planning constraints
    - Fields: `preferred_regions`, `avoid_regions`, `max_force`, `min_gripper_width`, `max_gripper_width`, `approach_direction_hint`
    - _Requirements: 4.3, 20.1_

  - [x] 3.4 Create `msg/GraspCandidate.msg` — candidate grasp with quality metrics
    - Fields: `grasp_id`, `grasp_pose` (geometry_msgs/Pose), `approach_direction`, `gripper_width`, `grasp_score`, `collision_score`, `reachable`, `matched_regions`, `ik_solution`
    - _Requirements: 4.4, 20.1_

  - [x] 3.5 Create `msg/ReachabilityResult.msg` — IK reachability check result
    - Fields: `reachable`, `failure_code`, `ik_solution`, `manipulability`
    - Comment on `failure_code` must list valid values
    - _Requirements: 4.5, 20.1, 20.2_

  - [x] 3.6 Create `msg/CollisionPair.msg` — collision pair
    - Fields: `object_a`, `object_b`, `min_distance`, `contact_point` (geometry_msgs/Point)
    - _Requirements: 4.6, 20.1_

- [x] 4. Create Safety and Control messages (msg/)
  - [x] 4.1 Create `msg/VLASafetyConstraints.msg` — VLA safety constraints
    - Fields: `max_velocity`, `max_angular_velocity`, `force_limit`, `torque_limit`, `workspace_limit_id`, `max_duration_sec`, `allow_contact`, `min_confidence_threshold`
    - _Requirements: 5.1, 20.1_

  - [x] 4.2 Create `msg/SafetyStatus.msg` — safety supervisor status
    - Fields: `header` (std_msgs/Header), `safety_level`, `e_stop_active`, `e_stop_latched`, `collision_detected`, `min_human_distance` (float32), `active_violations`, `active_safe_zones`, `last_heartbeat`
    - Comment on `safety_level` must list valid values: "normal", "warning", "critical", "emergency_stop"
    - _Requirements: 5.2, 20.1, 20.2_

  - [x] 4.3 Create `msg/ArmState.msg` — single arm state
    - Fields: `arm_id`, `joint_positions`, `joint_velocities`, `joint_efforts`, `eef_pose` (geometry_msgs/Pose), `manipulability`
    - _Requirements: 5.4, 20.1_

  - [x] 4.4 Create `msg/GripperState.msg` — single gripper state
    - Fields: `gripper_id`, `type`, `width`, `force`, `is_grasping`, `grasped_object_id`
    - Comment on `type` must list valid values: "parallel", "vacuum", "soft"
    - _Requirements: 5.5, 20.1, 20.2_

  - [x] 4.5 Create `msg/RobotStateMsg.msg` — complete robot state
    - Fields: `robot_id`, `arms` (ArmState[]), `grippers` (GripperState[]), `base_pose` (geometry_msgs/Pose), `is_moving`, `current_control_mode`
    - Comment on `current_control_mode` must list valid values: "position", "velocity", "effort", "impedance"
    - Must be created after ArmState.msg and GripperState.msg since it references them
    - _Requirements: 5.3, 20.1, 20.2_

- [x] 5. Create Runtime messages (msg/)
  - [x] 5.1 Create `msg/TaskStatus.msg` — task execution status
    - Fields: `task_id`, `status`, `progress`, `current_node_id`, `failure_code`, `message`
    - Comment on `status` must list valid values: "pending", "running", "paused", "succeeded", "failed", "cancelled"
    - _Requirements: 6.1, 20.1, 20.2_

  - [x] 5.2 Create `msg/ExecutionEvent.msg` — structured execution event
    - Fields: `event_id`, `task_id`, `node_id`, `event_type`, `failure_code`, `severity`, `message`, `recovery_candidates`, `timestamp`
    - Comments on `event_type` and `severity` must list valid values
    - _Requirements: 6.2, 20.1, 20.2_

  - [x] 5.3 Create `msg/WorldStateUpdate.msg` — incremental world state update
    - Fields: `header` (std_msgs/Header), `update_type`, `object_id`, `payload_json`
    - Comment on `update_type` must list valid values: "object_added", "object_updated", "object_removed", "full_refresh"
    - _Requirements: 6.3, 20.1, 20.2_

  - [x] 5.4 Create `msg/WorldStateStamped.msg` — full world state snapshot
    - Fields: `header` (std_msgs/Header), `world_state_json`
    - _Requirements: 6.4, 20.1_

- [x] 6. Create HITL messages (msg/)
  - [x] 6.1 Create `msg/HITLRequestMsg.msg` — HITL intervention request
    - Fields: `request_json`
    - _Requirements: 7.1, 20.1_

  - [x] 6.2 Create `msg/TeleopCommand.msg` — teleoperation command
    - Fields: `header` (std_msgs/Header), `arm_id`, `twist` (geometry_msgs/Twist), `gripper_action`
    - Comment on `gripper_action` must list valid values: "open", "close", "none"
    - _Requirements: 7.2, 20.1, 20.2_

- [x] 7. Checkpoint — Verify all 25 message files created
  - Ensure all 25 `.msg` files exist in `msg/` directory with correct field definitions and comments
  - Ensure all files follow CamelCase naming and all fields use snake_case
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Create Perception services (srv/)
  - [x] 8.1 Create `srv/DetectObjects.srv` — object detection service
    - Request: `query`, `camera_id`, `rgb_ref` (ImageRef), `confidence_threshold`
    - Response: `detections` (Detection[]), `success`, `error_code`, `message`
    - _Requirements: 8.1, 20.1_

  - [x] 8.2 Create `srv/SegmentObject.srv` — object segmentation service
    - Request: `object_id`, `camera_id`, `rgb_ref` (ImageRef), `depth_ref` (DepthRef)
    - Response: `mask_ref` (MaskRef), `success`, `error_code`, `message`
    - _Requirements: 8.2, 20.1_

  - [x] 8.3 Create `srv/BuildPointCloud.srv` — point cloud building service
    - Request: `object_id`, `depth_ref` (DepthRef), `mask_ref` (MaskRef)
    - Response: `point_cloud_ref` (PointCloudRef), `bbox_3d` (BoundingBox3D), `success`, `error_code`, `message`
    - _Requirements: 8.3, 20.1_

  - [x] 8.4 Create `srv/EstimatePose.srv` — pose estimation service
    - Request: `object_id`, `point_cloud_ref` (PointCloudRef), `method`
    - Response: `pose` (geometry_msgs/PoseStamped), `confidence`, `covariance` (float64[]), `success`, `error_code`, `message`
    - Comment on `method` must list valid values: "icp", "feature_matching", "learned"
    - _Requirements: 8.4, 20.1, 20.2_

- [x] 9. Create Planning services (srv/)
  - [x] 9.1 Create `srv/PlanGrasp.srv` — grasp planning service
    - Request: `object_id`, `point_cloud_ref` (PointCloudRef), `constraints` (GraspConstraints), `arm_id`
    - Response: `candidates` (GraspCandidate[]), `success`, `error_code`, `message`
    - _Requirements: 9.1, 20.1_

  - [x] 9.2 Create `srv/CheckReachability.srv` — IK reachability check service
    - Request: `target_pose` (geometry_msgs/Pose), `arm_id`, `current_joint_state` (float64[])
    - Response: `result` (ReachabilityResult), `success`, `error_code`, `message`
    - _Requirements: 9.2, 20.1_

  - [x] 9.3 Create `srv/CheckCollision.srv` — collision check service
    - Request: `joint_state` (float64[]), `arm_id`, `ignore_objects` (string[])
    - Response: `in_collision`, `collision_pairs` (CollisionPair[]), `success`, `error_code`, `message`
    - _Requirements: 9.3, 20.1_

- [x] 10. Create Control services (srv/)
  - [x] 10.1 Create `srv/GripperCommand.srv` — gripper command service
    - Request: `gripper_id`, `action`, `width`, `force`, `speed`
    - Response: `success`, `achieved_width`, `error_code`, `message`
    - Comment on `action` must list valid values: "open", "close", "move_to_width"
    - _Requirements: 10.1, 20.1, 20.2_

  - [x] 10.2 Create `srv/SafetyControl.srv` — safety control command service
    - Request: `action`, `operator_id`, `params_json`
    - Response: `success`, `message`
    - Comment on `action` must list valid values: "emergency_stop", "release_stop", "enter_safe_mode", "set_speed_limit", "set_force_limit", "set_workspace"
    - _Requirements: 10.2, 20.1, 20.2_

- [x] 11. Create Runtime services (srv/)
  - [x] 11.1 Create `srv/DispatchPlan.srv` — task plan dispatch service
    - Request: `task_id`, `plan_json`
    - Response: `accepted`, `message`
    - _Requirements: 11.1, 20.1_

  - [x] 11.2 Create `srv/TaskControl.srv` — task control service
    - Request: `task_id`, `action`
    - Response: `success`, `message`
    - Comment on `action` must list valid values: "pause", "resume", "cancel"
    - _Requirements: 11.2, 20.1, 20.2_

  - [x] 11.3 Create `srv/UpdateWorldState.srv` — world state update service
    - Request: `update_type`, `object_id`, `payload_json`
    - Response: `success`, `message`
    - Comment on `update_type` must list valid values: "object_added", "object_updated", "object_removed", "full_refresh"
    - _Requirements: 11.3, 20.1, 20.2_

  - [x] 11.4 Create `srv/QueryWorldState.srv` — world state query service
    - Request: `query_type`, `object_id`
    - Response: `result_json`, `success`, `message`
    - Comment on `query_type` must list valid values: "full", "object", "robot", "environment"
    - _Requirements: 11.4, 20.1, 20.2_

  - [x] 11.5 Create `srv/ListSkills.srv` — skill listing service
    - Request: `category_filter`
    - Response: `skill_names`, `skill_descriptors_json`, `success`
    - Comment on `category_filter` must list valid values: "perception", "planning", "vla", "control", "composite", "" (all)
    - _Requirements: 11.5, 20.1, 20.2_

  - [x] 11.6 Create `srv/SkillHealth.srv` — skill health query service
    - Request: `skill_name`
    - Response: `status`, `diagnostics_json`, `success`
    - Comment on `status` must list valid values: "healthy", "degraded", "unavailable"
    - _Requirements: 11.6, 20.1, 20.2_

  - [x] 11.7 Create `srv/RequestRecovery.srv` — recovery request service
    - Request: `task_id`, `failure_code`, `context_json`
    - Response: `recovery_action_json`, `success`, `message`
    - _Requirements: 11.7, 20.1_

- [x] 12. Create Data/Episode and Safety/HITL services (srv/)
  - [x] 12.1 Create `srv/EpisodeControl.srv` — episode recording lifecycle service
    - Request: `action`, `episode_id`, `task_id`, `labels_json`
    - Response: `episode_id`, `success`, `message`
    - Comment on `action` must list valid values: "start", "stop", "pause", "resume", "label"
    - _Requirements: 12.1, 20.1, 20.2_

  - [x] 12.2 Create `srv/GetSystemVersions.srv` — system version query service
    - Empty request section
    - Response: `versions_json`, `success`
    - _Requirements: 12.2, 20.1_

  - [x] 12.3 Create `srv/FilterVLAAction.srv` — VLA action safety filter service
    - Request: `vla_action_json`, `safety_constraints_json`, `arm_id`
    - Response: `approved`, `filtered_action_json`, `rejection_reason`, `violation_type`
    - _Requirements: 13.1, 20.1_

  - [x] 12.4 Create `srv/HITLRespond.srv` — HITL response service
    - Request: `response_json`
    - Response: `accepted`, `message`
    - _Requirements: 14.1, 20.1_

- [x] 13. Checkpoint — Verify all 19 service files created
  - Ensure all 19 `.srv` files exist in `srv/` directory with correct request/response fields and comments
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Create Action definitions (action/)
  - [x] 14.1 Create `action/PlanMotion.action` — motion planning action
    - Goal: `arm_id`, `goal_pose` (geometry_msgs/Pose), `goal_joint_state`, `planning_mode`, `max_velocity_scaling`, `max_acceleration_scaling`, `ignore_collision_objects`, `max_planning_time_ms`
    - Result: `trajectory` (trajectory_msgs/JointTrajectory), `duration_sec`, `collision_free`, `failure_code`, `message`
    - Feedback: `status`, `progress`
    - Comment on `planning_mode` must list valid values: "joint_space", "cartesian", "cartesian_linear"
    - _Requirements: 15.1, 20.1, 20.2_

  - [x] 14.2 Create `action/TrackPose.action` — pose tracking action
    - Goal: `object_id`, `camera_id`, `tracking_frequency_hz`
    - Result: `final_status`, `error_code`, `message`
    - Feedback: `current_pose` (geometry_msgs/PoseStamped), `confidence`, `tracking_age_sec`
    - Comment on `final_status` must list valid values: "completed", "lost", "cancelled"
    - _Requirements: 16.1, 20.1, 20.2_

  - [x] 14.3 Create `action/RunVLASkill.action` — VLA skill execution action
    - Goal: `skill_name`, `instruction`, `arm_id`, `safety_constraints` (VLASafetyConstraints), `max_steps`, `timeout_sec`
    - Result: `status`, `failure_code`, `message`, `steps_executed`
    - Feedback: `current_step`, `confidence`, `action_type`, `status`
    - Comments on result `status`, feedback `action_type`, and feedback `status` must list valid values
    - _Requirements: 17.1, 20.1, 20.2_

  - [x] 14.4 Create `action/ExecuteTrajectory.action` — trajectory execution action
    - Goal: `arm_id`, `trajectory` (trajectory_msgs/JointTrajectory), `velocity_scaling`, `monitor_force`
    - Result: `success`, `error_code`, `message`, `max_tracking_error`
    - Feedback: `progress`, `tracking_error`, `current_joint_positions`
    - _Requirements: 18.1, 20.1_

  - [x] 14.5 Create `action/CallSkill.action` — skill invocation action
    - Goal: `skill_call_id`, `skill_name`, `task_id`, `inputs_json`, `constraints_json`, `timeout_ms`
    - Result: `status`, `outputs_json`, `failure_code`, `failure_message`
    - Feedback: `phase`, `progress`, `status_message`
    - Comments on result `status` and feedback `phase` must list valid values
    - _Requirements: 19.1, 20.1, 20.2_

- [x] 15. Checkpoint — Verify all IDL files and attempt build
  - Verify all 25 msg, 19 srv, and 5 action files exist with correct content
  - If ROS2 environment is available, run `colcon build --packages-select roboweave_msgs` and verify exit code 0
  - If ROS2 is not available, verify file structure and content only
  - Ensure all tests pass, ask the user if questions arise.
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ]* 16. Write property test for naming convention compliance
  - **Property 3: Naming Convention Compliance**
  - Write a Python test that parses all IDL files and verifies:
    - All file names match CamelCase pattern `^[A-Z][a-zA-Z0-9]*\.(msg|srv|action)$`
    - All field names match snake_case pattern `^[a-z][a-z0-9_]*$`
  - **Validates: Requirements 21.1, 21.2**

- [ ]* 17. Write property test for field documentation completeness
  - **Property 2: Field Documentation Completeness**
  - Write a Python test that parses all IDL files and verifies:
    - Every field declaration has an associated comment (preceding line)
    - Fields representing enumerated string values have comments listing valid values
  - **Validates: Requirements 20.1, 20.2**

- [ ]* 18. Write property test for Pydantic–ROS2 field parity
  - **Property 1: Pydantic–ROS2 Field Parity**
  - Write a Python test that introspects `roboweave_interfaces` Pydantic models and compares against corresponding `.msg` files
  - Verify 1:1 field correspondence using the type mapping table from the design document
  - **Validates: Requirements 2.8, 22.1, 22.2, 22.3, 22.4, 22.5, 22.6**

- [x] 19. Final checkpoint — Ensure all files are complete and correct
  - Verify all 49 IDL files (25 msg + 19 srv + 5 action) are present and well-formed
  - Verify CMakeLists.txt lists all 49 files in rosidl_generate_interfaces
  - Verify package.xml has all required dependencies
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each major group of IDL files
- This is a pure IDL package — no Python source code, only `.msg`, `.srv`, `.action` files plus build configuration
- If ROS2 is not available in the build environment, all IDL files should still be created; only the `colcon build` verification step should be skipped
- Property tests validate universal correctness properties across all IDL files
- ArmState.msg and GripperState.msg must be created before RobotStateMsg.msg (task ordering handles this)
