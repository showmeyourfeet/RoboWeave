"""SafetyGuard — pure Python state machine for safety level management."""

from __future__ import annotations

from roboweave_interfaces.safety import SafetyEvent, SafetyLevel


class SafetyGuard:
    """Manages the safety level state machine and emergency stop semantics."""

    def __init__(self) -> None:
        self._level: SafetyLevel = SafetyLevel.NORMAL
        self._e_stop_active: bool = False
        self._e_stop_latched: bool = False
        self._active_violations: list[str] = []

    @property
    def level(self) -> SafetyLevel:
        return self._level

    @property
    def e_stop_active(self) -> bool:
        return self._e_stop_active

    @property
    def e_stop_latched(self) -> bool:
        return self._e_stop_latched

    @property
    def active_violations(self) -> list[str]:
        return list(self._active_violations)

    def process_violations(self, violations: list[SafetyEvent]) -> SafetyLevel:
        """Update state machine based on new violations. Returns new level."""
        if self._e_stop_latched:
            return self._level

        for v in violations:
            if v.violation_type not in self._active_violations:
                self._active_violations.append(v.violation_type)

            # Escalate based on violation severity
            if v.safety_level == SafetyLevel.EMERGENCY_STOP:
                self._level = SafetyLevel.EMERGENCY_STOP
                self._e_stop_active = True
                self._e_stop_latched = True
            elif v.safety_level == SafetyLevel.CRITICAL:
                if self._level in (SafetyLevel.NORMAL, SafetyLevel.WARNING):
                    self._level = SafetyLevel.CRITICAL
            elif v.safety_level == SafetyLevel.WARNING:
                if self._level == SafetyLevel.NORMAL:
                    self._level = SafetyLevel.WARNING

        return self._level

    def emergency_stop(self) -> None:
        """Immediately transition to EMERGENCY_STOP and latch."""
        self._level = SafetyLevel.EMERGENCY_STOP
        self._e_stop_active = True
        self._e_stop_latched = True

    def release_stop(self, operator_id: str) -> tuple[bool, str]:
        """Release e-stop. Requires non-empty operator_id."""
        if not operator_id or not operator_id.strip():
            return (False, "operator_id is required to release e-stop")

        self._e_stop_active = False
        self._e_stop_latched = False
        self._level = SafetyLevel.NORMAL
        self._active_violations.clear()
        return (True, f"E-stop released by {operator_id.strip()}")

    def enter_safe_mode(self) -> None:
        """Transition to WARNING (safe mode)."""
        if not self._e_stop_latched:
            self._level = SafetyLevel.WARNING
            if "safe_mode" not in self._active_violations:
                self._active_violations.append("safe_mode")

    def clear_violations(self) -> SafetyLevel:
        """Clear all violations and auto-recover if not latched."""
        if self._e_stop_latched:
            return self._level

        self._active_violations.clear()
        if self._level == SafetyLevel.WARNING:
            self._level = SafetyLevel.NORMAL
        elif self._level == SafetyLevel.CRITICAL:
            self._level = SafetyLevel.WARNING
        return self._level
