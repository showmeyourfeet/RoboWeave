# Implementation Plan: roboweave-planning

## Overview

Implement the `roboweave_planning` ROS2 ament_python package following the same structure as `roboweave_control`. Tasks proceed bottom-up: package scaffolding → internal dataclasses → abstract interfaces → backend registry → mock/simple backends → converters → PlanningNode → configuration/launch → tests. Each task builds on the previous, and property-based tests are placed close to the code they validate.

## Tasks

- [ ] 1. Scaffold the roboweave_planning package
  - [ ] 1.1 Create package directory structure and boilerplate files
    - Create `roboweave_planning/` top-level directory with `setup.py`, `setup.cfg`, `package.xml`, `resource/roboweave_planning` marker file
    - Create inner `roboweave_planning/roboweave_planning/__init__.py`
    - Create `roboweave_planning/roboweave_planning/backends/__init__.py`
    - Create `roboweave_planning/tests/__init__.py` and `roboweave_planning/tests/conftest.py`
    - Create `roboweave_planning/config/` and `roboweave_planning/launch/` directories with `.gitkeep` files
    - Mirror `roboweave_control` package layout: `setup.py` with ament data_files, `package.xml` with rclpy/roboweave_msgs/geometry_msgs/trajectory_msgs/roboweave_interfaces dependencies, `setup.cfg` with install scripts path
    - Entry point: `planning_node = roboweave_planning.planning_node:main`
    - _Requirements: 5.1, 12.1, 12.2, 13.1_

- [ ] 2. Define internal dataclasses and abstract interfaces
  - [ ] 2.1 Create IKResult and CollisionResult dataclasses, and the four abstract base classes
    - Create `ik_solver.py` with `IKResult` dataclass (`reachable`, `ik_solution`, `failure_code`, `manipulability`) and `IKSolver` ABC (`solve`, `get_backend_name`, `get_joint_count`)
    - Create `collision_checker.py` with `CollisionResult` dataclass (`in_collision`, `collision_pairs`) and `CollisionChecker` ABC (`check`, `get_backend_name`, `update_scene`)
    - Create `grasp_planner.py` with `GraspPlanner` ABC (`plan_grasps`, `get_backend_name`)
    - Create `motion_planner.py` with `MotionPlanner` ABC (`plan`, `get_backend_name`)
    - All ABCs use `abc.ABC` and `abc.abstractmethod`
    - Method signatures must match the design exactly (parameter types, return types)
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.4, 3.1, 3.2, 3.4, 4.1, 4.2_

- [ ] 3. Implement BackendRegistry
  - [ ] 3.1 Create the BackendRegistry singleton with decorator registration
    - Create `backend_registry.py` with capability constants (`GRASP_PLANNER`, `IK_SOLVER`, `COLLISION_CHECKER`, `MOTION_PLANNER`)
    - Implement `_CAPABILITY_ABCS` mapping from capability name to ABC class
    - Implement `BackendRegistry` as a singleton with `get_instance()`, `register()`, `get_backend()`, `list_backends()`
    - `register()` must validate the class is a subclass of the correct ABC, raising `TypeError` if not
    - `get_backend()` must raise `KeyError` listing available backends if name not found
    - Implement `register_backend(capability, name)` decorator for import-time registration
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [ ]* 3.2 Write property tests for BackendRegistry
    - **Property 10: Backend registry register-then-retrieve identity**
    - **Validates: Requirements 11.1, 11.2**

  - [ ]* 3.3 Write property test for BackendRegistry ABC rejection
    - **Property 11: Backend registry rejects non-conforming classes**
    - **Validates: Requirements 11.3**

  - [ ]* 3.4 Write unit tests for BackendRegistry
    - Test `get_backend` with unknown name raises `KeyError` with available backends listed
    - Test decorator registration mechanism
    - Test `list_backends` returns registered names
    - _Requirements: 11.4, 11.5_

- [ ] 4. Checkpoint - Verify interfaces and registry
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement mock and simple backends
  - [ ] 5.1 Implement MockGraspPlanner backend
    - Create `backends/mock_grasp_planner.py`
    - Register with `@register_backend(GRASP_PLANNER, "mock")`
    - `plan_grasps`: return empty list for empty point cloud; for non-empty, return one `GraspCandidate` at centroid with approach `[0,0,-1]`, gripper_width `0.05`, grasp_score `0.8`, collision_score `1.0`
    - If `constraints.approach_direction_hint` is non-empty, use it as approach direction
    - `get_backend_name`: return `"mock"`
    - _Requirements: 1.3, 1.4, 1.5_

  - [ ]* 5.2 Write property tests for MockGraspPlanner
    - **Property 1: Grasp candidates are ranked by score descending**
    - **Validates: Requirements 1.1**
    - **Property 2: Mock grasp pose is positioned at point cloud centroid**
    - **Validates: Requirements 1.3**
    - **Property 3: Approach direction hint overrides default**
    - **Validates: Requirements 1.5**

  - [ ] 5.3 Implement MockIKSolver backend
    - Create `backends/mock_ik_solver.py`
    - Register with `@register_backend(IK_SOLVER, "mock")`
    - `solve`: return `IKResult(reachable=True, ik_solution=[0.0]*6, failure_code="", manipulability=0.5)`
    - `get_backend_name`: return `"mock"`
    - `get_joint_count`: return `6`
    - _Requirements: 2.3, 2.5_

  - [ ]* 5.4 Write property test for MockIKSolver
    - **Property 4: Mock IK solver returns deterministic result for any pose**
    - **Validates: Requirements 2.3**

  - [ ] 5.5 Implement MockCollisionChecker backend
    - Create `backends/mock_collision_checker.py`
    - Register with `@register_backend(COLLISION_CHECKER, "mock")`
    - `check`: return `CollisionResult(in_collision=False, collision_pairs=[])`
    - `get_backend_name`: return `"mock"`
    - `update_scene`: accept call, store no state
    - _Requirements: 3.3, 3.5_

  - [ ]* 5.6 Write property test for MockCollisionChecker
    - **Property 5: Mock collision checker reports no collision for any joint state**
    - **Validates: Requirements 3.3**

  - [ ] 5.7 Implement SimpleMotionPlanner backend
    - Create `backends/simple_motion_planner.py`
    - Register with `@register_backend(MOTION_PLANNER, "simple")`
    - Constructor accepts `IKSolver` instance and config params (`num_interpolation_points`, `max_joint_velocity`)
    - `plan` with `joint_space` mode: linearly interpolate between current and goal joint states, produce at least 10 points, compute `time_from_start_sec` based on `max_velocity_scaling`, set `collision_free=True`
    - `plan` with `cartesian`/`cartesian_linear` mode: call `IKSolver.solve()` first, then interpolate; return `IK_NO_SOLUTION` failure if IK fails
    - Return `MOT_NO_GOAL` failure if no goal provided
    - Velocity: constant `(q_g[j] - q_s[j]) / T` per joint; accelerations: all zeros
    - Duration: `max_j(|q_g[j] - q_s[j]|) / (max_joint_velocity * max_velocity_scaling)`
    - First point: positions = start, time = 0.0; last point: positions = goal
    - `get_backend_name`: return `"simple"`
    - _Requirements: 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

  - [ ]* 5.8 Write property tests for SimpleMotionPlanner
    - **Property 6: Simple motion planner produces valid trajectory structure**
    - **Validates: Requirements 4.3, 4.5**
    - **Property 7: Trajectory duration scales inversely with velocity scaling**
    - **Validates: Requirements 4.4**
    - **Property 8: Cartesian planning trajectory ends at IK solution**
    - **Validates: Requirements 4.7**

  - [ ]* 5.9 Write property tests for linear interpolation correctness
    - **Property 12: Linear interpolation correctness with boundary conditions**
    - **Validates: Requirements 14.1, 14.5, 14.6**
    - **Property 13: Trajectory velocity and acceleration consistency**
    - **Validates: Requirements 14.2, 14.3**
    - **Property 14: Trajectory duration follows displacement formula**
    - **Validates: Requirements 14.4**

  - [ ]* 5.10 Write unit tests for backend edge cases
    - Test empty point cloud returns empty list (Req 1.4)
    - Test no goal returns `MOT_NO_GOAL` (Req 4.6)
    - Test IK unreachable returns `IK_NO_SOLUTION` (Req 4.8)
    - Test mock backend name strings (Req 1.2, 2.2, 3.2, 4.2)
    - Test mock IK joint count returns 6 (Req 2.4, 2.5)
    - Test mock collision `update_scene` accepts without error (Req 3.4, 3.5)
    - _Requirements: 1.2, 1.4, 2.2, 2.4, 2.5, 3.2, 3.4, 3.5, 4.2, 4.6, 4.8_

  - [ ] 5.11 Update `backends/__init__.py` to import all backend modules
    - Import `mock_grasp_planner`, `mock_ik_solver`, `mock_collision_checker`, `simple_motion_planner` to trigger registration decorators
    - _Requirements: 11.5_

- [ ] 6. Checkpoint - Verify backends and registry integration
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement Pydantic ↔ ROS2 message converters
  - [ ] 7.1 Create planning converters module
    - Create `converters.py` following the `roboweave_control/converters.py` dict-fallback pattern with `HAS_ROS2` guard
    - Implement `grasp_candidate_to_msg` / `msg_to_grasp_candidate` (GraspCandidate ↔ GraspCandidate.msg dict)
    - Implement `grasp_constraints_to_msg` / `msg_to_grasp_constraints` (GraspConstraints ↔ GraspConstraints.msg dict)
    - Implement `se3_to_pose_dict` / `pose_dict_to_se3` (SE3 ↔ geometry_msgs/Pose dict) — local copy for package independence
    - Implement `trajectory_result_to_joint_trajectory` / `joint_trajectory_to_trajectory_result` (TrajectoryResult ↔ trajectory_msgs/JointTrajectory dict)
    - Implement `ik_result_to_reachability_msg` / `reachability_msg_to_ik_result` (IKResult ↔ ReachabilityResult.msg dict)
    - Implement `collision_result_to_msg` / `msg_to_collision_result` (CollisionResult ↔ CollisionPair.msg[] dict)
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ]* 7.2 Write property tests for converter round-trips
    - **Property 9: Converter round-trip preserves planning models**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6**

- [ ] 8. Implement PlanningNode
  - [ ] 8.1 Create PlanningNode with backend initialization and service/action servers
    - Create `planning_node.py` with `HAS_ROS2` fallback pattern matching `ControlNode`
    - Load `planning_params.yaml` and `planning_backends.yaml` from ROS2 parameter file paths
    - Instantiate backends via `BackendRegistry.get_backend()`, falling back to mock if not found
    - Pass `IKSolver` instance to `SimpleMotionPlanner` constructor
    - Log active backend names on startup
    - Host service servers: `/roboweave/planning/plan_grasp`, `/roboweave/planning/check_reachability`, `/roboweave/planning/check_collision`
    - Host action server: `/roboweave/planning/plan_motion`
    - Implement `main()` entry point
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [ ] 8.2 Implement PlanGrasp service handler
    - Resolve point cloud from `point_cloud_ref` field
    - Call `GraspPlanner.plan_grasps()` with resolved point cloud, object_id, constraints, arm_id
    - Convert returned `GraspCandidate` models to ROS2 msg dicts via converters
    - Return `success=false` with `GRP_NO_GRASP_FOUND` if empty list
    - Return `success=false` with `GRP_PLANNING_FAILED` on exception
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ] 8.3 Implement CheckReachability service handler
    - Convert `target_pose` to `SE3` Pydantic model via converter
    - Call `IKSolver.solve()` with SE3, arm_id, and current_joint_state as seed
    - Convert `IKResult` to `ReachabilityResult` msg dict via converter
    - Return `success=false` with `IK_SOLVER_FAILED` on exception
    - _Requirements: 7.1, 7.2, 7.3_

  - [ ] 8.4 Implement CheckCollision service handler
    - Call `CollisionChecker.check()` with joint_state, arm_id, ignore_objects
    - Convert `CollisionResult` to `CollisionPair` msg dicts via converter
    - Return `success=false` with `COL_CHECK_FAILED` on exception
    - _Requirements: 8.1, 8.2, 8.3_

  - [ ] 8.5 Implement PlanMotion action handler
    - Construct `MotionRequest` from goal fields (arm_id, goal_pose, goal_joint_state, planning_mode, scaling factors, ignore list, max_planning_time_ms)
    - Call `MotionPlanner.plan()` with MotionRequest and current joint state
    - Publish feedback with status string and progress 0.0–1.0
    - Convert `TrajectoryResult` to `trajectory_msgs/JointTrajectory` msg dict
    - Return failure info and empty trajectory if failure_code is non-empty
    - Handle cancel requests by aborting and returning cancelled result
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [ ]* 8.6 Write unit tests for PlanningNode service handlers
    - Test plan_grasp handler returns error on empty result (Req 6.4)
    - Test plan_grasp handler returns error on exception (Req 6.5)
    - Test check_reachability handler returns error on exception (Req 7.3)
    - Test check_collision handler returns error on exception (Req 8.3)
    - Test plan_motion returns empty trajectory on failure (Req 9.5)
    - Test backend-not-found falls back to mock (Req 5.7)
    - _Requirements: 5.7, 6.4, 6.5, 7.3, 8.3, 9.5_

- [ ] 9. Checkpoint - Verify node and handlers
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Create configuration files and launch file
  - [ ] 10.1 Create planning_params.yaml and planning_backends.yaml
    - Create `config/planning_params.yaml` with: `max_planning_time_ms: 5000`, `default_velocity_scaling: 0.5`, `default_acceleration_scaling: 0.5`, `min_trajectory_points: 10`, `max_grasp_candidates: 5`, `max_joint_velocity: 1.5`
    - Create `config/planning_backends.yaml` with active backends: grasp_planner=mock, ik_solver=mock, collision_checker=mock, motion_planner=simple, each with params dict
    - _Requirements: 12.1, 12.2_

  - [ ] 10.2 Create planning.launch.py
    - Create `launch/planning.launch.py` that launches the PlanningNode
    - Accept launch arguments for planning params file path, planning backends file path, and arm_id
    - Pass arguments as ROS2 parameter overrides to the node
    - _Requirements: 13.1, 13.2, 13.3_

  - [ ]* 10.3 Write unit tests for configuration schema validation
    - Test planning_params.yaml contains all required keys
    - Test planning_backends.yaml contains all four capability entries with active and params keys
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [ ] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate the 14 universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All property tests use Hypothesis with `max_examples=100` and `deadline=None`
- All tests run without ROS2 dependency (pure Python, dict-based converters)
- The package mirrors `roboweave_control` conventions: ament_python build, dict-fallback converters, `HAS_ROS2` guard pattern
