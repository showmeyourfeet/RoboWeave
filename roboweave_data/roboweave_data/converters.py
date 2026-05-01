"""Pure functions for Pydantic ↔ ROS2 message conversion.

Since ROS2 may not be available, converters work with dict representations
of messages when ROS2 imports fail.
"""

from __future__ import annotations

import json
from typing import Any

from roboweave_interfaces.episode import EpisodeLabels, SystemVersions
from roboweave_interfaces.event import EventType, ExecutionEvent
from roboweave_interfaces.errors import Severity

# Try importing ROS2 message types; fall back to dict-based approach
try:
    from roboweave_msgs.msg import (
        ExecutionEvent as ExecutionEventMsg,
        TaskStatus as TaskStatusMsg,
        SafetyStatus as SafetyStatusMsg,
        JsonEnvelope as JsonEnvelopeMsg,
    )

    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False


def task_status_msg_to_dict(msg: Any) -> dict[str, Any]:
    """TaskStatus msg → dict with task_id, status, progress, etc."""
    if HAS_ROS2 and hasattr(msg, "task_id"):
        return {
            "task_id": msg.task_id,
            "status": msg.status,
            "progress": msg.progress,
            "current_node_id": msg.current_node_id,
            "failure_code": msg.failure_code,
            "message": msg.message,
        }
    # Dict-based fallback
    if isinstance(msg, dict):
        return {
            "task_id": msg.get("task_id", ""),
            "status": msg.get("status", ""),
            "progress": msg.get("progress", 0.0),
            "current_node_id": msg.get("current_node_id", ""),
            "failure_code": msg.get("failure_code", ""),
            "message": msg.get("message", ""),
        }
    return {}


def execution_event_msg_to_model(msg: Any) -> ExecutionEvent:
    """ExecutionEvent msg → Pydantic ExecutionEvent."""
    if HAS_ROS2 and hasattr(msg, "event_id"):
        context = {}
        if hasattr(msg, "context_json") and msg.context_json:
            try:
                context = json.loads(msg.context_json)
            except (json.JSONDecodeError, TypeError):
                pass
        return ExecutionEvent(
            event_id=msg.event_id,
            task_id=msg.task_id,
            node_id=getattr(msg, "node_id", ""),
            event_type=EventType(msg.event_type),
            failure_code=getattr(msg, "failure_code", ""),
            severity=Severity(getattr(msg, "severity", "info")),
            message=getattr(msg, "message", ""),
            recovery_candidates=list(getattr(msg, "recovery_candidates", [])),
            timestamp=getattr(msg, "timestamp", 0.0),
            context=context,
        )
    # Dict-based fallback
    if isinstance(msg, dict):
        context = msg.get("context", {})
        if isinstance(context, str):
            try:
                context = json.loads(context)
            except (json.JSONDecodeError, TypeError):
                context = {}
        return ExecutionEvent(
            event_id=msg.get("event_id", ""),
            task_id=msg.get("task_id", ""),
            node_id=msg.get("node_id", ""),
            event_type=EventType(msg.get("event_type", "skill_started")),
            failure_code=msg.get("failure_code", ""),
            severity=Severity(msg.get("severity", "info")),
            message=msg.get("message", ""),
            recovery_candidates=msg.get("recovery_candidates", []),
            timestamp=msg.get("timestamp", 0.0),
            context=context,
        )
    raise ValueError(f"Cannot convert {type(msg)} to ExecutionEvent")


def execution_event_model_to_msg_dict(event: ExecutionEvent) -> dict[str, Any]:
    """Pydantic ExecutionEvent → msg dict (for round-trip testing)."""
    return {
        "event_id": event.event_id,
        "task_id": event.task_id,
        "node_id": event.node_id,
        "event_type": event.event_type.value,
        "failure_code": event.failure_code,
        "severity": event.severity.value,
        "message": event.message,
        "recovery_candidates": list(event.recovery_candidates),
        "timestamp": event.timestamp,
        "context": event.context,
    }


def safety_status_msg_to_dict(msg: Any) -> dict[str, Any]:
    """SafetyStatus msg → dict with safety_level, e_stop_active, etc."""
    if HAS_ROS2 and hasattr(msg, "safety_level"):
        return {
            "safety_level": msg.safety_level,
            "e_stop_active": msg.e_stop_active,
            "collision_detected": msg.collision_detected,
            "active_violations": list(getattr(msg, "active_violations", [])),
        }
    # Dict-based fallback
    if isinstance(msg, dict):
        return {
            "safety_level": msg.get("safety_level", ""),
            "e_stop_active": msg.get("e_stop_active", False),
            "collision_detected": msg.get("collision_detected", False),
            "active_violations": msg.get("active_violations", []),
        }
    return {}


def episode_labels_to_json_envelope(labels: EpisodeLabels) -> str:
    """EpisodeLabels → JsonEnvelope JSON string."""
    return labels.model_dump_json()


def json_envelope_to_episode_labels(json_str: str) -> EpisodeLabels:
    """JsonEnvelope JSON string → EpisodeLabels."""
    return EpisodeLabels.model_validate_json(json_str)


def system_versions_to_json_envelope(versions: SystemVersions) -> str:
    """SystemVersions → JsonEnvelope JSON string."""
    return versions.model_dump_json()


def json_envelope_to_system_versions(json_str: str) -> SystemVersions:
    """JsonEnvelope JSON string → SystemVersions."""
    return SystemVersions.model_validate_json(json_str)
