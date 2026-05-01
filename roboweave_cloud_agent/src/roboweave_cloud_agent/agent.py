"""Agent orchestrator for roboweave_cloud_agent."""

from __future__ import annotations

from typing import Any

from roboweave_interfaces.event import ExecutionEvent
from roboweave_interfaces.skill import SkillCategory, SkillDescriptor
from roboweave_interfaces.task import PlanGraph

from .recovery_advisor import RecoveryAdvisor
from .skill_selector import SkillSelector
from .task_decomposer import TaskDecomposer


class Agent:
    """Central orchestrator wiring TaskDecomposer, SkillSelector, RecoveryAdvisor."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize sub-components from config dict."""
        # Build SkillDescriptors from config
        descriptors = [
            SkillDescriptor(
                name=d["name"],
                category=SkillCategory(d["category"]),
                description=d["description"],
                version=d["version"],
            )
            for d in config.get("skill_descriptors", [])
        ]

        self._skill_selector = SkillSelector(descriptors)
        self._recovery_advisor = RecoveryAdvisor()
        self._task_decomposer = TaskDecomposer(
            templates=config.get("task_templates", []),
            skill_selector=self._skill_selector,
        )
        self._world_state_cache: dict[str, tuple[str, float]] = {}

    def decompose_task(
        self,
        instruction: str,
        task_id: str,
        scene_context: dict[str, Any] | None = None,
    ) -> PlanGraph | None:
        """Decompose instruction into a PlanGraph, or None if unrecognized."""
        return self._task_decomposer.decompose(
            instruction, task_id, scene_context
        )

    def analyze_failure(
        self, event: ExecutionEvent
    ) -> tuple[str, list[str]]:
        """Analyze a failure event. Returns (analysis_string, recovery_actions)."""
        return self._recovery_advisor.advise(event.failure_code)

    def update_world_state(
        self, robot_id: str, ref_uri: str, timestamp: float
    ) -> bool:
        """Store world state ref. Returns False if robot_id is empty."""
        if not robot_id:
            return False
        self._world_state_cache[robot_id] = (ref_uri, timestamp)
        return True

    def get_world_state_ref(self, robot_id: str) -> tuple[str, float] | None:
        """Get cached (ref_uri, timestamp) for robot_id, or None."""
        return self._world_state_cache.get(robot_id)
