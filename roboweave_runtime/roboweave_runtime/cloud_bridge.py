"""CloudBridge — Phase 1 stub (no cloud connection)."""

from __future__ import annotations

from typing import Any

from roboweave_interfaces.event import ExecutionEvent, RecoveryAction
from roboweave_interfaces.task import PlanGraph, TaskRequest
from roboweave_interfaces.world_state import WorldState


class CloudBridge:
    """Phase 1 stub. Exposes the gRPC client interface without connecting."""

    async def submit_task(self, task_request: TaskRequest) -> PlanGraph | None:
        """Stub: returns None (no cloud connection in Phase 1)."""
        return None

    async def analyze_failure(
        self, event: ExecutionEvent, world_state: WorldState
    ) -> list[RecoveryAction]:
        """Stub: returns empty list."""
        return []

    @property
    def is_connected(self) -> bool:
        return False
