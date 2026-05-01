# Requirements Document

## Introduction

The `roboweave_runtime` package is the on-device task execution hub for the RoboWeave robotics system. It receives structured plans from the cloud agent, orchestrates skill execution across perception/planning/control/VLA subsystems, maintains a centralized world state, and handles failure recovery. This document covers Phase 1.3–1.6: WorldModel, SkillOrchestrator, TaskExecutor, ExecutionMonitor, and the RuntimeNode that wires them together.

All components communicate with other RoboWeave packages exclusively via ROS2 interfaces (topics, services, actions) defined in `roboweave_msgs`. Internal data structures use Pydantic models from `roboweave_interfaces`. The behavior tree library is `py_trees`.

## Glossary

- **WorldModel**: Component that maintains the centralized world state, including tracked objects, robot state, and environment state. Exposes ROS2 services and topics for state queries and updates.
- **WorldState**: A `roboweave_interfaces.WorldState` snapshot containing robot state, object states, environment state, and optional task state.
- **ObjectState**: Tracked object with separated observation (raw sensor data) and belief (fused estimate), a lifecycle state, and a TTL for staleness detection.
- **ObjectLifecycle**: Enum governing object tracking states: ACTIVE → OCCLUDED → LOST → REMOVED → HELD.
- **SkillOrchestrator**: Component that manages skill registration, health checking, resource locking, precondition/postcondition evaluation, and skill execution via the CallSkill action server.
- **SkillDescriptor**: Declarative description of a skill's interface, resource requirements, pre/postconditions, and execution constraints.
- **SkillProtocol**: Python Protocol that all skills must implement: `check_precondition`, `execute`, `check_postcondition`, `cancel`.
- **ResourceManager**: Sub-component of SkillOrchestrator that manages shared and exclusive resource locks to prevent skill conflicts.
- **TaskExecutor**: Component that receives a PlanGraph via the DispatchPlan service, converts it to a py_trees behavior tree, and drives tick-based execution.
- **PlanGraph**: A directed acyclic graph of PlanNode objects representing a task execution plan, produced by the cloud agent.
- **BehaviorTree**: A py_trees tree constructed from a PlanGraph, containing SkillAction, ConditionCheck, and RecoveryNode node types.
- **ExecutionMonitor**: Component that monitors skill execution events, routes failures to recovery strategies via the ErrorCodeSpec registry, and publishes ExecutionEvent messages.
- **ErrorCodeSpec**: Metadata for an error code specifying severity, recoverability, retryability, default recovery policy, and escalation flags.
- **RecoveryAction**: A structured recovery action with a name, parameters, priority, and escalation flags.
- **RuntimeNode**: The main ROS2 node that instantiates and wires WorldModel, SkillOrchestrator, TaskExecutor, ExecutionMonitor, CloudBridge (stub), and HITLManager (stub).
- **CloudBridge**: Stub component for gRPC communication with the cloud agent (Phase 1 provides interface only).
- **HITLManager**: Stub component for human-in-the-loop request management (Phase 1 provides interface only).
- **JsonEnvelope**: Standard wrapper for JSON payloads transmitted over ROS2 string fields, containing schema name, version, payload, and optional hash.
- **TTL**: Time-to-live in seconds; objects not observed within their TTL are transitioned to LOST.

## Requirements

### Requirement 1: WorldModel State Management

**User Story:** As a runtime component, I want a centralized world state so that all subsystems operate on a consistent view of the robot, objects, and environment.

#### Acceptance Criteria

1. THE WorldModel SHALL maintain a single WorldState instance containing robot state, object states, environment state, and task state.
2. WHEN an UpdateWorldState service request with update_type "object_added" is received, THE WorldModel SHALL add a new ObjectState to the WorldState and return success=true.
3. WHEN an UpdateWorldState service request with update_type "object_updated" is received, THE WorldModel SHALL update the matching ObjectState and return success=true.
4. WHEN an UpdateWorldState service request with update_type "object_removed" is received, THE WorldModel SHALL transition the matching ObjectState lifecycle to REMOVED and return success=true.
5. WHEN an UpdateWorldState service request with update_type "full_refresh" is received, THE WorldModel SHALL replace the entire WorldState with the provided payload and return success=true.
6. IF an UpdateWorldState request references a non-existent object_id for update_type "object_updated", THEN THE WorldModel SHALL return success=false with a descriptive error message.
7. WHEN a QueryWorldState service request with query_type "full" is received, THE WorldModel SHALL return the complete WorldState serialized as a JsonEnvelope.
8. WHEN a QueryWorldState service request with query_type "object" is received, THE WorldModel SHALL return the ObjectState matching the provided object_id serialized as a JsonEnvelope.
9. WHEN a QueryWorldState service request with query_type "robot" is received, THE WorldModel SHALL return the current RobotState serialized as a JsonEnvelope.
10. IF a QueryWorldState request with query_type "object" references a non-existent object_id, THEN THE WorldModel SHALL return success=false with a descriptive error message.

### Requirement 2: WorldModel ROS2 Topic Publishing

**User Story:** As a downstream subscriber, I want to receive world state updates over ROS2 topics so that I can react to state changes without polling.

#### Acceptance Criteria

1. THE WorldModel SHALL publish the complete WorldState as a WorldStateStamped message on the /roboweave/world_state topic at a configurable low frequency (default 1 Hz).
2. WHEN the WorldState is modified via UpdateWorldState, THE WorldModel SHALL publish a WorldStateUpdate message on the /roboweave/world_state_update topic containing the update_type, affected object_id, and the changed payload.
3. WHEN a RobotStateMsg message is received on the /roboweave/robot_state topic, THE WorldModel SHALL update the robot state within the WorldState.

### Requirement 3: Object Lifecycle Management

**User Story:** As a task planner, I want objects to have well-defined lifecycle states so that I can reason about object availability and plan accordingly.

#### Acceptance Criteria

1. THE WorldModel SHALL track each ObjectState with a lifecycle_state from the ObjectLifecycle enum: ACTIVE, OCCLUDED, LOST, REMOVED, HELD.
2. WHEN an object's last_seen timestamp exceeds the current time minus the object's ttl_sec, THE WorldModel SHALL transition the object's lifecycle_state from ACTIVE to LOST.
3. WHEN an object in ACTIVE state is updated with a new observation, THE WorldModel SHALL update the object's last_seen timestamp to the observation timestamp.
4. WHEN an object in OCCLUDED state receives a new observation, THE WorldModel SHALL transition the object's lifecycle_state back to ACTIVE.
5. WHEN an object in LOST state receives a new observation, THE WorldModel SHALL transition the object's lifecycle_state back to ACTIVE and update last_seen.
6. THE WorldModel SHALL separate each ObjectState into an ObjectObservation (raw sensor data) and an ObjectBelief (fused estimate), storing both independently.
7. WHILE an object is in HELD lifecycle_state, THE WorldModel SHALL not transition the object to LOST due to TTL expiry.

### Requirement 4: Skill Registration and Discovery

**User Story:** As a skill developer, I want to register skills with the orchestrator so that the runtime can discover and invoke them.

#### Acceptance Criteria

1. THE SkillOrchestrator SHALL maintain a skill registry mapping skill names to SkillProtocol implementations and their SkillDescriptor metadata.
2. WHEN a skill is registered, THE SkillOrchestrator SHALL validate that the skill implements the SkillProtocol interface (name, category, descriptor, check_precondition, execute, check_postcondition, cancel).
3. WHEN a ListSkills service request is received with an empty category_filter, THE SkillOrchestrator SHALL return all registered skill names and their SkillDescriptor JSON.
4. WHEN a ListSkills service request is received with a non-empty category_filter, THE SkillOrchestrator SHALL return only skills matching the specified SkillCategory.
5. WHEN a SkillHealth service request is received, THE SkillOrchestrator SHALL return the health status ("healthy", "degraded", or "unavailable") and diagnostics for the named skill.
6. IF a SkillHealth request references an unregistered skill name, THEN THE SkillOrchestrator SHALL return success=false.

### Requirement 5: Skill Execution via CallSkill Action

**User Story:** As a task executor, I want to invoke skills through a ROS2 action server so that I can execute skills asynchronously with progress feedback and cancellation support.

#### Acceptance Criteria

1. THE SkillOrchestrator SHALL provide a CallSkill action server that accepts skill_call_id, skill_name, task_id, inputs_json, constraints_json, and timeout_ms.
2. WHEN a CallSkill goal is received, THE SkillOrchestrator SHALL check the skill's preconditions against the current WorldState before execution.
3. IF precondition checking fails, THEN THE SkillOrchestrator SHALL abort the CallSkill goal with failure_code "TSK_PRECONDITION_FAILED" and a descriptive failure_message.
4. WHEN preconditions are satisfied, THE SkillOrchestrator SHALL execute the skill by calling the SkillProtocol.execute method with the constructed SkillCall and current WorldState.
5. WHEN a skill completes execution, THE SkillOrchestrator SHALL check the skill's postconditions against the updated WorldState.
6. IF postcondition checking fails, THEN THE SkillOrchestrator SHALL report failure_code "TSK_POSTCONDITION_FAILED" in the CallSkill result.
7. THE SkillOrchestrator SHALL publish CallSkill feedback messages indicating the current phase ("precondition_check", "executing", "postcondition_check") and progress.
8. WHEN a CallSkill goal is cancelled, THE SkillOrchestrator SHALL call the skill's cancel method and release any acquired resources.
9. IF the skill execution exceeds timeout_ms (or the skill's default timeout when timeout_ms is 0), THEN THE SkillOrchestrator SHALL cancel the skill and return status "timeout".
10. IF a CallSkill goal references an unregistered skill_name, THEN THE SkillOrchestrator SHALL abort the goal with failure_code "TSK_SKILL_NOT_FOUND".

### Requirement 6: Resource Lock Management

**User Story:** As a system operator, I want the orchestrator to prevent resource conflicts between concurrent skills so that two skills do not simultaneously control the same arm or gripper.

#### Acceptance Criteria

1. THE ResourceManager SHALL support acquiring shared resources (multiple holders allowed) and exclusive resources (single holder only) as declared in a SkillDescriptor.
2. WHEN a CallSkill goal is accepted, THE SkillOrchestrator SHALL acquire the skill's required_resources (shared) and exclusive_resources (exclusive) via the ResourceManager before execution begins.
3. IF resource acquisition fails due to a conflict, THEN THE SkillOrchestrator SHALL abort the CallSkill goal with a descriptive failure_message indicating which resources are held and by which skill.
4. WHEN a skill completes, is cancelled, or times out, THE SkillOrchestrator SHALL release all resources acquired for that skill via the ResourceManager.
5. THE ResourceManager SHALL provide a query method to check whether a specific resource is currently available for shared or exclusive access.
6. THE ResourceManager SHALL provide a query method to list the current holders of a specific resource.

### Requirement 7: PlanGraph Dispatch and Validation

**User Story:** As a cloud agent, I want to dispatch a PlanGraph to the runtime so that the robot executes the planned task.

#### Acceptance Criteria

1. WHEN a DispatchPlan service request is received, THE TaskExecutor SHALL deserialize the plan_json field as a JsonEnvelope containing a PlanGraph.
2. THE TaskExecutor SHALL validate that the PlanGraph forms a valid directed acyclic graph (no cycles in depends_on references).
3. THE TaskExecutor SHALL validate that all skill_name references in PlanNodes correspond to skills registered in the SkillOrchestrator.
4. IF validation fails, THEN THE TaskExecutor SHALL return accepted=false with a descriptive error message.
5. WHEN validation succeeds, THE TaskExecutor SHALL return accepted=true and begin execution.

### Requirement 8: Behavior Tree Construction and Execution

**User Story:** As a runtime developer, I want PlanGraphs converted to behavior trees so that task execution follows a well-defined tick-based control flow.

#### Acceptance Criteria

1. WHEN a valid PlanGraph is accepted, THE TaskExecutor SHALL convert the PlanGraph into a py_trees behavior tree respecting node dependencies (depends_on).
2. THE TaskExecutor SHALL support three BT node types: SkillAction (invokes a skill via SkillOrchestrator), ConditionCheck (evaluates a precondition against WorldState), and RecoveryNode (executes a recovery strategy on child failure).
3. THE TaskExecutor SHALL tick the behavior tree at a configurable rate (default 10 Hz).
4. WHEN a SkillAction node is ticked, THE TaskExecutor SHALL invoke the corresponding skill through the SkillOrchestrator's CallSkill action and map the skill result to py_trees Status (SUCCESS, FAILURE, RUNNING).
5. WHEN a ConditionCheck node is ticked, THE TaskExecutor SHALL evaluate the condition against the current WorldState from the WorldModel.
6. WHEN a RecoveryNode's child fails, THE RecoveryNode SHALL attempt the configured recovery strategy before reporting failure to its parent.

### Requirement 9: Task Status Publishing and Control

**User Story:** As a system monitor, I want to observe task execution progress and control running tasks so that I can track and intervene in task execution.

#### Acceptance Criteria

1. WHILE a task is executing, THE TaskExecutor SHALL publish TaskStatus messages on the /roboweave/task_status topic containing task_id, status, progress, current_node_id, failure_code, and message.
2. WHEN a TaskControl service request with action "pause" is received, THE TaskExecutor SHALL pause the behavior tree ticking and set the task status to "paused".
3. WHEN a TaskControl service request with action "resume" is received for a paused task, THE TaskExecutor SHALL resume behavior tree ticking and set the task status to "running".
4. WHEN a TaskControl service request with action "cancel" is received, THE TaskExecutor SHALL stop behavior tree ticking, cancel any running skills, and set the task status to "cancelled".
5. IF a TaskControl request references a non-existent task_id, THEN THE TaskExecutor SHALL return success=false with a descriptive error message.

### Requirement 10: Execution Event Monitoring

**User Story:** As a data collection system, I want structured execution events so that I can record and analyze task execution for debugging and training data generation.

#### Acceptance Criteria

1. THE ExecutionMonitor SHALL publish ExecutionEvent messages on the /roboweave/execution_events topic for all skill and task lifecycle transitions (skill_started, skill_succeeded, skill_failed, skill_timeout, precondition_failed, postcondition_failed, safety_triggered, recovery_started, recovery_succeeded, recovery_failed, task_started, task_completed, task_failed).
2. WHEN a skill execution event occurs, THE ExecutionMonitor SHALL populate the ExecutionEvent with the event_id, task_id, node_id, event_type, failure_code (if applicable), severity, message, and timestamp.
3. THE ExecutionMonitor SHALL populate the recovery_candidates field of an ExecutionEvent by looking up the failure_code in the ERROR_CODE_SPECS registry.

### Requirement 11: Failure Recovery Routing

**User Story:** As a task executor, I want failures automatically routed to appropriate recovery strategies so that the robot can recover from common errors without cloud intervention.

#### Acceptance Criteria

1. WHEN a RequestRecovery service request is received, THE ExecutionMonitor SHALL look up the failure_code in the ERROR_CODE_SPECS registry to determine the default_recovery_policy.
2. IF the ErrorCodeSpec for the failure_code has recoverable=true, THEN THE ExecutionMonitor SHALL return a RecoveryAction with the default_recovery_policy as the action_name.
3. IF the ErrorCodeSpec for the failure_code has escalate_to_cloud=true, THEN THE ExecutionMonitor SHALL set escalate_to_cloud=true on the returned RecoveryAction.
4. IF the ErrorCodeSpec for the failure_code has escalate_to_user=true, THEN THE ExecutionMonitor SHALL set escalate_to_user=true on the returned RecoveryAction.
5. IF the failure_code is not found in the ERROR_CODE_SPECS registry, THEN THE ExecutionMonitor SHALL return success=false with a message indicating the unknown failure code.
6. IF the ErrorCodeSpec for the failure_code has recoverable=false, THEN THE ExecutionMonitor SHALL return a RecoveryAction with escalate_to_cloud=true and escalate_to_user=true.

### Requirement 12: Recovery Strategy Chain Execution

**User Story:** As a runtime system, I want recovery strategies executed in priority order so that the system tries the most appropriate recovery first before escalating.

#### Acceptance Criteria

1. WHEN a skill failure triggers recovery, THE ExecutionMonitor SHALL construct an ordered list of RecoveryAction candidates based on the ErrorCodeSpec default_recovery_policy and any additional recovery_candidates from the ExecutionEvent.
2. THE ExecutionMonitor SHALL attempt recovery actions in priority order (lowest priority value first).
3. IF a recovery action succeeds, THEN THE ExecutionMonitor SHALL publish a recovery_succeeded ExecutionEvent and signal the TaskExecutor to retry the failed node.
4. IF a recovery action fails, THEN THE ExecutionMonitor SHALL publish a recovery_failed ExecutionEvent and attempt the next recovery action in the chain.
5. IF all recovery actions in the chain fail, THEN THE ExecutionMonitor SHALL escalate the failure by publishing a task_failed ExecutionEvent.

### Requirement 13: RuntimeNode Composition

**User Story:** As a system integrator, I want a single ROS2 node that wires all runtime components together so that the runtime can be launched as one unit.

#### Acceptance Criteria

1. THE RuntimeNode SHALL instantiate and wire together the WorldModel, SkillOrchestrator, TaskExecutor, and ExecutionMonitor components.
2. THE RuntimeNode SHALL instantiate a CloudBridge stub that exposes the gRPC client interface without connecting to a real cloud agent in Phase 1.
3. THE RuntimeNode SHALL instantiate an HITLManager stub that exposes the HITL request/response interface without implementing real human-in-the-loop routing in Phase 1.
4. THE RuntimeNode SHALL register all ROS2 services (UpdateWorldState, QueryWorldState, DispatchPlan, TaskControl, ListSkills, SkillHealth, RequestRecovery) on the correct topic names under the /roboweave/ namespace.
5. THE RuntimeNode SHALL register all ROS2 topic publishers (/roboweave/world_state, /roboweave/world_state_update, /roboweave/task_status, /roboweave/execution_events) and subscribers (/roboweave/robot_state).
6. THE RuntimeNode SHALL register the CallSkill action server under the /roboweave/ namespace.

### Requirement 14: JsonEnvelope Serialization Round-Trip

**User Story:** As a developer, I want all JSON payloads transmitted over ROS2 string fields to use JsonEnvelope so that schema versioning and integrity checking are consistent.

#### Acceptance Criteria

1. THE RuntimeNode SHALL serialize all outgoing JSON payloads (WorldState, ObjectState, RobotState, SkillDescriptor, SkillResult, RecoveryAction) using JsonEnvelope.wrap().
2. THE RuntimeNode SHALL deserialize all incoming JSON payloads by validating the JsonEnvelope schema_name and schema_version before extracting the payload.
3. FOR ALL valid Pydantic models used in ROS2 JSON fields, wrapping with JsonEnvelope.wrap() then deserializing the payload_json back to the original model SHALL produce an equivalent object (round-trip property).
4. IF an incoming JsonEnvelope has a schema_version that does not match the expected version, THEN THE RuntimeNode SHALL log a warning and attempt best-effort deserialization.

### Requirement 15: Pure Python Testability

**User Story:** As a test engineer, I want runtime components testable as pure Python without requiring a live ROS2 environment so that unit tests run fast and reliably.

#### Acceptance Criteria

1. THE WorldModel, SkillOrchestrator (core logic), TaskExecutor (BT construction and validation), ExecutionMonitor (recovery routing), and ResourceManager SHALL be implementable as pure Python classes that accept dependencies via constructor injection rather than requiring ROS2 node initialization.
2. THE RuntimeNode SHALL act as the ROS2 adapter layer that delegates to the pure Python components, keeping ROS2-specific code (service handlers, topic publishers, action servers) separate from business logic.
