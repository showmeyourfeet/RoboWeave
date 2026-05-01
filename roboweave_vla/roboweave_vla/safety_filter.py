"""SafetyFilterClient: Calls the FilterVLAAction ROS2 service.

This is the only component that imports rclpy (lazily, at construction).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from roboweave_interfaces.base import JsonEnvelope
from roboweave_interfaces.vla import VLAAction, VLASafetyConstraints

from .converters import msg_to_vla_action

# Lazy ROS2 import
try:
    import rclpy  # noqa: F401
    from rclpy.node import Node

    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False


@dataclass
class FilterResult:
    """Safety filter response."""

    approved: bool
    filtered_action: VLAAction | None = None
    rejection_reason: str = ""
    violation_type: str = ""


class SafetyFilterClient:
    """Calls the FilterVLAAction ROS2 service.

    This is the only component that imports rclpy (lazily, at construction).
    """

    def __init__(
        self,
        node: Any,
        service_name: str = "/roboweave/safety/filter_vla_action",
    ) -> None:
        self._node = node
        self._service_name = service_name
        self._client: Any = None

        if HAS_ROS2 and node is not None:
            try:
                from roboweave_msgs.srv import FilterVLAAction  # type: ignore[import]

                self._client = node.create_client(FilterVLAAction, service_name)
            except Exception:
                self._client = None

    async def filter(
        self,
        action: VLAAction,
        constraints: VLASafetyConstraints,
        arm_id: str,
    ) -> FilterResult:
        """Filter a VLA action through the safety service.

        Returns FilterResult with approved=False and rejection_reason
        'safety_service_unavailable' if the service cannot be reached.
        """
        if not HAS_ROS2 or self._client is None:
            return FilterResult(
                approved=False,
                rejection_reason="safety_service_unavailable",
            )

        try:
            # Wait for service availability
            if not self._client.wait_for_service(timeout_sec=2.0):
                return FilterResult(
                    approved=False,
                    rejection_reason="safety_service_unavailable",
                )

            from roboweave_msgs.srv import FilterVLAAction  # type: ignore[import]

            request = FilterVLAAction.Request()
            request.action_json = JsonEnvelope.wrap(action).payload_json
            request.constraints_json = JsonEnvelope.wrap(constraints).payload_json
            request.arm_id = arm_id

            future = self._client.call_async(request)
            # In a real ROS2 context, we'd await the future
            response = await self._await_future(future)

            if response is None:
                return FilterResult(
                    approved=False,
                    rejection_reason="safety_service_unavailable",
                )

            if response.approved:
                filtered = VLAAction.model_validate_json(response.filtered_action_json)
                return FilterResult(approved=True, filtered_action=filtered)
            else:
                return FilterResult(
                    approved=False,
                    rejection_reason=getattr(response, "rejection_reason", "unknown"),
                    violation_type=getattr(response, "violation_type", ""),
                )

        except Exception:
            return FilterResult(
                approved=False,
                rejection_reason="safety_service_unavailable",
            )

    async def _await_future(self, future: Any) -> Any:
        """Await a ROS2 service future."""
        import asyncio

        while not future.done():
            await asyncio.sleep(0.01)
        return future.result()
