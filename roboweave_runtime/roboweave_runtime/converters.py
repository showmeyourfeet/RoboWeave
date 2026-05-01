"""Converters — Pydantic ↔ ROS2 msg dict converters for RoboWeave runtime."""

from __future__ import annotations

from typing import Any

from roboweave_interfaces.event import ExecutionEvent
from roboweave_interfaces.base import JsonEnvelope
from roboweave_interfaces.world_state import RobotState, WorldState


def world_state_to_stamped_msg(ws: WorldState, header: dict[str, Any] | None = None) -> dict[str, Any]:
    """Convert WorldState to a WorldStateStamped-like dict."""
    envelope = JsonEnvelope.wrap(ws)
    return {
        "header": header or {},
        "world_state_json": envelope.model_dump_json(),
    }


def robot_state_msg_to_pydantic(msg: dict[str, Any]) -> RobotState:
    """Convert a RobotStateMsg-like dict to a RobotState Pydantic model."""
    if "payload_json" in msg:
        envelope = JsonEnvelope.model_validate_json(msg["payload_json"])
        return RobotState.model_validate_json(envelope.payload_json)
    return RobotState(**msg)


def execution_event_to_msg(event: ExecutionEvent) -> dict[str, Any]:
    """Convert ExecutionEvent to an ExecutionEventMsg-like dict."""
    envelope = JsonEnvelope.wrap(event)
    return {
        "event_json": envelope.model_dump_json(),
    }


def task_status_to_msg(
    task_id: str,
    status: str,
    progress: float,
    current_node_id: str,
    failure_code: str,
    message: str,
) -> dict[str, Any]:
    """Convert task status fields to a TaskStatusMsg-like dict."""
    return {
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "current_node_id": current_node_id,
        "failure_code": failure_code,
        "message": message,
    }


def json_envelope_to_msg(envelope: JsonEnvelope) -> dict[str, Any]:
    """Convert a JsonEnvelope to a JsonEnvelopeMsg-like dict."""
    return {
        "schema_name": envelope.schema_name,
        "schema_version": envelope.schema_version,
        "payload_json": envelope.payload_json,
        "payload_hash": envelope.payload_hash,
    }


def msg_to_json_envelope(msg: dict[str, Any]) -> JsonEnvelope:
    """Convert a JsonEnvelopeMsg-like dict to a JsonEnvelope."""
    return JsonEnvelope(**msg)
