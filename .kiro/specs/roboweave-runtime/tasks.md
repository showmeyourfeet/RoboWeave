# Implementation Plan: roboweave-runtime

## Overview

Implement the `roboweave_runtime` package — the on-device task execution hub for RoboWeave (Phase 1.3–1.6). The package uses an ament_python layout with pure-Python core components (WorldModel, ResourceManager, SkillOrchestrator, TaskExecutor, ExecutionMonitor) and a thin ROS2 adapter (RuntimeNode). All internal data uses `roboweave_interfaces` Pydantic models; `py_trees` drives behavior tree execution. Implementation proceeds bottom-up: foundational components first, then orchestration, then BT nodes, then the ROS2 wiring layer.

## Tasks

- [ ] 1. Package scaffolding and project setup
  - [ ] 1.1 Create ament_python package structure
    - Create `roboweave_runtime/` directory with `setup.py`, `setup.cfg`, `package.xml`
    - Create `roboweave_runtime/roboweave_runtime/__init__.py` with package version
    - Create `roboweave_runtime/roboweave_runtime/bt_nodes/__init__.py`
    - Create `roboweave_runtime/config/runtime_params.yaml` with default parameters (`publish_hz: 1.0`, `tick_hz: 10.0`)
    - Create `roboweave_runtime/launch/runtime.launch.py` placeholder
    - Create `roboweave_runtime/tests/__init__.py` and `roboweave_runtime/tests/conftest.py` with shared fixtures
    - Add `py_trees`, `roboweave_interfaces`, and `roboweave_msgs` as dependencies in `package.xml` and `setup.py`
    - _Requirements: 13.1, 15.1, 15.2_

- [ ] 2. Implement WorldModel (pure Python)
  - [ ] 2.1 Create `roboweave_runtime/roboweave_runtime/world_model.py`
    - Implement `WorldModel.__init__` with `publish_hz`, injectable `clock` callable, and empty `WorldState`
    - Implement `handle_update(update_type, object_id, payload_json)` supporting `object_added`, `object_updated`, `object_removed`, `full_refresh`
    - Implement `update_robot_state(robot_state)` to update the `RobotState` within `WorldState`
    - Implement `query_full()`, `query_object(object_id)`, `query_robot()`, `get_world_state()`
    - Implement `tick_ttl()` — iterate objects, transition ACTIVE → LOST when `clock() - last_seen > ttl_sec`, skip HELD objects
    - Wire `on_state_changed` and `on_update_published` callbacks
    - Handle error cases: unknown `update_type`, non-existent `object_id` for update, invalid JSON payload
    - Implement lifecycle transitions: `object_updated` on OCCLUDED/LOST → ACTIVE with `last_seen` update
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [ ]* 2.2 Write property test: Object add/query round-trip
    - **Property 1: Object add/query round-trip**
    - **Validates: Requirements 1.2, 1.7, 1.8**

  - [ ]* 2.3 Write property test: Object update preserves changes
    - **Property 2: Object update preserves changes**
    - **Validates: Requirements 1.3**

  - [ ]* 2.4 Write property test: Object removal sets REMOVED lifecycle
    - **Property 3: Object removal sets REMOVED lifecycle**
    - **Validates: Requirements 1.4**

  - [ ]* 2.5 Write property test: Full refresh replaces entire WorldState
    - **Property 4: Full refresh replaces entire WorldState**
    - **Validates: Requirements 1.5**

  - [ ]* 2.6 Write property test: Update of non-existent object fails
    - **Property 5: Update of non-existent object fails**
    - **Validates: Requirements 1.6**

  - [ ]* 2.7 Write property test: State mutation triggers change callback
    - **Property 6: State mutation triggers change callback**
    - **Validates: Requirements 2.2**

  - [ ]* 2.8 Write property test: Robot state update round-trip
    - **Property 7: Robot state update round-trip**
    - **Validates: Requirements 2.3, 1.9**

  - [ ]* 2.9 Write property test: TTL expiry transitions ACTIVE to LOST, HELD exempt
    - **Property 8: TTL expiry transitions ACTIVE to LOST, HELD exempt**
    - **Validates: Requirements 3.2, 3.7**

  - [ ]* 2.10 Write property test: Observation reactivates non-REMOVED objects
    - **Property 9: Observation reactivates non-REMOVED objects**
    - **Validates: Requirements 3.3, 3.4, 3.5**

  - [ ]* 2.11 Write unit tests for WorldModel
    - Test invalid `update_type` returns `(False, ...)`
    - Test `query_object` for non-existent `object_id` returns `None`
    - Test `full_refresh` replaces all objects
    - Test lifecycle separation of `ObjectObservation` and `ObjectBelief`
    - _Requirements: 1.6, 1.10, 3.6_

- [ ] 3. Implement ResourceManager (pure Python)
  - [ ] 3.1 Create `roboweave_runtime/roboweave_runtime/resource_manager.py`
    - Implement `ResourceManager.__init__` with `_shared: dict[str, set[str]]` and `_exclusive: dict[str, str]`
    - Implement `acquire(holder, shared, exclusive)` with atomic all-or-nothing semantics
    - Implement `release(holder)` to remove holder from all shared and exclusive locks
    - Implement `is_available(resource, exclusive)` and `get_holders(resource)`
    - Enforce mutual exclusion: a resource cannot have both shared and exclusive holders
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ]* 3.2 Write property test: Resource mutual exclusion invariant
    - **Property 14: Resource mutual exclusion invariant**
    - **Validates: Requirements 6.1, 6.5, 6.6**

  - [ ]* 3.3 Write property test: Resource acquisition atomicity
    - **Property 15: Resource acquisition atomicity**
    - **Validates: Requirements 6.1, 6.3**

  - [ ]* 3.4 Write unit tests for ResourceManager
    - Test shared acquisition by multiple holders
    - Test exclusive blocks shared and vice versa
    - Test release clears all locks for a holder
    - Test `get_holders` returns correct holders
    - _Requirements: 6.5, 6.6_

- [ ] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement ExecutionMonitor (pure Python)
  - [ ] 5.1 Create `roboweave_runtime/roboweave_runtime/execution_monitor.py`
    - Implement `ExecutionMonitor.__init__` with injectable `error_code_specs` (defaults to `ERROR_CODE_SPECS`)
    - Implement `create_event(task_id, node_id, event_type, ...)` factory with auto-generated `event_id` (UUID)
    - Implement `publish_event(event)` — populate `recovery_candidates` from `ERROR_CODE_SPECS` when `failure_code` is present, invoke `on_event` callback
    - Implement `request_recovery(failure_code, context)` — look up `ErrorCodeSpec`, return `(True, RecoveryAction, msg)` or `(False, None, msg)` for unknown codes
    - Implement `build_recovery_chain(failure_code, extra_candidates)` — build ordered list of `RecoveryAction` sorted by ascending priority
    - Handle non-recoverable errors: set `escalate_to_cloud=True` and `escalate_to_user=True`
    - _Requirements: 10.1, 10.2, 10.3, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 12.1, 12.2_

  - [ ]* 5.2 Write property test: ExecutionEvent recovery_candidates populated from ERROR_CODE_SPECS
    - **Property 22: ExecutionEvent recovery_candidates populated from ERROR_CODE_SPECS**
    - **Validates: Requirements 10.3**

  - [ ]* 5.3 Write property test: Recovery routing matches ErrorCodeSpec
    - **Property 23: Recovery routing matches ErrorCodeSpec**
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.6**

  - [ ]* 5.4 Write property test: Recovery chain priority ordering
    - **Property 24: Recovery chain priority ordering**
    - **Validates: Requirements 12.2**

  - [ ]* 5.5 Write unit tests for ExecutionMonitor
    - Test unknown `failure_code` returns `(False, None, ...)`
    - Test recovery chain: all fail → escalate scenario
    - Test recovery chain: first succeeds → retry scenario
    - Test `create_event` generates unique `event_id`
    - _Requirements: 11.5, 12.3, 12.4, 12.5_

- [ ] 6. Implement SkillOrchestrator (pure Python)
  - [ ] 6.1 Create `roboweave_runtime/roboweave_runtime/skill_orchestrator.py`
    - Implement `SkillOrchestrator.__init__` accepting `WorldModel`, `ResourceManager`, `ExecutionMonitor`
    - Implement `register_skill(skill)` — validate `SkillProtocol` compliance, store in `_registry: dict[str, tuple[SkillProtocol, SkillDescriptor]]`
    - Implement `list_skills(category_filter)` — return all or filtered by `SkillCategory`
    - Implement `get_skill_health(skill_name)` — return `(success, status, diagnostics_json)`
    - Implement `execute_skill(call: SkillCall) -> SkillResult` with full lifecycle:
      1. Look up skill in registry (fail with `TSK_SKILL_NOT_FOUND`)
      2. Acquire resources via `ResourceManager` (fail with `TSK_RESOURCE_CONFLICT`)
      3. Check preconditions (fail with `TSK_PRECONDITION_FAILED`)
      4. Execute skill
      5. Check postconditions (fail with `TSK_POSTCONDITION_FAILED`)
      6. Release resources in `finally` block
    - Implement `cancel_skill(skill_call_id)` — cancel running asyncio task, release resources
    - Track running skills in `_running: dict[str, asyncio.Task]`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 6.2, 6.4_

  - [ ]* 6.2 Write property test: Skill list with category filter
    - **Property 10: Skill list with category filter**
    - **Validates: Requirements 4.1, 4.3, 4.4**

  - [ ]* 6.3 Write property test: Precondition failure produces TSK_PRECONDITION_FAILED
    - **Property 11: Precondition failure produces TSK_PRECONDITION_FAILED**
    - **Validates: Requirements 5.2, 5.3**

  - [ ]* 6.4 Write property test: Postcondition failure produces TSK_POSTCONDITION_FAILED
    - **Property 12: Postcondition failure produces TSK_POSTCONDITION_FAILED**
    - **Validates: Requirements 5.5, 5.6**

  - [ ]* 6.5 Write property test: Skill termination releases all resources
    - **Property 13: Skill termination releases all resources**
    - **Validates: Requirements 5.8, 6.4**

  - [ ]* 6.6 Write unit tests for SkillOrchestrator
    - Test `register_skill` with valid and invalid `SkillProtocol`
    - Test `execute_skill` with unregistered skill returns `TSK_SKILL_NOT_FOUND`
    - Test `get_skill_health` for unregistered skill returns `success=false`
    - Test skill timeout behavior
    - Test `cancel_skill` releases resources
    - _Requirements: 4.2, 4.6, 5.9, 5.10_

- [ ] 7. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement BT nodes
  - [ ] 8.1 Create `roboweave_runtime/roboweave_runtime/bt_nodes/skill_action.py`
    - Implement `SkillAction(py_trees.behaviour.Behaviour)` wrapping `SkillOrchestrator.execute_skill()`
    - Map `SkillResult.status` → `py_trees.common.Status`: SUCCESS→SUCCESS, FAILED/SAFETY_STOP→FAILURE, TIMEOUT/CANCELLED/INTERRUPTED→FAILURE, in-progress→RUNNING
    - Store `SkillCall` parameters on the node, invoke orchestrator on `update()`
    - _Requirements: 8.2, 8.4_

  - [ ] 8.2 Create `roboweave_runtime/roboweave_runtime/bt_nodes/condition_check.py`
    - Implement `ConditionCheck(py_trees.behaviour.Behaviour)` evaluating a precondition expression against `WorldModel.get_world_state()`
    - Return SUCCESS if condition satisfied, FAILURE otherwise
    - _Requirements: 8.2, 8.5_

  - [ ] 8.3 Create `roboweave_runtime/roboweave_runtime/bt_nodes/recovery_node.py`
    - Implement `RecoveryNode(py_trees.behaviour.Behaviour)` as a decorator that catches child FAILURE
    - Attempt configured recovery strategy, optionally retry child
    - Report FAILURE to parent if recovery fails
    - _Requirements: 8.2, 8.6_

  - [ ]* 8.4 Write property test: SkillStatus to py_trees Status mapping consistency
    - **Property 19: SkillStatus to py_trees Status mapping consistency**
    - **Validates: Requirements 8.4**

  - [ ]* 8.5 Write unit tests for BT nodes
    - Test `ConditionCheck` evaluation with satisfied and unsatisfied conditions
    - Test `RecoveryNode` retry-then-fail behavior
    - Test `SkillAction` maps all `SkillStatus` values correctly
    - _Requirements: 8.2, 8.4, 8.5, 8.6_

- [ ] 9. Implement TaskExecutor (pure Python)
  - [ ] 9.1 Create `roboweave_runtime/roboweave_runtime/task_executor.py`
    - Implement `TaskExecutor.__init__` accepting `SkillOrchestrator`, `WorldModel`, `ExecutionMonitor`, `tick_hz`
    - Implement `validate_plan_graph(plan: PlanGraph)` — DAG check via Kahn's algorithm + skill reference check against `SkillOrchestrator`
    - Implement `build_behaviour_tree(plan: PlanGraph)` — convert `PlanGraph` to `py_trees.trees.BehaviourTree` respecting `depends_on` ordering, using `SkillAction`, `ConditionCheck`, `RecoveryNode`
    - Implement `dispatch_plan(plan_json)` — deserialize `JsonEnvelope`, validate, build BT, publish `task_started` event
    - Implement `tick()` — single BT tick, update task status, publish `TaskStatus`
    - Implement `pause(task_id)`, `resume(task_id)`, `cancel(task_id)` — control BT ticking, cancel running skills on cancel, release resources
    - Wire `on_task_status` callback
    - Handle errors: invalid PlanGraph, non-existent `task_id`, BT tick exceptions
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.3, 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 9.2 Write property test: PlanGraph DAG validation detects cycles
    - **Property 16: PlanGraph DAG validation detects cycles**
    - **Validates: Requirements 7.2**

  - [ ]* 9.3 Write property test: PlanGraph skill reference validation
    - **Property 17: PlanGraph skill reference validation**
    - **Validates: Requirements 7.3**

  - [ ]* 9.4 Write property test: BT preserves PlanGraph dependency ordering
    - **Property 18: BT preserves PlanGraph dependency ordering**
    - **Validates: Requirements 8.1**

  - [ ]* 9.5 Write property test: Task pause/resume round-trip
    - **Property 20: Task pause/resume round-trip**
    - **Validates: Requirements 9.2, 9.3**

  - [ ]* 9.6 Write property test: Task cancel stops execution and releases resources
    - **Property 21: Task cancel stops execution and releases resources**
    - **Validates: Requirements 9.4**

  - [ ]* 9.7 Write unit tests for TaskExecutor
    - Test `dispatch_plan` with invalid JSON returns `(False, ...)`
    - Test `TaskControl` with non-existent `task_id` returns `(False, ...)`
    - Test BT tick exception is caught and task set to `"failed"`
    - _Requirements: 7.4, 9.5_

- [ ] 10. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement Converters (Pydantic ↔ ROS2 msg)
  - [ ] 11.1 Create `roboweave_runtime/roboweave_runtime/converters.py`
    - Implement `world_state_to_stamped_msg(ws, header)` → `WorldStateStamped`
    - Implement `robot_state_msg_to_pydantic(msg)` → `RobotState`
    - Implement `execution_event_to_msg(event)` → `ExecutionEventMsg`
    - Implement `task_status_to_msg(task_id, status, progress, current_node_id, failure_code, message)` → `TaskStatusMsg`
    - Implement `json_envelope_to_msg(envelope)` → `JsonEnvelopeMsg` and `msg_to_json_envelope(msg)` → `JsonEnvelope`
    - All converters use `JsonEnvelope.wrap()` for JSON-over-string fields
    - _Requirements: 14.1, 14.2, 14.4_

  - [ ]* 11.2 Write property test: JsonEnvelope serialization round-trip
    - **Property 25: JsonEnvelope serialization round-trip**
    - **Validates: Requirements 14.3**

  - [ ]* 11.3 Write unit tests for converters
    - Test `JsonEnvelope` version mismatch warning
    - Test round-trip for each converter function
    - _Requirements: 14.3, 14.4_

- [ ] 12. Implement CloudBridge stub and HITLManager stub
  - [ ] 12.1 Create `roboweave_runtime/roboweave_runtime/cloud_bridge.py`
    - Implement `CloudBridge` stub: `submit_task` returns `None`, `analyze_failure` returns `[]`, `is_connected` returns `False`
    - _Requirements: 13.2_

  - [ ] 12.2 Create `roboweave_runtime/roboweave_runtime/hitl_manager.py`
    - Implement `HITLManager` stub: `request_intervention` returns `None`, `has_operator` returns `False`
    - _Requirements: 13.3_

  - [ ]* 12.3 Write unit tests for stubs
    - Test `CloudBridge.submit_task` returns `None`
    - Test `CloudBridge.is_connected` returns `False`
    - Test `HITLManager.request_intervention` returns `None`
    - Test `HITLManager.has_operator` returns `False`
    - _Requirements: 13.2, 13.3_

- [ ] 13. Implement RuntimeNode (ROS2 adapter)
  - [ ] 13.1 Create `roboweave_runtime/roboweave_runtime/runtime_node.py`
    - Implement `RuntimeNode(rclpy.node.Node)` instantiating all pure-Python components
    - Register ROS2 services: `UpdateWorldState`, `QueryWorldState`, `DispatchPlan`, `TaskControl`, `ListSkills`, `SkillHealth`, `RequestRecovery` under `/roboweave/` namespace
    - Register ROS2 publishers: `/roboweave/world_state` (WorldStateStamped @ 1 Hz), `/roboweave/world_state_update`, `/roboweave/task_status`, `/roboweave/execution_events`
    - Register ROS2 subscriber: `/roboweave/robot_state` → `WorldModel.update_robot_state`
    - Register `CallSkill` action server under `/roboweave/` namespace
    - Wire callbacks from pure-Python components to ROS2 publishers using converters
    - Create timer for BT tick at configurable rate and timer for WorldState publishing at `publish_hz`
    - Create timer for `WorldModel.tick_ttl()` at 1 Hz
    - _Requirements: 13.1, 13.4, 13.5, 13.6, 2.1, 2.3_

- [ ] 14. Configuration and launch files
  - [ ] 14.1 Finalize `roboweave_runtime/config/runtime_params.yaml`
    - Define all configurable parameters: `publish_hz`, `tick_hz`, `ttl_check_hz`, node name
    - _Requirements: 2.1, 8.3_

  - [ ] 14.2 Finalize `roboweave_runtime/launch/runtime.launch.py`
    - Launch `RuntimeNode` with parameters from `runtime_params.yaml`
    - _Requirements: 13.1_

- [ ] 15. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each major component
- Property tests use Hypothesis with `@settings(max_examples=100)` and tag format `# Feature: roboweave-runtime, Property {N}: {title}`
- All pure-Python components accept dependencies via constructor injection for testability (Requirement 15.1)
- ROS2-specific code is isolated in `RuntimeNode` and `converters.py` (Requirement 15.2)
- Custom Hypothesis strategies (`st_object_state`, `st_world_state`, `st_plan_graph`, etc.) should be defined in `tests/conftest.py`
