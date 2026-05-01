"""SkillOrchestrator — skill registry and execution lifecycle."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol, runtime_checkable

from roboweave_interfaces.skill import PreconditionResult, PostconditionResult, SkillCall, SkillCategory, SkillDescriptor, SkillResult, SkillStatus
from roboweave_interfaces.world_state import WorldState

from .execution_monitor import ExecutionMonitor
from .resource_manager import ResourceManager
from .world_model import WorldModel


@runtime_checkable
class SkillProtocol(Protocol):
    """Protocol that all skills must implement."""

    @property
    def descriptor(self) -> SkillDescriptor: ...

    async def execute(
        self, call: SkillCall, world_state: WorldState
    ) -> SkillResult: ...

    def check_precondition(self, world_state: WorldState) -> PreconditionResult: ...

    def check_postcondition(self, world_state: WorldState) -> PostconditionResult: ...


class SkillOrchestrator:
    """Pure Python skill registry and execution orchestrator."""

    def __init__(
        self,
        world_model: WorldModel,
        resource_manager: ResourceManager,
        execution_monitor: ExecutionMonitor,
    ) -> None:
        self._world_model = world_model
        self._resource_manager = resource_manager
        self._execution_monitor = execution_monitor
        self._registry: dict[str, tuple[SkillProtocol, SkillDescriptor]] = {}
        self._running: dict[str, asyncio.Task[Any]] = {}

    # --- Registration ---

    def register_skill(self, skill: SkillProtocol) -> None:
        """Register a skill. Validates SkillProtocol compliance."""
        if not isinstance(skill, SkillProtocol):
            raise TypeError(
                f"Skill does not implement SkillProtocol: {type(skill).__name__}"
            )
        desc = skill.descriptor
        self._registry[desc.name] = (skill, desc)

    def list_skills(
        self, category_filter: str = ""
    ) -> list[tuple[str, SkillDescriptor]]:
        """Return registered skills, optionally filtered by category."""
        results: list[tuple[str, SkillDescriptor]] = []
        for name, (_, desc) in self._registry.items():
            if not category_filter or desc.category.value == category_filter:
                results.append((name, desc))
        return results

    def get_skill_health(self, skill_name: str) -> tuple[bool, str, str]:
        """Return (success, status, diagnostics_json) for a skill."""
        if skill_name not in self._registry:
            return False, "not_found", "{}"
        return True, "healthy", "{}"

    def is_skill_registered(self, skill_name: str) -> bool:
        """Check if a skill is registered."""
        return skill_name in self._registry

    # --- Execution ---

    async def execute_skill(self, call: SkillCall) -> SkillResult:
        """
        Full skill execution lifecycle:
        1. Look up skill in registry
        2. Acquire resources via ResourceManager
        3. Check preconditions against WorldState
        4. Execute skill
        5. Check postconditions
        6. Release resources
        """
        # 1. Look up skill
        entry = self._registry.get(call.skill_name)
        if entry is None:
            return SkillResult(
                skill_call_id=call.skill_call_id,
                status=SkillStatus.FAILED,
                failure_code="TSK_SKILL_NOT_FOUND",
                failure_message=f"Skill not found: {call.skill_name}",
            )

        skill, desc = entry
        holder = call.skill_call_id

        try:
            # 2. Acquire resources
            shared = list(desc.required_resources)
            exclusive = list(desc.exclusive_resources)
            if shared or exclusive:
                ok, msg = self._resource_manager.acquire(holder, shared, exclusive)
                if not ok:
                    return SkillResult(
                        skill_call_id=call.skill_call_id,
                        status=SkillStatus.FAILED,
                        failure_code="TSK_RESOURCE_CONFLICT",
                        failure_message=msg,
                    )

            # 3. Check preconditions
            world_state = self._world_model.get_world_state()
            pre_result = skill.check_precondition(world_state)
            if not pre_result.satisfied:
                return SkillResult(
                    skill_call_id=call.skill_call_id,
                    status=SkillStatus.FAILED,
                    failure_code="TSK_PRECONDITION_FAILED",
                    failure_message=pre_result.message
                    or "; ".join(pre_result.unsatisfied_conditions),
                )

            # 4. Execute skill
            task = asyncio.ensure_future(skill.execute(call, world_state))
            self._running[call.skill_call_id] = task
            try:
                result = await asyncio.wait_for(
                    task, timeout=call.timeout_ms / 1000.0
                )
            except asyncio.TimeoutError:
                return SkillResult(
                    skill_call_id=call.skill_call_id,
                    status=SkillStatus.TIMEOUT,
                    failure_code="TIMEOUT",
                    failure_message=f"Skill timed out after {call.timeout_ms}ms",
                )
            except asyncio.CancelledError:
                return SkillResult(
                    skill_call_id=call.skill_call_id,
                    status=SkillStatus.CANCELLED,
                    failure_code="CANCELLED",
                    failure_message="Skill was cancelled",
                )

            # 5. Check postconditions
            if result.status == SkillStatus.SUCCESS:
                world_state = self._world_model.get_world_state()
                post_result = skill.check_postcondition(world_state)
                if not post_result.satisfied:
                    return SkillResult(
                        skill_call_id=call.skill_call_id,
                        status=SkillStatus.FAILED,
                        failure_code="TSK_POSTCONDITION_FAILED",
                        failure_message=post_result.message
                        or "; ".join(post_result.unsatisfied_conditions),
                    )

            return result

        finally:
            # 6. Release resources
            self._resource_manager.release(holder)
            self._running.pop(call.skill_call_id, None)

    async def cancel_skill(self, skill_call_id: str) -> None:
        """Cancel a running skill and release its resources."""
        task = self._running.get(skill_call_id)
        if task and not task.done():
            task.cancel()
        self._resource_manager.release(skill_call_id)
        self._running.pop(skill_call_id, None)
