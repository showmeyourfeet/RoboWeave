"""HITLManager — Phase 1 stub (no real HITL routing)."""

from __future__ import annotations

from roboweave_interfaces.hitl import HITLRequest, HITLResponse


class HITLManager:
    """Phase 1 stub. Exposes HITL request/response interface without real routing."""

    async def request_intervention(
        self, request: HITLRequest
    ) -> HITLResponse | None:
        """Stub: returns None (timeout behavior)."""
        return None

    @property
    def has_operator(self) -> bool:
        return False
