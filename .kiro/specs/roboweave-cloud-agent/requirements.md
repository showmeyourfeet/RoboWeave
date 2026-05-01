# Requirements Document

## Introduction

The `roboweave_cloud_agent` package is the cloud-side LLM/VLM Agent for the RoboWeave system. It runs as a standalone gRPC server (not a ROS2 package) that the on-device runtime connects to via `CloudBridge`. The agent understands user instructions, decomposes tasks into structured `PlanGraph` objects, selects appropriate skills for plan nodes, and analyzes execution failures to suggest recovery strategies.

This is Phase 4 of the RoboWeave project. The MVP scope uses template-based task decomposition (no real LLM API calls), keyword-based skill selection, and `ErrorCodeSpec` lookup for recovery advice. The gRPC interface follows the `cloud_agent.proto` definition from architecture spec Section 4.1.3.

The package depends on `roboweave_interfaces` (Pydantic models: `PlanGraph`, `PlanNode`, `TaskRequest`, `WorldState`, `SkillDescriptor`, `ExecutionEvent`, `RecoveryAction`, `ErrorCodeSpec`, `JsonEnvelope`), `grpcio`, and `protobuf`.

## Glossary

- **Cloud_Agent_Service**: The gRPC service that hosts SubmitTask, SubmitTaskStream, AnalyzeFailure, and UpdateWorldState RPCs, defined by `cloud_agent.proto`.
- **gRPC_Server**: The process that binds the Cloud_Agent_Service to a network address and manages server lifecycle (start, graceful shutdown).
- **Task_Decomposer**: A component that takes a user instruction string and scene context, and produces a `PlanGraph` Pydantic model. MVP implementation uses template matching against known task patterns.
- **Skill_Selector**: A component that, given a plan node's description or intent, selects the most appropriate skill name from a registry of `SkillDescriptor` objects. MVP implementation uses keyword matching.
- **Recovery_Advisor**: A component that analyzes an `ExecutionEvent` failure and returns a list of suggested recovery action names. MVP implementation looks up the `ErrorCodeSpec` registry for the failure's error code.
- **PlanGraph**: A Pydantic model (`roboweave_interfaces.task.PlanGraph`) representing a directed acyclic graph of `PlanNode` objects that define a task execution plan.
- **PlanNode**: A Pydantic model (`roboweave_interfaces.task.PlanNode`) representing a single step in a plan with skill name, inputs, dependencies, pre/postconditions, retry policy, and resource requirements.
- **SkillDescriptor**: A Pydantic model (`roboweave_interfaces.skill.SkillDescriptor`) describing a skill's name, category, input/output schema, preconditions, postconditions, and resource requirements.
- **ErrorCodeSpec**: A Pydantic model (`roboweave_interfaces.errors.ErrorCodeSpec`) containing metadata for an error code including severity, recoverability, default recovery policy, and escalation flags.
- **ExecutionEvent**: A Pydantic model (`roboweave_interfaces.event.ExecutionEvent`) representing a structured execution event with event type, failure code, severity, and recovery candidates.
- **JsonEnvelope**: A Pydantic model (`roboweave_interfaces.base.JsonEnvelope`) used to wrap versioned Pydantic models for JSON transport over gRPC string fields.
- **WorldState_Cache**: An in-memory store within the cloud agent that holds the most recent `WorldState` reference URI and timestamp per robot, updated via the UpdateWorldState RPC.
- **Task_Template**: A predefined mapping from a task pattern (keyword or regex) to a `PlanGraph` skeleton, used by the MVP Task_Decomposer.
- **cloud_agent_params.yaml**: A YAML configuration file defining the gRPC server address, port, task templates, skill registry, and operational parameters.
- **cloud_agent.proto**: The Protocol Buffers definition file specifying the CloudAgentService gRPC interface, request/response messages, and PlanGraph proto structures.

## Requirements

### Requirement 1: Proto Compilation and Generated Code

**User Story:** As a developer, I want the `cloud_agent.proto` file compiled into Python gRPC stubs, so that the server and any future clients can use strongly-typed gRPC interfaces.

#### Acceptance Criteria

1. THE cloud_agent.proto file SHALL define the CloudAgentService with four RPCs: SubmitTask (unary), SubmitTaskStream (server-streaming), AnalyzeFailure (unary), and UpdateWorldState (unary), matching the architecture spec Section 4.1.3.
2. WHEN the proto file is compiled, THE build process SHALL produce `cloud_agent_pb2.py` and `cloud_agent_pb2_grpc.py` files in the package.
3. THE proto file SHALL define all message types specified in architecture spec Section 4.1.3: SubmitTaskRequest, SceneContext, AttachmentRef, SubmitTaskResponse, ResponseType, SubmitTaskStreamResponse, StreamEventType, ClarificationRequest, AnalyzeFailureRequest, AnalyzeFailureResponse, UpdateWorldStateRequest, UpdateWorldStateResponse, PlanGraphProto, PlanNodeProto, RetryPolicyProto, SuccessCondition, FailurePolicy, and ExecutionEventProto.

### Requirement 2: gRPC Server Lifecycle

**User Story:** As a system operator, I want the cloud agent to run as a gRPC server that starts, accepts connections, and shuts down gracefully, so that the on-device runtime can reliably connect and disconnect.

#### Acceptance Criteria

1. THE gRPC_Server SHALL bind to the address and port specified in cloud_agent_params.yaml.
2. THE gRPC_Server SHALL register the Cloud_Agent_Service implementation as a servicer on the gRPC server.
3. WHEN the gRPC_Server starts, THE gRPC_Server SHALL log the bound address and port.
4. WHEN a shutdown signal (SIGINT or SIGTERM) is received, THE gRPC_Server SHALL initiate a graceful shutdown with a configurable grace period, allowing in-flight RPCs to complete.
5. WHEN the grace period expires during shutdown, THE gRPC_Server SHALL forcefully terminate remaining RPCs.
6. THE gRPC_Server SHALL be launchable via a `__main__.py` entry point using `.venv/bin/python -m roboweave_cloud_agent`.

### Requirement 3: SubmitTask RPC — Task Decomposition

**User Story:** As the on-device runtime, I want to submit a user instruction and receive a structured PlanGraph, so that the task executor can orchestrate skill execution.

#### Acceptance Criteria

1. WHEN a SubmitTaskRequest is received, THE Cloud_Agent_Service SHALL extract the instruction, task_id, and scene context from the request.
2. WHEN a SubmitTaskRequest is received, THE Cloud_Agent_Service SHALL pass the instruction and context to the Task_Decomposer.
3. WHEN the Task_Decomposer produces a PlanGraph, THE Cloud_Agent_Service SHALL convert the PlanGraph Pydantic model to a PlanGraphProto message and return it in a SubmitTaskResponse with response_type set to PLAN.
4. IF the Task_Decomposer cannot decompose the instruction (no matching template), THEN THE Cloud_Agent_Service SHALL return a SubmitTaskResponse with response_type set to REJECTION and an error_message describing that the instruction is not recognized.
5. IF the SubmitTaskRequest has an empty instruction field, THEN THE Cloud_Agent_Service SHALL return a SubmitTaskResponse with response_type set to ERROR and an error_message indicating that the instruction is required.

### Requirement 4: SubmitTaskStream RPC — Streaming Task Decomposition

**User Story:** As the on-device runtime, I want to receive streaming status updates during task decomposition, so that I can display progress and partial results to the user.

#### Acceptance Criteria

1. WHEN a SubmitTaskRequest is received on the streaming endpoint, THE Cloud_Agent_Service SHALL yield a SubmitTaskStreamResponse with event_type STATUS_UPDATE and a status_summary indicating decomposition has started.
2. WHEN the Task_Decomposer produces a PlanGraph, THE Cloud_Agent_Service SHALL yield a SubmitTaskStreamResponse with event_type PLAN_COMPLETE, the full PlanGraphProto in partial_plan, and is_final set to true.
3. IF the Task_Decomposer cannot decompose the instruction, THEN THE Cloud_Agent_Service SHALL yield a SubmitTaskStreamResponse with event_type ERROR_OCCURRED, a status_summary describing the failure, and is_final set to true.
4. WHEN the client cancels the stream, THE Cloud_Agent_Service SHALL stop processing and clean up resources for that request.

### Requirement 5: AnalyzeFailure RPC — Recovery Advice

**User Story:** As the on-device runtime, I want to send a failure event to the cloud agent and receive recovery suggestions, so that the execution monitor can attempt automated recovery.

#### Acceptance Criteria

1. WHEN an AnalyzeFailureRequest is received, THE Cloud_Agent_Service SHALL extract the ExecutionEventProto and pass the failure_code and event context to the Recovery_Advisor.
2. WHEN the Recovery_Advisor produces recovery suggestions, THE Cloud_Agent_Service SHALL return an AnalyzeFailureResponse with the analysis string, the list of recovery_actions, and a rationale_summary explaining the recommendation.
3. IF the failure_code in the ExecutionEventProto is empty or not recognized, THEN THE Cloud_Agent_Service SHALL return an AnalyzeFailureResponse with an analysis indicating the failure code is unknown and an empty recovery_actions list.
4. WHEN the ErrorCodeSpec for the failure_code has escalate_to_user set to true, THE Recovery_Advisor SHALL include "ask_user_clarification" in the recovery_actions list.

### Requirement 6: UpdateWorldState RPC

**User Story:** As the on-device runtime, I want to push world state reference updates to the cloud agent, so that subsequent task decomposition and failure analysis can use current scene information.

#### Acceptance Criteria

1. WHEN an UpdateWorldStateRequest is received, THE Cloud_Agent_Service SHALL store the world_state_ref_uri and timestamp in the WorldState_Cache, keyed by robot_id.
2. WHEN an UpdateWorldStateRequest is received with a valid robot_id and world_state_ref_uri, THE Cloud_Agent_Service SHALL return an UpdateWorldStateResponse with accepted set to true.
3. IF the UpdateWorldStateRequest has an empty robot_id, THEN THE Cloud_Agent_Service SHALL return an UpdateWorldStateResponse with accepted set to false.
4. THE WorldState_Cache SHALL retain only the most recent entry per robot_id, replacing any previous entry.

### Requirement 7: Task Decomposer — Template-Based MVP

**User Story:** As a developer, I want a template-based task decomposer that maps known instruction patterns to PlanGraphs, so that the MVP can demonstrate end-to-end task flow without a real LLM.

#### Acceptance Criteria

1. THE Task_Decomposer SHALL load task templates from cloud_agent_params.yaml at initialization.
2. WHEN an instruction matches a template pattern (case-insensitive substring match), THE Task_Decomposer SHALL produce a PlanGraph by instantiating the matched template with the task_id and extracting object references from the instruction.
3. THE Task_Decomposer SHALL support at least the following MVP templates: "pick up {object}" producing a pick PlanGraph (detect → plan_grasp → plan_motion → execute_grasp), and "place {object} on {surface}" producing a place PlanGraph (plan_motion → open_gripper → retract).
4. WHEN an instruction matches a "pick up" template, THE Task_Decomposer SHALL produce a PlanGraph with nodes that have correct depends_on relationships forming a sequential chain.
5. WHEN no template matches the instruction, THE Task_Decomposer SHALL return None to indicate decomposition failure.
6. FOR ALL PlanGraphs produced by the Task_Decomposer, each PlanNode SHALL have a unique node_id within the graph.
7. FOR ALL PlanGraphs produced by the Task_Decomposer, each PlanNode SHALL have the skill_name field populated with a valid skill name from the skill registry.

### Requirement 8: Skill Selector — Keyword-Based MVP

**User Story:** As a developer, I want a keyword-based skill selector that matches plan node intents to registered skills, so that the task decomposer can assign concrete skills to abstract plan steps.

#### Acceptance Criteria

1. THE Skill_Selector SHALL load a list of SkillDescriptor objects from cloud_agent_params.yaml at initialization.
2. WHEN given a query string (node description or intent), THE Skill_Selector SHALL return the SkillDescriptor whose name or description has the highest keyword overlap with the query.
3. IF no skill has any keyword overlap with the query, THEN THE Skill_Selector SHALL return None.
4. THE Skill_Selector SHALL provide a method to list all registered skill names.
5. THE Skill_Selector SHALL be case-insensitive when matching keywords.

### Requirement 9: Recovery Advisor — ErrorCodeSpec Lookup MVP

**User Story:** As a developer, I want a recovery advisor that looks up the ErrorCodeSpec registry to suggest recovery actions, so that the MVP can demonstrate failure analysis without a real LLM.

#### Acceptance Criteria

1. WHEN given a failure_code string, THE Recovery_Advisor SHALL look up the corresponding ErrorCodeSpec from the `ERROR_CODE_SPECS` registry in `roboweave_interfaces.errors`.
2. WHEN an ErrorCodeSpec is found and has a non-empty default_recovery_policy, THE Recovery_Advisor SHALL include the default_recovery_policy in the returned recovery actions list.
3. WHEN an ErrorCodeSpec is found and has retryable set to true, THE Recovery_Advisor SHALL include "retry" in the returned recovery actions list.
4. WHEN an ErrorCodeSpec is found and has escalate_to_cloud set to true, THE Recovery_Advisor SHALL include "escalate_to_cloud" in the returned recovery actions list.
5. WHEN an ErrorCodeSpec is found and has escalate_to_user set to true, THE Recovery_Advisor SHALL include "ask_user_clarification" in the returned recovery actions list.
6. IF the failure_code does not match any ErrorCode enum value, THEN THE Recovery_Advisor SHALL return an empty recovery actions list and an analysis string indicating the code is unrecognized.
7. THE Recovery_Advisor SHALL return an analysis string that includes the error code, its severity, its module, and whether the error is recoverable.

### Requirement 10: PlanGraph ↔ Proto Conversion

**User Story:** As a developer, I want reliable conversion between PlanGraph Pydantic models and PlanGraphProto gRPC messages, so that the cloud agent can serialize plans for transport and deserialize incoming data.

#### Acceptance Criteria

1. THE Converter SHALL provide a function to convert a `PlanGraph` Pydantic model to a `PlanGraphProto` message, mapping all fields including nodes, success_condition, and failure_policy.
2. THE Converter SHALL provide a function to convert a `PlanGraphProto` message to a `PlanGraph` Pydantic model.
3. WHEN converting a PlanNode to a PlanNodeProto, THE Converter SHALL serialize the node's `inputs` dict as a JsonEnvelope JSON string in the `inputs_envelope_json` field.
4. WHEN converting a PlanNode to a PlanNodeProto, THE Converter SHALL serialize the node's `constraints` dict as a JsonEnvelope JSON string in the `constraints_envelope_json` field.
5. WHEN converting a PlanNodeProto to a PlanNode, THE Converter SHALL deserialize the `inputs_envelope_json` and `constraints_envelope_json` fields back into Python dicts.
6. FOR ALL valid PlanGraph Pydantic models, converting to PlanGraphProto and back SHALL produce an equivalent PlanGraph (round-trip property).

### Requirement 11: ExecutionEvent ↔ Proto Conversion

**User Story:** As a developer, I want reliable conversion between ExecutionEvent Pydantic models and ExecutionEventProto gRPC messages, so that failure analysis requests can be properly deserialized.

#### Acceptance Criteria

1. THE Converter SHALL provide a function to convert an `ExecutionEvent` Pydantic model to an `ExecutionEventProto` message, mapping all fields including event_id, task_id, node_id, event_type, failure_code, severity, message, recovery_candidates, and timestamp.
2. THE Converter SHALL provide a function to convert an `ExecutionEventProto` message to an `ExecutionEvent` Pydantic model.
3. FOR ALL valid ExecutionEvent Pydantic models, converting to ExecutionEventProto and back SHALL produce an equivalent ExecutionEvent (round-trip property).

### Requirement 12: Configuration File

**User Story:** As a system operator, I want a YAML configuration file for the cloud agent, so that I can tune server settings, task templates, and skill registries without code changes.

#### Acceptance Criteria

1. THE cloud_agent_params.yaml file SHALL define the gRPC server host address and port number.
2. THE cloud_agent_params.yaml file SHALL define a list of task templates, each with a pattern string and a PlanGraph skeleton (list of node definitions with skill_name, node_type, depends_on, and default inputs).
3. THE cloud_agent_params.yaml file SHALL define a list of skill descriptors, each with at minimum a name, category, and description.
4. THE cloud_agent_params.yaml file SHALL define the graceful shutdown timeout in seconds.
5. THE gRPC_Server SHALL load cloud_agent_params.yaml from a file path specified by a command-line argument or environment variable `ROBOWEAVE_CLOUD_AGENT_CONFIG`.

### Requirement 13: Package Structure and Entry Point

**User Story:** As a developer, I want the cloud agent organized as a standard Python package with a clear entry point, so that it can be installed, tested, and launched consistently.

#### Acceptance Criteria

1. THE package SHALL be structured with a `roboweave_cloud_agent/` source directory containing `__init__.py`, `__main__.py`, `agent.py`, `task_decomposer.py`, `skill_selector.py`, `recovery_advisor.py`, `grpc_server.py`, and a `converters.py` module.
2. THE package SHALL include a `proto/` directory containing `cloud_agent.proto`.
3. THE package SHALL include a `prompts/` directory (empty for MVP, placeholder for future LLM prompt templates).
4. THE package SHALL include a `pyproject.toml` declaring dependencies on `roboweave_interfaces`, `grpcio`, `grpcio-tools`, and `protobuf`.
5. WHEN installed, THE package SHALL be runnable via `.venv/bin/python -m roboweave_cloud_agent` which starts the gRPC server.
6. THE package SHALL include a `tests/` directory with `__init__.py` and `conftest.py`.

### Requirement 14: Agent Orchestrator

**User Story:** As a developer, I want a central agent module that wires together the Task_Decomposer, Skill_Selector, and Recovery_Advisor, so that the gRPC service handlers have a single entry point for business logic.

#### Acceptance Criteria

1. THE Agent SHALL accept a configuration dict (loaded from cloud_agent_params.yaml) and initialize the Task_Decomposer, Skill_Selector, and Recovery_Advisor.
2. WHEN the Agent's `decompose_task` method is called with an instruction and context, THE Agent SHALL invoke the Task_Decomposer and return the resulting PlanGraph or None.
3. WHEN the Agent's `analyze_failure` method is called with an ExecutionEvent, THE Agent SHALL invoke the Recovery_Advisor and return the analysis string and recovery actions list.
4. THE Agent SHALL provide a `get_world_state_ref` method that returns the cached world state reference URI for a given robot_id, or None if no state has been received.
5. THE Agent SHALL provide an `update_world_state` method that stores a world state reference URI and timestamp for a given robot_id.
