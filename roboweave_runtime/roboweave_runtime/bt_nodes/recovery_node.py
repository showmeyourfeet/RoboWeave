"""RecoveryNode — BT decorator that catches child failure and attempts recovery."""

from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

from .skill_action import BTStatus

if TYPE_CHECKING:
    pass


class RecoveryNode:
    """BT decorator that catches child FAILURE and attempts a recovery strategy."""

    def __init__(
        self,
        name: str,
        child: Any,
        recovery_fn: Callable[[], bool],
        max_retries: int = 1,
    ) -> None:
        """
        Args:
            name: Node name for debugging.
            child: The child BT node to wrap.
            recovery_fn: Callable that attempts recovery, returns True on success.
            max_retries: Maximum number of retry attempts after recovery.
        """
        self.name = name
        self._child = child
        self._recovery_fn = recovery_fn
        self._max_retries = max_retries
        self._retry_count = 0
        self.status: BTStatus = BTStatus.RUNNING

    def tick(self) -> BTStatus:
        """Tick child; on failure, attempt recovery and optionally retry."""
        child_status = self._child.tick()

        if child_status == BTStatus.SUCCESS:
            self.status = BTStatus.SUCCESS
            return BTStatus.SUCCESS

        if child_status == BTStatus.RUNNING:
            self.status = BTStatus.RUNNING
            return BTStatus.RUNNING

        # Child failed
        if self._retry_count >= self._max_retries:
            self.status = BTStatus.FAILURE
            return BTStatus.FAILURE

        # Attempt recovery
        recovered = self._recovery_fn()
        if recovered:
            self._retry_count += 1
            self._child.reset()
            self.status = BTStatus.RUNNING
            return BTStatus.RUNNING

        # Recovery failed
        self.status = BTStatus.FAILURE
        return BTStatus.FAILURE

    def reset(self) -> None:
        """Reset node and child."""
        self._retry_count = 0
        self._child.reset()
        self.status = BTStatus.RUNNING
