"""PlanGraph/ExecutionEvent ↔ Proto converters.

Uses duck-typed attribute access so converters work with both real proto
objects and types.SimpleNamespace test stubs.
"""

from __future__ import annotations

import json
import types
from typing import Any

from roboweave_interfaces.base import JsonEnvelope, VersionedModel
from roboweave_interfaces.errors import Severity
from roboweave_interfaces.event import EventType, ExecutionEvent
from roboweave_interfaces.task import (
    FailurePolicy,
    PlanGraph,
    PlanNode,
    RetryPolicy,
    SuccessCondition,
)


# --- Helper for wrapping dicts as JSON envelopes ---


class _DictModel(VersionedModel):
    """Temporary model for wrapping arbitrary dicts via JsonEnvelope."""

    data: dict[str, Any] = {}


def _dict_to_envelope_json(d: dict[str, Any]) -> str:
    """Serialize a dict into a JsonEnvelope JSON string."""
    if not d:
        return ""
    model = _DictModel(data=d)
    envelope = JsonEnvelope.wrap(model)
    return envelope.model_dump_json()


def _envelope_json_to_dict(envelope_json: str) -> dict[str, Any]:
    """Deserialize a JsonEnvelope JSON string back into a dict."""
    if not envelope_json:
        return {}
    envelope = JsonEnvelope.model_validate_json(envelope_json)
    payload = json.loads(envelope.payload_json)
    return payload.get("data", {})


# --- PlanGraph converters ---


def plan_graph_to_proto(pg: PlanGraph) -> types.SimpleNamespace:
    """Convert PlanGraph Pydantic model → PlanGraphProto (SimpleNamespace)."""
    nodes = []
    for node in pg.nodes:
        retry_policy_proto = None
        if node.retry_policy is not None:
            retry_policy_proto = types.SimpleNamespace(
                max_retries=node.retry_policy.max_retries,
                backoff_ms=node.retry_policy.backoff_ms,
                backoff_strategy=node.retry_policy.backoff_strategy,
            )

        node_proto = types.SimpleNamespace(
            schema_version=node.schema_version,
            node_id=node.node_id,
            node_type=node.node_type,
            skill_name=node.skill_name,
            inputs_envelope_json=_dict_to_envelope_json(node.inputs),
            constraints_envelope_json=_dict_to_envelope_json(node.constraints),
            depends_on=list(node.depends_on),
            preconditions=list(node.preconditions),
            postconditions=list(node.postconditions),
            retry_policy=retry_policy_proto,
            timeout_ms=node.timeout_ms,
            on_success=list(node.on_success),
            on_failure=list(node.on_failure),
            rollback_action=node.rollback_action,
            recovery_policy_id=node.recovery_policy_id,
            required_resources=list(node.required_resources),
            interruptible=node.interruptible,
            safety_level=node.safety_level,
        )
        nodes.append(node_proto)

    # Success condition: convert dict[str, Any] -> dict[str, str]
    conditions_map = {
        k: json.dumps(v) if not isinstance(v, str) else v
        for k, v in pg.success_condition.conditions.items()
    }

    return types.SimpleNamespace(
        schema_version=pg.schema_version,
        plan_id=pg.plan_id,
        task_id=pg.task_id,
        nodes=nodes,
        success_condition=types.SimpleNamespace(conditions=conditions_map),
        failure_policy=types.SimpleNamespace(
            max_retry=pg.failure_policy.max_retry,
            fallback=pg.failure_policy.fallback,
        ),
    )


def plan_graph_from_proto(proto: Any) -> PlanGraph:
    """Convert PlanGraphProto (or SimpleNamespace) → PlanGraph Pydantic model."""
    nodes = []
    for node_proto in proto.nodes:
        retry_policy = None
        if node_proto.retry_policy is not None:
            retry_policy = RetryPolicy(
                max_retries=node_proto.retry_policy.max_retries,
                backoff_ms=node_proto.retry_policy.backoff_ms,
                backoff_strategy=node_proto.retry_policy.backoff_strategy,
            )

        node = PlanNode(
            node_id=node_proto.node_id,
            node_type=node_proto.node_type,
            skill_name=node_proto.skill_name,
            inputs=_envelope_json_to_dict(node_proto.inputs_envelope_json),
            constraints=_envelope_json_to_dict(node_proto.constraints_envelope_json),
            depends_on=list(node_proto.depends_on),
            preconditions=list(node_proto.preconditions),
            postconditions=list(node_proto.postconditions),
            retry_policy=retry_policy,
            timeout_ms=node_proto.timeout_ms,
            on_success=list(node_proto.on_success),
            on_failure=list(node_proto.on_failure),
            rollback_action=node_proto.rollback_action,
            recovery_policy_id=node_proto.recovery_policy_id,
            required_resources=list(node_proto.required_resources),
            interruptible=node_proto.interruptible,
            safety_level=node_proto.safety_level,
        )
        nodes.append(node)

    # Success condition: convert dict[str, str] -> dict[str, Any]
    conditions_raw = dict(proto.success_condition.conditions)
    conditions: dict[str, Any] = {}
    for k, v in conditions_raw.items():
        try:
            conditions[k] = json.loads(v)
        except (json.JSONDecodeError, TypeError):
            conditions[k] = v

    return PlanGraph(
        plan_id=proto.plan_id,
        task_id=proto.task_id,
        nodes=nodes,
        success_condition=SuccessCondition(conditions=conditions),
        failure_policy=FailurePolicy(
            max_retry=proto.failure_policy.max_retry,
            fallback=proto.failure_policy.fallback,
        ),
    )


# --- ExecutionEvent converters ---


def event_to_proto(ev: ExecutionEvent) -> types.SimpleNamespace:
    """Convert ExecutionEvent Pydantic model → ExecutionEventProto (SimpleNamespace)."""
    return types.SimpleNamespace(
        schema_version=ev.schema_version,
        event_id=ev.event_id,
        task_id=ev.task_id,
        node_id=ev.node_id,
        event_type=ev.event_type.value,
        failure_code=ev.failure_code,
        severity=ev.severity.value,
        message=ev.message,
        recovery_candidates=list(ev.recovery_candidates),
        timestamp=ev.timestamp,
    )


def event_from_proto(proto: Any) -> ExecutionEvent:
    """Convert ExecutionEventProto (or SimpleNamespace) → ExecutionEvent Pydantic model."""
    return ExecutionEvent(
        event_id=proto.event_id,
        task_id=proto.task_id,
        node_id=proto.node_id,
        event_type=EventType(proto.event_type),
        failure_code=proto.failure_code,
        severity=Severity(proto.severity),
        message=proto.message,
        recovery_candidates=list(proto.recovery_candidates),
        timestamp=proto.timestamp,
    )
