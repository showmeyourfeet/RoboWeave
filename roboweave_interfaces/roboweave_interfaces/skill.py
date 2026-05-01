from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field

from .base import VersionedModel


class SkillCategory(str, Enum):
    """Category of a skill."""

    PERCEPTION = "perception"
    PLANNING = "planning"
    VLA = "vla"
    CONTROL = "control"
    COMPOSITE = "composite"


class SkillStatus(str, Enum):
    """Outcome status of a skill execution."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"
    SAFETY_STOP = "safety_stop"


class SkillLogs(VersionedModel):
    """Diagnostic logs from a skill execution."""

    runtime_ms: int = 0
    model_version: str = ""
    backend: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class PreconditionResult(VersionedModel):
    """Result of evaluating skill preconditions."""

    satisfied: bool
    unsatisfied_conditions: list[str] = Field(default_factory=list)
    message: str = ""


class PostconditionResult(VersionedModel):
    """Result of evaluating skill postconditions."""

    satisfied: bool
    unsatisfied_conditions: list[str] = Field(default_factory=list)
    message: str = ""


class SkillDescriptor(VersionedModel):
    """Declarative description of a skill's interface and requirements."""

    name: str
    category: SkillCategory
    description: str
    version: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    preconditions: list[str] = Field(default_factory=list)
    postconditions: list[str] = Field(default_factory=list)
    timeout_ms: int = 5000
    retry_limit: int = 2
    fallback_skills: list[str] = Field(default_factory=list)
    safety_requirements: list[str] = Field(default_factory=list)
    required_resources: list[str] = Field(default_factory=list)
    exclusive_resources: list[str] = Field(default_factory=list)
    estimated_duration_ms: int = 0
    realtime_level: str = "non_realtime"
    side_effects: list[str] = Field(default_factory=list)


class SkillCall(VersionedModel):
    """A request to execute a skill."""

    skill_call_id: str
    skill_name: str
    task_id: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int = 5000


class SkillResult(VersionedModel):
    """Result of a skill execution."""

    skill_call_id: str
    status: SkillStatus
    outputs: dict[str, Any] = Field(default_factory=dict)
    failure_code: str = ""
    failure_message: str = ""
    logs: SkillLogs | None = None
