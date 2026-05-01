"""Shared pytest fixtures for roboweave_runtime tests."""

from __future__ import annotations

import pytest

from roboweave_runtime.world_model import WorldModel
from roboweave_runtime.resource_manager import ResourceManager
from roboweave_runtime.execution_monitor import ExecutionMonitor
from roboweave_runtime.skill_orchestrator import SkillOrchestrator
from roboweave_runtime.task_executor import TaskExecutor


@pytest.fixture
def world_model() -> WorldModel:
    """A WorldModel with a fixed clock for deterministic testing."""
    return WorldModel(publish_hz=1.0, clock=lambda: 100.0)


@pytest.fixture
def resource_manager() -> ResourceManager:
    return ResourceManager()


@pytest.fixture
def execution_monitor() -> ExecutionMonitor:
    return ExecutionMonitor()


@pytest.fixture
def skill_orchestrator(
    world_model: WorldModel,
    resource_manager: ResourceManager,
    execution_monitor: ExecutionMonitor,
) -> SkillOrchestrator:
    return SkillOrchestrator(world_model, resource_manager, execution_monitor)


@pytest.fixture
def task_executor(
    skill_orchestrator: SkillOrchestrator,
    world_model: WorldModel,
    execution_monitor: ExecutionMonitor,
) -> TaskExecutor:
    return TaskExecutor(skill_orchestrator, world_model, execution_monitor)
