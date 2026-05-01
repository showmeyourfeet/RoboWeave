"""ErrorCodeSpec-based recovery advice (MVP)."""

from __future__ import annotations

from roboweave_interfaces.errors import ERROR_CODE_SPECS, ErrorCode


class RecoveryAdvisor:
    """ErrorCodeSpec-based recovery advisor.

    Looks up failure codes in the ERROR_CODE_SPECS registry and
    mechanically translates spec flags into recovery action strings.
    """

    def advise(self, failure_code: str) -> tuple[str, list[str]]:
        """Look up failure_code in ERROR_CODE_SPECS.

        Returns:
            A tuple of (analysis_string, recovery_actions_list).
        """
        # Try to match failure_code against ErrorCode enum values
        error_code = None
        for ec in ErrorCode:
            if ec.value == failure_code:
                error_code = ec
                break

        if error_code is None:
            return (f"Unrecognized error code: {failure_code}", [])

        spec = ERROR_CODE_SPECS.get(error_code)
        if spec is None:
            return (f"Unrecognized error code: {failure_code}", [])

        # Build recovery actions from spec flags
        recovery_actions: list[str] = []
        if spec.default_recovery_policy:
            recovery_actions.append(spec.default_recovery_policy)
        if spec.retryable:
            recovery_actions.append("retry")
        if spec.escalate_to_cloud:
            recovery_actions.append("escalate_to_cloud")
        if spec.escalate_to_user:
            recovery_actions.append("ask_user_clarification")

        # Build analysis string
        analysis = (
            f"Error {error_code.value} [{spec.severity.value}] "
            f"in module '{spec.module}': "
            f"recoverable={spec.recoverable}"
        )

        return (analysis, recovery_actions)
