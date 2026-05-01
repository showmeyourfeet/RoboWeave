from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field

from .base import VersionedModel
from .errors import Severity


class EventType(str, Enum):
    """Type of execution event."""

    SKILL_STARTED = "skill_started"
    SKILL_SUCCEEDED = "skill_succeeded"
    SKILL_FAILED = "skill_failed"
    SKILL_TIMEOUT = "skill_timeout"
    PRECONDITION_FAILED = "precondition_failed"
    POSTCONDITION_FAILED = "postcondition_failed"
    SAFETY_TRIGGERED = "safety_triggered"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_SUCCEEDED = "recovery_succeeded"
    RECOVERY_FAILED = "recovery_failed"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"


class ExecutionEvent(VersionedModel):
    """A structured execution event for monitoring and recovery."""

    event_id: str
    task_id: str
    node_id: str = ""
    event_type: EventType
    failure_code: str = ""
    severity: Severity = Severity.INFO
    message: str = ""
    recovery_candidates: list[str] = Field(default_factory=list)
    timestamp: float = 0.0
    context: dict[str, Any] = Field(default_factory=dict)


class RecoveryAction(VersionedModel):
    """A recovery action to be executed in response to a failure."""

    action_name: str
    params: dict[str, Any] = Field(default_factory=dict)
    escalate_to_cloud: bool = False
    escalate_to_user: bool = False
    priority: int = 0
