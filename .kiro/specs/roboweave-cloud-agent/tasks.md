# Implementation Plan: roboweave-cloud-agent

## Overview

Implement the `roboweave_cloud_agent` standalone Python package (not ROS2) as a gRPC server for cloud-side task decomposition, failure analysis, and world state caching. Tasks proceed bottom-up: package scaffolding + proto definition → configuration + config loader → pure-Python core components (SkillSelector, RecoveryAdvisor, TaskDecomposer, Agent orchestrator) → converters → gRPC server + servicer → entry point → tests. Each task builds on the previous, and property-based tests are placed close to the code they validate.

## Tasks

- [ ] 1. Scaffold the roboweave_cloud_agent package
  - [ ] 1.1 Create package directory structure and boilerplate files
    - Create `roboweave_cloud_agent/` top-level directory
    - Create `roboweave_cloud_agent/pyproject.toml` declaring dependencies on `roboweave_interfaces`, `grpcio`, `grpcio-tools`, `protobuf`, and dev dependencies `pytest`, `hypothesis`
    - Create `roboweave_cloud_agent/roboweave_cloud_agent/__init__.py`
    - Create `roboweave_cloud_agent/roboweave_cloud_agent/prompts/.gitkeep` (empty placeholder for future LLM prompts)
    - Create `roboweave_cloud_agent/tests/__init__.py` and `roboweave_cloud_agent/tests/conftest.py`
    - Create `roboweave_cloud_agent/config/` directory
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.6_

  - [ ] 1.2 Create cloud_agent.proto file
    - Create `roboweave_cloud_agent/proto/cloud_agent.proto`
    - Define `CloudAgentService` with four RPCs: `SubmitTask` (unary), `SubmitTaskStream` (server-streaming), `AnalyzeFailure` (unary), `UpdateWorldState` (unary)
    - Define all message types: `SubmitTaskRequest`, `SceneContext`, `AttachmentRef`, `SubmitTaskResponse`, `ResponseType` enum, `SubmitTaskStreamResponse`, `StreamEventType` enum, `ClarificationRequest`, `AnalyzeFailureRequest`, `AnalyzeFailureResponse`, `UpdateWorldStateRequest`, `UpdateWorldStateResponse`, `PlanGraphProto`, `PlanNodeProto`, `RetryPolicyProto`, `SuccessCondition`, `FailurePolicy`, `ExecutionEventProto`
    - _Requirements: 1.1, 1.3_

  - [ ] 1.3 Compile proto and generate Python gRPC stubs
    - Run `python -m grpc_tools.protoc` to compile `cloud_agent.proto` into `cloud_agent_pb2.py` and `cloud_agent_pb2_grpc.py` in the `roboweave_cloud_agent/roboweave_cloud_agent/` directory
    - Verify both generated files exist and are importable
    - _Requirements: 1.2_

- [ ] 2. Create configuration file and config loader
  - [ ] 2.1 Create cloud_agent_params.yaml
    - Create `roboweave_cloud_agent/config/cloud_agent_params.yaml` with server host/port, shutdown_timeout_sec, task_templates (pick up, place), and skill_descriptors (detect_object, plan_grasp, plan_motion, execute_grasp, open_gripper, retract)
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

  - [ ] 2.2 Create config.py loader module
    - Create `roboweave_cloud_agent/roboweave_cloud_agent/config.py`
    - Implement `load_config(path: str) -> dict[str, Any]` that reads and parses the YAML file
    - Raise `FileNotFoundError` if file does not exist, `ValueError` on invalid YAML
    - _Requirements: 12.5_

- [ ] 3. Implement SkillSelector
  - [ ] 3.1 Create SkillSelector with keyword-based matching
    - Create `roboweave_cloud_agent/roboweave_cloud_agent/skill_selector.py`
    - Implement `__init__(self, descriptors: list[SkillDescriptor])` storing skill descriptors
    - Implement `select(self, query: str) -> SkillDescriptor | None` that tokenizes query and skill name+description into lowercase words (split on whitespace and underscores), computes token overlap, returns descriptor with highest overlap or None if overlap is 0
    - Implement `list_skills(self) -> list[str]` returning all registered skill names
    - Matching must be case-insensitive
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 3.2 Write property test for SkillSelector best match or None
    - **Property 6: SkillSelector returns best match or None**
    - **Validates: Requirements 8.2, 8.3**

  - [ ]* 3.3 Write property test for SkillSelector case-insensitivity
    - **Property 7: SkillSelector is case-insensitive**
    - **Validates: Requirements 8.5**

- [ ] 4. Implement RecoveryAdvisor
  - [ ] 4.1 Create RecoveryAdvisor with ErrorCodeSpec lookup
    - Create `roboweave_cloud_agent/roboweave_cloud_agent/recovery_advisor.py`
    - Implement `advise(self, failure_code: str) -> tuple[str, list[str]]` that:
      - Tries to match `failure_code` against `ErrorCode` enum values
      - If no match: returns `("Unrecognized error code: {failure_code}", [])`
      - If match: looks up `ERROR_CODE_SPECS[error_code]`, builds recovery_actions list from spec flags (default_recovery_policy, retryable→"retry", escalate_to_cloud→"escalate_to_cloud", escalate_to_user→"ask_user_clarification")
      - Builds analysis string: `"Error {code} [{severity}] in module '{module}': recoverable={recoverable}"`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

  - [ ]* 4.2 Write property test for RecoveryAdvisor ErrorCodeSpec flags
    - **Property 8: RecoveryAdvisor faithfully reflects ErrorCodeSpec flags**
    - **Validates: Requirements 5.4, 9.2, 9.3, 9.4, 9.5**

  - [ ]* 4.3 Write property test for RecoveryAdvisor unknown codes
    - **Property 9: RecoveryAdvisor returns empty for unknown codes**
    - **Validates: Requirements 9.6**

  - [ ]* 4.4 Write property test for RecoveryAdvisor analysis metadata
    - **Property 10: RecoveryAdvisor analysis string contains required metadata**
    - **Validates: Requirements 9.7**

- [ ] 5. Implement TaskDecomposer
  - [ ] 5.1 Create TaskDecomposer with template-based decomposition
    - Create `roboweave_cloud_agent/roboweave_cloud_agent/task_decomposer.py`
    - Implement `__init__(self, templates: list[dict[str, Any]], skill_selector: SkillSelector)` loading templates
    - Implement `decompose(self, instruction: str, task_id: str, scene_context: dict[str, Any] | None = None) -> PlanGraph | None` that:
      - Iterates templates in order, performs case-insensitive substring match of `template["pattern"]` against instruction
      - Extracts object references via regex from template `regex` field
      - Instantiates `PlanNode` objects from template skeleton with unique `node_id`s (`"{task_id}_node_{i}"`)
      - Calls `SkillSelector.select(node["skill_name"])` to validate each skill exists
      - Wires `depends_on` relationships as defined in template
      - Returns `PlanGraph(plan_id=f"{task_id}_plan", task_id=task_id, nodes=nodes)` or None if no match
    - Support MVP templates: "pick up {object}" (detect → plan_grasp → plan_motion → execute_grasp) and "place {object} on {surface}" (plan_motion → open_gripper → retract)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [ ]* 5.2 Write property test for PlanGraph structural invariants
    - **Property 3: PlanGraph structural invariants**
    - **Validates: Requirements 7.4, 7.6, 7.7**

  - [ ]* 5.3 Write property test for template match task_id
    - **Property 4: Template match produces correct task_id**
    - **Validates: Requirements 7.2**

  - [ ]* 5.4 Write property test for no-match returns None
    - **Property 5: No-match instruction returns None**
    - **Validates: Requirements 7.5**

- [ ] 6. Checkpoint - Verify core components
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement Agent orchestrator
  - [ ] 7.1 Create Agent with sub-component wiring and WorldState cache
    - Create `roboweave_cloud_agent/roboweave_cloud_agent/agent.py`
    - Implement `__init__(self, config: dict[str, Any])` that initializes `TaskDecomposer`, `SkillSelector`, `RecoveryAdvisor` from config, and an empty `_world_state_cache: dict[str, tuple[str, float]]`
    - Implement `decompose_task(self, instruction, task_id, scene_context=None) -> PlanGraph | None` delegating to TaskDecomposer
    - Implement `analyze_failure(self, event: ExecutionEvent) -> tuple[str, list[str]]` delegating to RecoveryAdvisor with `event.failure_code`
    - Implement `update_world_state(self, robot_id, ref_uri, timestamp) -> bool` storing in cache, returning False if robot_id is empty
    - Implement `get_world_state_ref(self, robot_id) -> tuple[str, float] | None` returning cached entry or None
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [ ]* 7.2 Write property test for WorldState cache
    - **Property 11: WorldState cache returns most recent entry**
    - **Validates: Requirements 6.1, 6.4**

  - [ ]* 7.3 Write unit tests for Agent orchestration
    - Test Agent.decompose_task delegates to TaskDecomposer (Req 14.2)
    - Test Agent.analyze_failure delegates to RecoveryAdvisor (Req 14.3)
    - Test Agent initialization creates all sub-components (Req 14.1)
    - Test update_world_state with empty robot_id returns False (Req 6.3)
    - _Requirements: 14.1, 14.2, 14.3, 6.3_

- [ ] 8. Implement PlanGraph and ExecutionEvent converters
  - [ ] 8.1 Create converters module with PlanGraph ↔ Proto and ExecutionEvent ↔ Proto
    - Create `roboweave_cloud_agent/roboweave_cloud_agent/converters.py`
    - Implement `plan_graph_to_proto(pg: PlanGraph) -> PlanGraphProto` mapping all fields; serialize `PlanNode.inputs` and `PlanNode.constraints` dicts via `JsonEnvelope.wrap()` into `inputs_envelope_json` and `constraints_envelope_json` string fields; map `RetryPolicy`, `SuccessCondition`, `FailurePolicy` fields
    - Implement `plan_graph_from_proto(proto) -> PlanGraph` reversing the conversion; deserialize `inputs_envelope_json` and `constraints_envelope_json` back into Python dicts
    - Implement `event_to_proto(ev: ExecutionEvent) -> ExecutionEventProto` mapping all fields; use `.value` for enum fields
    - Implement `event_from_proto(proto) -> ExecutionEvent` reversing the conversion; use enum lookup for event_type and severity
    - Use duck-typed attribute access so converters work with both real proto objects and `types.SimpleNamespace` test stubs
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 11.1, 11.2_

  - [ ]* 8.2 Write property test for PlanGraph round-trip conversion
    - **Property 1: PlanGraph round-trip conversion**
    - **Validates: Requirements 10.6**

  - [ ]* 8.3 Write property test for ExecutionEvent round-trip conversion
    - **Property 2: ExecutionEvent round-trip conversion**
    - **Validates: Requirements 11.3**

- [ ] 9. Checkpoint - Verify converters and agent
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Implement gRPC server and CloudAgentServicer
  - [ ] 10.1 Create CloudAgentServicer with RPC handlers
    - Create `roboweave_cloud_agent/roboweave_cloud_agent/grpc_server.py`
    - Implement `CloudAgentServicer.__init__(self, agent: Agent)`
    - Implement `SubmitTask(self, request, context)`: validate instruction not empty (return ERROR if empty), call `agent.decompose_task`, convert result via `plan_graph_to_proto`, return `SubmitTaskResponse` with PLAN or REJECTION
    - Implement `SubmitTaskStream(self, request, context)`: yield STATUS_UPDATE, call decompose, yield PLAN_COMPLETE or ERROR_OCCURRED with is_final=True; check `context.is_active()` before each yield
    - Implement `AnalyzeFailure(self, request, context)`: convert event via `event_from_proto`, call `agent.analyze_failure`, return `AnalyzeFailureResponse` with analysis, recovery_actions, rationale_summary
    - Implement `UpdateWorldState(self, request, context)`: call `agent.update_world_state`, return `UpdateWorldStateResponse` with accepted flag
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3_

  - [ ] 10.2 Implement gRPC server lifecycle (serve function)
    - Implement `serve(config_path: str)` that loads config, creates Agent, creates gRPC server, registers CloudAgentServicer, binds to configured host:port, logs address, handles SIGINT/SIGTERM for graceful shutdown with configurable grace period
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ] 10.3 Create __main__.py entry point
    - Create `roboweave_cloud_agent/roboweave_cloud_agent/__main__.py`
    - Parse command-line argument or `ROBOWEAVE_CLOUD_AGENT_CONFIG` environment variable for config path
    - Call `serve(config_path)`
    - _Requirements: 2.6, 13.5_

  - [ ]* 10.4 Write unit tests for CloudAgentServicer RPC handlers
    - Test SubmitTask with empty instruction returns ERROR response (Req 3.5)
    - Test SubmitTask with unrecognized instruction returns REJECTION (Req 3.4)
    - Test SubmitTask with "pick up cup" returns PLAN response (Req 3.3)
    - Test SubmitTaskStream yields STATUS_UPDATE then PLAN_COMPLETE (Req 4.1, 4.2)
    - Test SubmitTaskStream with unrecognized instruction yields ERROR_OCCURRED (Req 4.3)
    - Test AnalyzeFailure with known error code returns recovery actions (Req 5.2)
    - Test AnalyzeFailure with unknown code returns empty actions (Req 5.3)
    - Test UpdateWorldState with valid robot_id returns accepted=True (Req 6.2)
    - Test UpdateWorldState with empty robot_id returns accepted=False (Req 6.3)
    - _Requirements: 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 5.2, 5.3, 6.2, 6.3_

- [ ] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate the 11 universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All property tests use Hypothesis with `max_examples=100` and `deadline=None`
- All pure-Python component tests run without gRPC dependency (converters use duck-typed `types.SimpleNamespace` stubs)
- This is a standalone Python package using `pyproject.toml` — no ROS2, no `ament_python`, no `package.xml`
