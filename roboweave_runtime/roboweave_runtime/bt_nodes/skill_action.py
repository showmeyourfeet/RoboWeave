"""SkillActionNode — BT node wrapping skill execution."""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import TYPE_CHECKING

from roboweave_interfaces.skill import SkillCall, SkillResult, SkillStatus

if TYPE_CHECKING:
    from roboweave_runtime.skill_orchestrator import SkillOrchestrator


class BTStatus(str, Enum):
    """Lightweight BT status (avoids py_trees dependency)."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RUNNING = "RUNNING"


def skill_status_to_bt(status: SkillStatus) -> BTStatus:
    """Map SkillResult.status to BT status."""
    if status == SkillStatus.SUCCESS:
        return BTStatus.SUCCESS
    elif status in (SkillStatus.FAILED, SkillStatus.SAFETY_STOP):
        return BTStatus.FAILURE
    elif status in (
        SkillStatus.TIMEOUT,
        SkillStatus.CANCELLED,
        SkillStatus.INTERRUPTED,
    ):
        return BTStatus.FAILURE
    return BTStatus.RUNNING


class SkillActionNode:
    """BT node that wraps SkillOrchestrator.execute_skill()."""

    def __init__(
        self,
        name: str,
        skill_call: SkillCall,
        orchestrator: SkillOrchestrator,
    ) -> None:
        self.name = name
        self.skill_call = skill_call
        self._orchestrator = orchestrator
        self._result: SkillResult | None = None
        self._task: asyncio.Task | None = None  # type: ignore[type-arg]
        self.status: BTStatus = BTStatus.RUNNING

    def tick(self) -> BTStatus:
        """Execute a single tick of this node."""
        if self._result is not None:
            self.status = skill_status_to_bt(self._result.status)
            return self.status

        # Start execution if not already running
        if self._task is None:
            loop = asyncio.get_event_loop()
            self._task = loop.create_task(
                self._orchestrator.execute_skill(self.skill_call)
            )

        if self._task.done():
            try:
                self._result = self._task.result()
                self.status = skill_status_to_bt(self._result.status)
            except Exception:
                self.status = BTStatus.FAILURE
            return self.status

        self.status = BTStatus.RUNNING
        return BTStatus.RUNNING

    @property
    def result(self) -> SkillResult | None:
        return self._result

    def reset(self) -> None:
        """Reset node for re-execution."""
        self._result = None
        self._task = None
        self.status = BTStatus.RUNNING
