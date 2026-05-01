from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .base import VersionedModel
from .refs import DataRef


class TaskPriority(str, Enum):
    """Priority level for a task."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    """Execution status of a task."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RetryPolicy(BaseModel):
    """Retry configuration for a plan node."""

    max_retries: int = 3
    backoff_ms: int = 500
    backoff_strategy: str = "fixed"


class SuccessCondition(VersionedModel):
    """Conditions that define task success."""

    conditions: dict[str, Any] = Field(default_factory=dict)


class FailurePolicy(VersionedModel):
    """Policy for handling task failures."""

    max_retry: int = 3
    fallback: str = "ask_user_clarification"


class SceneContext(VersionedModel):
    """Context about the scene for task execution."""

    scene_id: str = ""
    robot_id: str = ""
    additional: dict[str, Any] = Field(default_factory=dict)


class PlanNode(VersionedModel):
    """A single node in a task execution plan graph."""

    node_id: str
    node_type: str
    skill_name: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    preconditions: list[str] = Field(default_factory=list)
    postconditions: list[str] = Field(default_factory=list)
    retry_policy: RetryPolicy | None = None
    timeout_ms: int = 0
    on_success: list[str] = Field(default_factory=list)
    on_failure: list[str] = Field(default_factory=list)
    rollback_action: str = ""
    recovery_policy_id: str = ""
    required_resources: list[str] = Field(default_factory=list)
    interruptible: bool = True
    safety_level: str = "normal"


class PlanGraph(VersionedModel):
    """A directed acyclic graph of plan nodes."""

    plan_id: str
    task_id: str
    nodes: list[PlanNode] = Field(default_factory=list)
    success_condition: SuccessCondition = Field(default_factory=SuccessCondition)
    failure_policy: FailurePolicy = Field(default_factory=FailurePolicy)


class TaskRequest(VersionedModel):
    """A user-submitted task request."""

    task_id: str
    user_id: str
    instruction: str
    input_type: str = "text"
    context: SceneContext = Field(default_factory=SceneContext)
    attachment_refs: list[DataRef] = Field(default_factory=list)
    priority: TaskPriority = TaskPriority.NORMAL
    require_confirmation: bool = False
