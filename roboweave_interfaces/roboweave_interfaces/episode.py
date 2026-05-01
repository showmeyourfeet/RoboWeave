from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field

from .base import VersionedModel
from .refs import DataRef, DepthRef, ImageRef, MaskRef, PointCloudRef, WorldStateRef


class EpisodeStatus(str, Enum):
    """Status of an episode recording."""

    RECORDING = "recording"
    PAUSED = "paused"
    COMPLETED_SUCCESS = "completed_success"
    COMPLETED_FAILURE = "completed_failure"
    CANCELLED = "cancelled"


class EpisodeLabels(VersionedModel):
    """Labels and metadata for an episode."""

    task_type: str = ""
    object_categories: list[str] = Field(default_factory=list)
    scene_type: str = ""
    success: bool = False
    failure_stage: str = ""
    failure_code: str = ""
    recovery_used: bool = False
    human_intervention: bool = False
    data_quality: str = "normal"
    tags: list[str] = Field(default_factory=list)


class SystemVersions(VersionedModel):
    """Version information for all system components at episode time."""

    timestamp: float = 0.0
    roboweave_version: str = ""
    cloud_agent_version: str = ""
    agent_prompt_version: str = ""
    skill_registry_version: str = ""
    perception_models: dict[str, str] = Field(default_factory=dict)
    vla_models: dict[str, str] = Field(default_factory=dict)
    planner_backend: str = ""
    planner_version: str = ""
    controller_version: str = ""
    hardware_config_hash: str = ""
    robot_urdf_hash: str = ""


class SkillLog(VersionedModel):
    """Log entry for a single skill execution within an episode."""

    skill_call_id: str
    skill_name: str
    status: str
    start_time: float
    end_time: float = 0.0
    runtime_ms: int = 0
    inputs_summary: dict[str, Any] = Field(default_factory=dict)
    outputs_summary: dict[str, Any] = Field(default_factory=dict)
    failure_code: str = ""
    model_version: str = ""


class FrameLog(VersionedModel):
    """Log entry for a single frame of data within an episode."""

    timestamp: float
    episode_id: str
    rgb_ref: ImageRef | None = None
    depth_ref: DepthRef | None = None
    point_cloud_ref: PointCloudRef | None = None
    mask_ref: MaskRef | None = None
    robot_state_ref: DataRef | None = None
    world_state_ref: WorldStateRef | None = None
    control_command_ref: DataRef | None = None
    labels: dict[str, Any] = Field(default_factory=dict)


class EpisodeLog(VersionedModel):
    """Complete log of a task execution episode."""

    episode_id: str
    task_id: str
    status: EpisodeStatus
    start_time: float
    end_time: float = 0.0
    duration_sec: float = 0.0
    task_instruction: str = ""
    plan_ref: DataRef | None = None
    skill_logs: list[SkillLog] = Field(default_factory=list)
    labels: EpisodeLabels = Field(default_factory=EpisodeLabels)
    failure_code: str = ""
    notes: str = ""
    system_versions: SystemVersions | None = None
