"""ConditionCheckNode — BT node evaluating conditions against WorldState."""

from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

from .skill_action import BTStatus

if TYPE_CHECKING:
    from roboweave_runtime.world_model import WorldModel


class ConditionCheckNode:
    """BT node that evaluates a precondition expression against WorldState."""

    def __init__(
        self,
        name: str,
        condition_fn: Callable[[Any], bool],
        world_model: WorldModel,
    ) -> None:
        """
        Args:
            name: Node name for debugging.
            condition_fn: Callable that takes a WorldState and returns True if satisfied.
            world_model: WorldModel instance to query.
        """
        self.name = name
        self._condition_fn = condition_fn
        self._world_model = world_model
        self.status: BTStatus = BTStatus.RUNNING

    def tick(self) -> BTStatus:
        """Evaluate the condition against current WorldState."""
        try:
            world_state = self._world_model.get_world_state()
            satisfied = self._condition_fn(world_state)
            self.status = BTStatus.SUCCESS if satisfied else BTStatus.FAILURE
        except Exception:
            self.status = BTStatus.FAILURE
        return self.status

    def reset(self) -> None:
        """Reset node state."""
        self.status = BTStatus.RUNNING
