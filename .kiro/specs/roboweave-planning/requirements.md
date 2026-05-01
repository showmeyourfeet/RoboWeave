# Requirements Document

## Introduction

The `roboweave_planning` package is the geometric planning layer of the RoboWeave hybrid robotics system. It provides grasp candidate generation, inverse kinematics and reachability analysis, collision detection, and motion trajectory planning. Each capability is exposed as a ROS2 service (grasp planning, reachability checking, collision checking) or action (motion planning), hosted by a single `PlanningNode`. A backend plugin system allows swapping implementations (e.g., mock → MoveIt2, mock → cuRobo) without changing the node or service interfaces.

This is Phase 2.2 of the RoboWeave project, building on the already-implemented `roboweave_interfaces` (Pydantic models: `GraspCandidate`, `GraspConstraints`, `MotionRequest`, `TrajectoryResult`, `TrajectoryPoint`, `SE3`) and `roboweave_msgs` (ROS2 msg/srv/action definitions: `PlanGrasp.srv`, `CheckReachability.srv`, `CheckCollision.srv`, `PlanMotion.action`).

The MVP target uses mock/simple backends only. Real planning backends (MoveIt2, cuRobo, analytical IK solvers) will be added in later phases.

## Glossary

- **Planning_Node**: The main ROS2 node that hosts all planning service and action servers, manages backend lifecycle, and loads configuration.
- **Grasp_Planner**: A component that generates ranked grasp candidates for a target object given its point cloud and grasp constraints.
- **IK_Solver**: A component that computes inverse kinematics solutions and evaluates reachability for a target end-effector pose.
- **Collision_Checker**: A component that checks whether a given joint configuration results in collisions with the environment or the robot itself.
- **Motion_Planner**: A component that plans a collision-free trajectory from the current joint state to a goal pose or joint configuration, exposed as a ROS2 action with progress feedback.
- **Backend**: A swappable implementation of a planning capability (Grasp_Planner, IK_Solver, Collision_Checker, Motion_Planner). Each backend conforms to an abstract interface and is selected via configuration.
- **Backend_Registry**: A configuration-driven mechanism that maps backend names to their implementing classes, allowing runtime selection of which backend to use for each capability.
- **Converter**: A set of functions that translate between `roboweave_interfaces` Pydantic models and `roboweave_msgs` ROS2 message types for the planning domain.
- **GraspCandidate**: A ROS2 message (and Pydantic model) representing a candidate grasp with 6-DOF pose, approach direction, gripper width, quality scores, and optional IK solution.
- **GraspConstraints**: A ROS2 message (and Pydantic model) specifying constraints for grasp planning including preferred/avoid regions, force limits, and gripper width bounds.
- **ReachabilityResult**: A ROS2 message containing whether a pose is reachable, the IK joint solution, failure code, and manipulability measure.
- **CollisionPair**: A ROS2 message representing a pair of objects in collision with minimum distance and contact point.
- **TrajectoryPoint**: A Pydantic model representing a single point in a joint trajectory with positions, velocities, accelerations, and time from start.
- **MotionRequest**: A Pydantic model encapsulating a motion planning request with goal pose/joints, planning mode, velocity/acceleration scaling, and constraints.
- **TrajectoryResult**: A Pydantic model encapsulating the result of motion planning with the trajectory, duration, collision-free status, and failure information.
- **planning_params.yaml**: A YAML configuration file defining runtime parameters for the Planning_Node (planning timeouts, velocity limits, default scaling factors).
- **planning_backends.yaml**: A YAML configuration file mapping each planning capability to its active backend name and backend-specific parameters.

## Requirements

### Requirement 1: Grasp Planner Abstract Interface and Mock Backend

**User Story:** As a robotics developer, I want a pluggable grasp planning interface with a working mock backend, so that I can develop and test the manipulation pipeline without requiring real grasp planning algorithms.

#### Acceptance Criteria

1. THE Grasp_Planner SHALL define an abstract method `plan_grasps` that accepts a point cloud (as a numpy array of shape Nx3), an object_id string, a `GraspConstraints` Pydantic model, and an arm_id string, and returns a list of `GraspCandidate` Pydantic models ranked by `grasp_score` in descending order.
2. THE Grasp_Planner SHALL define an abstract method `get_backend_name` that returns the string name of the active backend.
3. WHEN the mock Grasp_Planner backend receives a `plan_grasps` call with a non-empty point cloud, THE mock Grasp_Planner backend SHALL return a list containing one `GraspCandidate` with the grasp pose positioned at the centroid of the point cloud, an approach direction of [0, 0, -1], a gripper width of 0.05 meters, a grasp_score of 0.8, and a collision_score of 1.0.
4. IF the point cloud provided to `plan_grasps` is empty (zero points), THEN THE Grasp_Planner SHALL return an empty list.
5. IF the `GraspConstraints` specifies an `approach_direction_hint`, THE mock Grasp_Planner backend SHALL use that hint as the approach direction in the returned candidate instead of the default [0, 0, -1].

### Requirement 2: IK Solver Abstract Interface and Mock Backend

**User Story:** As a robotics developer, I want a pluggable inverse kinematics interface with a mock backend, so that I can test reachability checks and grasp validation without a real IK solver.

#### Acceptance Criteria

1. THE IK_Solver SHALL define an abstract method `solve` that accepts a target pose (`SE3` Pydantic model), an arm_id string, and an optional seed joint state (list of floats), and returns a `ReachabilityResult`-equivalent dataclass containing `reachable` (bool), `ik_solution` (list of floats), `failure_code` (string), and `manipulability` (float).
2. THE IK_Solver SHALL define an abstract method `get_backend_name` that returns the string name of the active backend.
3. WHEN the mock IK_Solver backend receives a `solve` call, THE mock IK_Solver backend SHALL return a result with `reachable=True`, an `ik_solution` of six zeros representing a 6-DOF identity joint configuration, an empty `failure_code`, and a `manipulability` of 0.5.
4. THE IK_Solver SHALL define an abstract method `get_joint_count` that returns the number of joints for the specified arm_id.
5. WHEN the mock IK_Solver backend `get_joint_count` is called, THE mock IK_Solver backend SHALL return 6.

### Requirement 3: Collision Checker Abstract Interface and Mock Backend

**User Story:** As a robotics developer, I want a pluggable collision checking interface with a mock backend, so that I can test motion planning validation without a real collision detection engine.

#### Acceptance Criteria

1. THE Collision_Checker SHALL define an abstract method `check` that accepts a joint state (list of floats), an arm_id string, and a list of object IDs to ignore, and returns a result containing `in_collision` (bool) and `collision_pairs` (list of collision pair tuples).
2. THE Collision_Checker SHALL define an abstract method `get_backend_name` that returns the string name of the active backend.
3. WHEN the mock Collision_Checker backend receives a `check` call, THE mock Collision_Checker backend SHALL return a result with `in_collision=False` and an empty `collision_pairs` list.
4. THE Collision_Checker SHALL define an abstract method `update_scene` that accepts a list of object states (object_id, pose, bounding box) to update the internal collision world representation.
5. WHEN the mock Collision_Checker backend `update_scene` is called, THE mock Collision_Checker backend SHALL accept the call without error and store no state.

### Requirement 4: Motion Planner Abstract Interface and Simple Backend

**User Story:** As a robotics developer, I want a pluggable motion planning interface with a simple linear interpolation backend, so that I can test the full pick-and-place pipeline with basic trajectory generation.

#### Acceptance Criteria

1. THE Motion_Planner SHALL define an abstract method `plan` that accepts a `MotionRequest` Pydantic model and a current joint state (list of floats), and returns a `TrajectoryResult` Pydantic model.
2. THE Motion_Planner SHALL define an abstract method `get_backend_name` that returns the string name of the active backend.
3. WHEN the simple Motion_Planner backend receives a `plan` call with `planning_mode` set to `joint_space` and a valid `goal_joint_state`, THE simple Motion_Planner backend SHALL generate a trajectory by linearly interpolating between the current joint state and the goal joint state, producing at least 10 evenly-spaced `TrajectoryPoint` entries.
4. WHEN the simple Motion_Planner backend generates a trajectory, THE simple Motion_Planner backend SHALL compute `time_from_start_sec` for each point based on the `max_velocity_scaling` factor, such that the total duration scales inversely with the velocity scaling.
5. WHEN the simple Motion_Planner backend generates a trajectory, THE simple Motion_Planner backend SHALL set `collision_free=True` in the result (no collision checking in the simple backend).
6. IF the `goal_joint_state` in the `MotionRequest` is empty and `goal_pose` is None, THEN THE Motion_Planner SHALL return a `TrajectoryResult` with an empty trajectory, `failure_code` set to `MOT_NO_GOAL`, and a descriptive message.
7. IF the `planning_mode` is `cartesian` or `cartesian_linear` and `goal_pose` is provided, THE simple Motion_Planner backend SHALL use the IK_Solver to convert the goal pose to a joint state, then perform linear interpolation in joint space.
8. IF the IK_Solver returns `reachable=False` during Cartesian planning, THEN THE Motion_Planner SHALL return a `TrajectoryResult` with an empty trajectory, `failure_code` set to `IK_NO_SOLUTION`, and a descriptive message.

### Requirement 5: Planning Node Lifecycle

**User Story:** As a system integrator, I want a single ROS2 node that initializes all planning backends, hosts all planning services and actions, and manages configuration, so that I can launch the planning subsystem with a single command.

#### Acceptance Criteria

1. THE Planning_Node SHALL load planning_params.yaml and planning_backends.yaml from file paths specified by ROS2 parameters.
2. THE Planning_Node SHALL instantiate the Grasp_Planner, IK_Solver, Collision_Checker, and Motion_Planner backends based on the backend names specified in planning_backends.yaml.
3. THE Planning_Node SHALL host the following ROS2 service servers: `/roboweave/planning/plan_grasp` (PlanGrasp), `/roboweave/planning/check_reachability` (CheckReachability), `/roboweave/planning/check_collision` (CheckCollision).
4. THE Planning_Node SHALL host the ROS2 action server `/roboweave/planning/plan_motion` (PlanMotion) via the Motion_Planner.
5. WHEN the Planning_Node starts, THE Planning_Node SHALL log the active backend name for each planning capability.
6. WHEN the Planning_Node shuts down, THE Planning_Node SHALL release all backend resources.
7. IF a backend specified in planning_backends.yaml is not found in the Backend_Registry, THEN THE Planning_Node SHALL log an error and fall back to the mock backend for that capability.

### Requirement 6: PlanGrasp Service Handler

**User Story:** As a skill developer, I want to call a ROS2 service to generate grasp candidates for a target object, so that the runtime can select and execute grasps during manipulation tasks.

#### Acceptance Criteria

1. WHEN a PlanGrasp request is received, THE Planning_Node SHALL resolve the point cloud from the `point_cloud_ref` field in the request.
2. WHEN a PlanGrasp request is received, THE Planning_Node SHALL call the Grasp_Planner `plan_grasps` method with the resolved point cloud, the `object_id`, the `constraints`, and the `arm_id` from the request.
3. WHEN the Grasp_Planner returns candidates, THE Planning_Node SHALL convert each `GraspCandidate` Pydantic model to a `GraspCandidate` ROS2 message and return them in the response with `success=true`.
4. IF the Grasp_Planner returns an empty list, THEN THE Planning_Node SHALL return a response with `success=false`, error_code `GRP_NO_GRASP_FOUND`, and a descriptive message.
5. IF the Grasp_Planner raises an exception, THEN THE Planning_Node SHALL return a response with `success=false`, error_code `GRP_PLANNING_FAILED`, and the exception message.

### Requirement 7: CheckReachability Service Handler

**User Story:** As a skill developer, I want to call a ROS2 service to check whether a target pose is reachable by the robot arm, so that the runtime can validate grasp candidates before attempting execution.

#### Acceptance Criteria

1. WHEN a CheckReachability request is received, THE Planning_Node SHALL call the IK_Solver `solve` method with the `target_pose` converted to an `SE3` Pydantic model, the `arm_id`, and the `current_joint_state` as seed.
2. WHEN the IK_Solver returns a result, THE Planning_Node SHALL convert the result to a `ReachabilityResult` ROS2 message and return it in the response with `success=true`.
3. IF the IK_Solver raises an exception, THEN THE Planning_Node SHALL return a response with `success=false`, error_code `IK_SOLVER_FAILED`, and the exception message.

### Requirement 8: CheckCollision Service Handler

**User Story:** As a skill developer, I want to call a ROS2 service to check whether a joint configuration is in collision, so that the runtime can validate planned trajectories and configurations.

#### Acceptance Criteria

1. WHEN a CheckCollision request is received, THE Planning_Node SHALL call the Collision_Checker `check` method with the `joint_state`, the `arm_id`, and the `ignore_objects` list from the request.
2. WHEN the Collision_Checker returns a result, THE Planning_Node SHALL populate the response with `in_collision`, the `collision_pairs` converted to ROS2 messages, and return with `success=true`.
3. IF the Collision_Checker raises an exception, THEN THE Planning_Node SHALL return a response with `success=false`, error_code `COL_CHECK_FAILED`, and the exception message.

### Requirement 9: PlanMotion Action Handler

**User Story:** As a skill developer, I want to call a ROS2 action to plan a motion trajectory, so that the runtime can generate collision-free paths for the robot arm to follow.

#### Acceptance Criteria

1. WHEN a PlanMotion goal is received, THE Planning_Node SHALL construct a `MotionRequest` Pydantic model from the goal fields (`arm_id`, `goal_pose`, `goal_joint_state`, `planning_mode`, `max_velocity_scaling`, `max_acceleration_scaling`, `ignore_collision_objects`, `max_planning_time_ms`).
2. WHEN a PlanMotion goal is received, THE Planning_Node SHALL call the Motion_Planner `plan` method with the constructed `MotionRequest` and the current joint state obtained from the robot state topic or parameter.
3. WHILE motion planning is in progress, THE Planning_Node SHALL publish feedback with the current `status` string and `progress` value between 0.0 and 1.0.
4. WHEN the Motion_Planner returns a `TrajectoryResult`, THE Planning_Node SHALL convert the trajectory to a `trajectory_msgs/JointTrajectory` ROS2 message and return the result with `duration_sec`, `collision_free`, `failure_code`, and `message`.
5. IF the Motion_Planner returns a result with a non-empty `failure_code`, THEN THE Planning_Node SHALL return the action result with the failure information and an empty trajectory.
6. WHEN a cancel request is received during motion planning, THE Planning_Node SHALL abort the planning computation and return a cancelled result.

### Requirement 10: Pydantic ↔ ROS2 Message Converters

**User Story:** As a developer, I want reliable conversion functions between Pydantic models and ROS2 messages for planning types, so that the planning node can interoperate with both the Pydantic-based interfaces package and the ROS2 message layer.

#### Acceptance Criteria

1. THE Converter SHALL provide a function to convert a `roboweave_interfaces.grasp.GraspCandidate` Pydantic model to a `roboweave_msgs/msg/GraspCandidate` ROS2 message and vice versa.
2. THE Converter SHALL provide a function to convert a `roboweave_interfaces.grasp.GraspConstraints` Pydantic model to a `roboweave_msgs/msg/GraspConstraints` ROS2 message and vice versa.
3. THE Converter SHALL provide a function to convert a `geometry_msgs/Pose` ROS2 message to a `roboweave_interfaces.world_state.SE3` Pydantic model and vice versa.
4. THE Converter SHALL provide a function to convert a `roboweave_interfaces.motion.TrajectoryResult` Pydantic model to a `trajectory_msgs/JointTrajectory` ROS2 message and vice versa.
5. THE Converter SHALL provide a function to convert a `roboweave_msgs/msg/ReachabilityResult` ROS2 message to the IK_Solver result dataclass and vice versa.
6. FOR ALL valid Pydantic planning models, converting to a ROS2 message and back SHALL produce an equivalent Pydantic model (round-trip property).

### Requirement 11: Backend Plugin System

**User Story:** As a robotics developer, I want a plugin system for planning backends, so that I can swap between mock, simple, and production planning implementations without modifying the planning node code.

#### Acceptance Criteria

1. THE Backend_Registry SHALL maintain a mapping from capability name (grasp_planner, ik_solver, collision_checker, motion_planner) and backend name to the implementing Python class.
2. THE Backend_Registry SHALL provide a `get_backend` method that accepts a capability name and a backend name and returns an instance of the corresponding backend class.
3. WHEN a backend name is registered for a capability, THE Backend_Registry SHALL verify that the class implements the required abstract interface for that capability.
4. IF `get_backend` is called with an unregistered backend name, THEN THE Backend_Registry SHALL raise a `KeyError` with a message listing the available backends for that capability.
5. THE Backend_Registry SHALL support registering new backends at import time via a decorator or explicit registration call, so that adding a new backend requires only creating a new module in the `backends/` directory.

### Requirement 12: Configuration Files

**User Story:** As a system integrator, I want well-defined YAML configuration files for planning parameters and backend selection, so that I can tune the planning subsystem and swap backends without code changes.

#### Acceptance Criteria

1. THE planning_params.yaml file SHALL define the default maximum planning time in milliseconds, the default velocity scaling factor, the default acceleration scaling factor, the minimum number of trajectory interpolation points, and the default number of grasp candidates to generate.
2. THE planning_backends.yaml file SHALL define, for each planning capability (grasp_planner, ik_solver, collision_checker, motion_planner), the active backend name and a dictionary of backend-specific parameters.
3. THE Planning_Node SHALL accept ROS2 parameters specifying the file paths to planning_params.yaml and planning_backends.yaml.
4. THE Planning_Node SHALL accept ROS2 parameters that override values from planning_params.yaml at launch time.

### Requirement 13: Launch File

**User Story:** As a system integrator, I want a ROS2 launch file that starts the planning node with configurable parameters, so that I can integrate the planning subsystem into the full system launch.

#### Acceptance Criteria

1. THE planning.launch.py file SHALL launch the Planning_Node with default parameters from planning_params.yaml and planning_backends.yaml.
2. THE planning.launch.py file SHALL accept launch arguments for the planning params file path, planning backends file path, and arm_id.
3. WHEN launch arguments are provided, THE planning.launch.py file SHALL pass them as ROS2 parameter overrides to the Planning_Node.

### Requirement 14: Linear Interpolation Trajectory Generation

**User Story:** As a robotics developer, I want the simple motion planner to produce smooth, time-parameterized trajectories via linear interpolation, so that the control layer can execute them directly.

#### Acceptance Criteria

1. WHEN the simple Motion_Planner backend generates a trajectory, THE simple Motion_Planner backend SHALL produce trajectory points with `positions` that linearly interpolate between start and goal joint states.
2. WHEN the simple Motion_Planner backend generates a trajectory, THE simple Motion_Planner backend SHALL compute `velocities` for each trajectory point as the finite difference of adjacent positions divided by the time step.
3. WHEN the simple Motion_Planner backend generates a trajectory, THE simple Motion_Planner backend SHALL set `accelerations` to zero for all trajectory points (constant velocity segments).
4. THE simple Motion_Planner backend SHALL compute the total trajectory duration as `max_joint_displacement / (max_joint_velocity * max_velocity_scaling)`, where `max_joint_velocity` is a configurable parameter.
5. FOR ALL trajectories produced by the simple Motion_Planner backend, the first trajectory point SHALL have positions equal to the start joint state and `time_from_start_sec` equal to 0.0.
6. FOR ALL trajectories produced by the simple Motion_Planner backend, the last trajectory point SHALL have positions equal to the goal joint state.
