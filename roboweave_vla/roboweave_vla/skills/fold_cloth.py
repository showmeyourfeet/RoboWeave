"""MockFoldClothSkill: Synthetic fold_cloth skill for integration testing."""

from __future__ import annotations

from typing import Any

import numpy as np

from roboweave_interfaces.vla import (
    VLAAction,
    VLAActionSpace,
    VLAActionType,
    VLASafetyConstraints,
)
from roboweave_interfaces.world_state import RobotState, SE3

from ..vla_skill_base import VLASkillBase


class MockFoldClothSkill(VLASkillBase):
    """Synthetic fold_cloth skill for integration testing."""

    def __init__(self, fold_sequence_length: int = 10) -> None:
        super().__init__()
        self._fold_sequence_length = fold_sequence_length
        self._step: int = 0

    @property
    def skill_name(self) -> str:
        return "fold_cloth"

    @property
    def supported_instructions(self) -> list[str]:
        return ["fold the cloth", "fold cloth"]

    @property
    def action_space(self) -> VLAActionSpace:
        return VLAActionSpace(
            supported_action_types=[
                VLAActionType.DELTA_EEF_POSE,
                VLAActionType.GRIPPER_COMMAND,
            ],
            control_frequency_hz=10.0,
        )

    @property
    def default_safety_constraints(self) -> VLASafetyConstraints:
        return VLASafetyConstraints(allow_contact=True)

    async def predict(
        self,
        rgb: np.ndarray,
        depth: np.ndarray | None,
        robot_state: RobotState,
        instruction: str,
        **kwargs: Any,
    ) -> VLAAction:
        """Return deterministic delta_eef_pose for steps < fold_sequence_length,
        then gripper_command(open) to signal completion."""
        current_step = self._step
        self._step += 1

        if current_step >= self._fold_sequence_length:
            return VLAAction(
                action_type=VLAActionType.GRIPPER_COMMAND,
                gripper_command={"action": "open"},
                confidence=0.9,
            )

        # Deterministic small delta with confidence in [0.7, 0.95]
        confidence = 0.7 + 0.25 * (current_step / max(self._fold_sequence_length, 1))
        delta = 0.01 * (current_step + 1)
        return VLAAction(
            action_type=VLAActionType.DELTA_EEF_POSE,
            delta_pose=SE3(
                position=[delta, 0.0, -delta],
                quaternion=[0.0, 0.0, 0.0, 1.0],
            ),
            confidence=confidence,
        )

    async def reset(self) -> None:
        """Reset internal step counter to zero."""
        self._step = 0
