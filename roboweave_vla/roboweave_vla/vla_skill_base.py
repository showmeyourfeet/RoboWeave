"""VLASkillBase: Abstract base class for all VLA skills.

Provides concrete SkillProtocol methods so VLA skills integrate with
the unified skill orchestration lifecycle. Pure Python — no ROS2 imports.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from roboweave_interfaces.skill import (
    PreconditionResult,
    PostconditionResult,
    SkillCall,
    SkillCategory,
    SkillDescriptor,
    SkillLogs,
    SkillResult,
    SkillStatus,
)
from roboweave_interfaces.vla import VLAAction, VLAActionSpace, VLASafetyConstraints
from roboweave_interfaces.world_state import RobotState, WorldState

from .vla_monitor import VLAMonitor


class VLASkillBase(ABC):
    """Abstract base class for all VLA skills.

    Subclasses implement predict() and reset(). The base class provides
    concrete SkillProtocol methods (descriptor, execute, check_precondition,
    check_postcondition) so that VLA skills integrate with the unified
    skill orchestration lifecycle.
    """

    def __init__(self) -> None:
        self._cancelled = False

    # --- Abstract interface (subclass must implement) ---

    @property
    @abstractmethod
    def skill_name(self) -> str: ...

    @property
    @abstractmethod
    def supported_instructions(self) -> list[str]: ...

    @property
    @abstractmethod
    def action_space(self) -> VLAActionSpace: ...

    @property
    @abstractmethod
    def default_safety_constraints(self) -> VLASafetyConstraints: ...

    @abstractmethod
    async def predict(
        self,
        rgb: np.ndarray,
        depth: np.ndarray | None,
        robot_state: RobotState,
        instruction: str,
        **kwargs: Any,
    ) -> VLAAction: ...

    @abstractmethod
    async def reset(self) -> None: ...

    # --- Concrete SkillProtocol methods ---

    @property
    def descriptor(self) -> SkillDescriptor:
        """Build SkillDescriptor from abstract properties."""
        return SkillDescriptor(
            name=self.skill_name,
            category=SkillCategory.VLA,
            description=f"VLA skill: {self.skill_name}",
            version="0.1.0",
            input_schema={
                "instruction": "str",
                "arm_id": "str",
                "max_steps": "int",
                "timeout_sec": "float",
            },
            output_schema={},
            preconditions=[],
            postconditions=[],
            timeout_ms=int(self.default_safety_constraints.max_duration_sec * 1000),
            retry_limit=0,
            fallback_skills=[],
            safety_requirements=[],
            required_resources=[],
            exclusive_resources=[],
            estimated_duration_ms=int(
                self.default_safety_constraints.max_duration_sec * 1000
            ),
            realtime_level="soft_realtime",
            side_effects=["robot_motion"],
        )

    async def check_precondition(
        self, world_state: WorldState, inputs: dict[str, Any]
    ) -> PreconditionResult:
        """Default: satisfied. Subclasses may override."""
        return PreconditionResult(satisfied=True)

    async def execute(
        self, call: SkillCall, world_state: WorldState
    ) -> SkillResult:
        """Run the prediction loop. Delegates to predict() each step."""
        instruction = call.inputs.get("instruction", "")
        arm_id = call.inputs.get("arm_id", "default_arm")
        max_steps = int(call.inputs.get("max_steps", 0))
        timeout_sec = float(call.inputs.get("timeout_sec", 60.0))

        monitor = VLAMonitor(
            max_steps=max_steps,
            timeout_sec=timeout_sec,
            min_confidence_threshold=self.default_safety_constraints.min_confidence_threshold,
        )

        self._cancelled = False
        await self.reset()
        monitor.start()

        while not self._cancelled:
            try:
                rgb = np.zeros((100, 100, 3), dtype=np.uint8)
                action = await self.predict(rgb, None, world_state.robot, instruction)
            except Exception:
                return SkillResult(
                    skill_call_id=call.skill_call_id,
                    status=SkillStatus.FAILED,
                    failure_code="VLA_PREDICT_ERROR",
                    failure_message="predict() raised an exception",
                )

            monitor.record_step(action.confidence)
            status = monitor.check()

            if status.should_abort:
                return SkillResult(
                    skill_call_id=call.skill_call_id,
                    status=SkillStatus.FAILED,
                    failure_code=status.abort_reason,
                    failure_message=status.abort_reason,
                    logs=SkillLogs(extra={"steps_executed": monitor.steps_executed}),
                )

            if status.should_finish:
                return SkillResult(
                    skill_call_id=call.skill_call_id,
                    status=SkillStatus.SUCCESS,
                    logs=SkillLogs(extra={"steps_executed": monitor.steps_executed}),
                )

        # Cancelled
        await self.reset()
        return SkillResult(
            skill_call_id=call.skill_call_id,
            status=SkillStatus.CANCELLED,
            logs=SkillLogs(extra={"steps_executed": monitor.steps_executed}),
        )

    async def check_postcondition(
        self, world_state: WorldState, result: SkillResult
    ) -> PostconditionResult:
        """Default: satisfied. Subclasses may override."""
        return PostconditionResult(satisfied=True)

    def cancel(self) -> None:
        """Set cancellation flag to stop the prediction loop."""
        self._cancelled = True
