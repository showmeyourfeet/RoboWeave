"""ExecutionMonitor — event publishing and recovery routing."""

from __future__ import annotations

import uuid
from typing import Any, Callable

from roboweave_interfaces.errors import ERROR_CODE_SPECS, ErrorCode, ErrorCodeSpec, Severity
from roboweave_interfaces.event import EventType, ExecutionEvent, RecoveryAction


class ExecutionMonitor:
    """Pure Python event publishing and recovery routing."""

    def __init__(
        self,
        error_code_specs: dict[ErrorCode, ErrorCodeSpec] | None = None,
    ) -> None:
        self._specs = error_code_specs if error_code_specs is not None else ERROR_CODE_SPECS
        self.on_event: Callable[[ExecutionEvent], None] | None = None

    # --- Event publishing ---

    def create_event(
        self,
        task_id: str,
        node_id: str,
        event_type: EventType,
        failure_code: str = "",
        severity: Severity = Severity.INFO,
        message: str = "",
        timestamp: float = 0.0,
    ) -> ExecutionEvent:
        """Factory method to create an ExecutionEvent with auto-generated event_id."""
        return ExecutionEvent(
            event_id=str(uuid.uuid4()),
            task_id=task_id,
            node_id=node_id,
            event_type=event_type,
            failure_code=failure_code,
            severity=severity,
            message=message,
            timestamp=timestamp,
        )

    def publish_event(self, event: ExecutionEvent) -> None:
        """Publish an ExecutionEvent. Populates recovery_candidates from ERROR_CODE_SPECS."""
        if event.failure_code:
            spec = self._lookup_spec(event.failure_code)
            if spec and spec.default_recovery_policy:
                event.recovery_candidates = [spec.default_recovery_policy]
        if self.on_event:
            self.on_event(event)

    # --- Recovery routing ---

    def request_recovery(
        self, failure_code: str, context: dict[str, Any]
    ) -> tuple[bool, RecoveryAction | None, str]:
        """
        Look up failure_code in ERROR_CODE_SPECS.
        Returns (success, recovery_action, message).
        """
        spec = self._lookup_spec(failure_code)
        if spec is None:
            return False, None, f"Unknown failure code: {failure_code}"

        if spec.recoverable and spec.default_recovery_policy:
            action = RecoveryAction(
                action_name=spec.default_recovery_policy,
                escalate_to_cloud=spec.escalate_to_cloud,
                escalate_to_user=spec.escalate_to_user,
                priority=0,
            )
            return True, action, f"Recovery: {spec.default_recovery_policy}"

        # Non-recoverable or no default policy
        action = RecoveryAction(
            action_name=spec.default_recovery_policy or "escalate",
            escalate_to_cloud=True,
            escalate_to_user=True,
            priority=99,
        )
        return True, action, "Non-recoverable: escalating"

    def build_recovery_chain(
        self, failure_code: str, extra_candidates: list[str]
    ) -> list[RecoveryAction]:
        """Build ordered list of RecoveryAction candidates sorted by ascending priority."""
        actions: list[RecoveryAction] = []
        spec = self._lookup_spec(failure_code)

        if spec and spec.default_recovery_policy:
            actions.append(
                RecoveryAction(
                    action_name=spec.default_recovery_policy,
                    escalate_to_cloud=spec.escalate_to_cloud,
                    escalate_to_user=spec.escalate_to_user,
                    priority=0,
                )
            )

        for i, candidate in enumerate(extra_candidates):
            actions.append(
                RecoveryAction(
                    action_name=candidate,
                    priority=i + 1,
                )
            )

        # Sort by ascending priority
        actions.sort(key=lambda a: a.priority)
        return actions

    # --- Internal ---

    def _lookup_spec(self, failure_code: str) -> ErrorCodeSpec | None:
        """Look up an ErrorCodeSpec by code string."""
        try:
            code = ErrorCode(failure_code)
        except ValueError:
            return None
        return self._specs.get(code)
