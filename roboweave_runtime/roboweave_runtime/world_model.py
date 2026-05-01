"""WorldModel — centralized world state management for RoboWeave runtime."""

from __future__ import annotations

import json
import time
from typing import Any, Callable

from roboweave_interfaces.world_state import ObjectLifecycle, ObjectState, RobotState, WorldState


class WorldModel:
    """Pure Python class managing the centralized WorldState."""

    def __init__(
        self,
        publish_hz: float = 1.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.publish_hz = publish_hz
        self._clock = clock
        self._state = WorldState(
            timestamp=0.0,
            robot=RobotState(robot_id=""),
        )
        # Callbacks
        self.on_state_changed: Callable[[WorldState], None] | None = None
        self.on_update_published: Callable[[str, str, str], None] | None = None

    # --- State mutation ---

    def handle_update(
        self, update_type: str, object_id: str, payload_json: str
    ) -> tuple[bool, str]:
        """Process an UpdateWorldState request. Returns (success, message)."""
        try:
            payload = json.loads(payload_json) if payload_json else {}
        except (json.JSONDecodeError, TypeError) as e:
            return False, f"Deserialization error: {e}"

        if update_type == "object_added":
            return self._handle_object_added(object_id, payload)
        elif update_type == "object_updated":
            return self._handle_object_updated(object_id, payload)
        elif update_type == "object_removed":
            return self._handle_object_removed(object_id)
        elif update_type == "full_refresh":
            return self._handle_full_refresh(payload)
        else:
            return False, f"Unknown update_type: {update_type}"

    def update_robot_state(self, robot_state: RobotState) -> None:
        """Update robot state from /roboweave/robot_state subscription."""
        self._state.robot = robot_state
        self._state.timestamp = self._clock()
        self._notify_state_changed()

    # --- State queries ---

    def query_full(self) -> WorldState:
        """Return the complete WorldState snapshot."""
        return self._state

    def query_object(self, object_id: str) -> ObjectState | None:
        """Return a single ObjectState or None if not found."""
        for obj in self._state.objects:
            if obj.object_id == object_id:
                return obj
        return None

    def query_robot(self) -> RobotState:
        """Return the current RobotState."""
        return self._state.robot

    def get_world_state(self) -> WorldState:
        """Alias for query_full(), used by SkillOrchestrator."""
        return self.query_full()

    # --- Lifecycle management ---

    def tick_ttl(self) -> list[str]:
        """Check all objects for TTL expiry. Returns list of object_ids transitioned to LOST."""
        now = self._clock()
        transitioned: list[str] = []
        for obj in self._state.objects:
            if obj.lifecycle_state == ObjectLifecycle.HELD:
                continue
            if obj.lifecycle_state == ObjectLifecycle.ACTIVE:
                if now - obj.last_seen > obj.ttl_sec:
                    obj.lifecycle_state = ObjectLifecycle.LOST
                    transitioned.append(obj.object_id)
        if transitioned:
            self._notify_state_changed()
        return transitioned

    # --- Internal handlers ---

    def _handle_object_added(
        self, object_id: str, payload: dict[str, Any]
    ) -> tuple[bool, str]:
        payload.setdefault("object_id", object_id)
        try:
            obj = ObjectState(**payload)
        except Exception as e:
            return False, f"Deserialization error: {e}"
        obj.lifecycle_state = ObjectLifecycle.ACTIVE
        obj.last_seen = self._clock()
        self._state.objects.append(obj)
        self._state.timestamp = self._clock()
        self._notify_state_changed()
        self._notify_update_published("object_added", object_id, "")
        return True, "Object added"

    def _handle_object_updated(
        self, object_id: str, payload: dict[str, Any]
    ) -> tuple[bool, str]:
        obj = self.query_object(object_id)
        if obj is None:
            return False, f"Object not found: {object_id}"
        # Merge payload fields into existing object
        for key, value in payload.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        # Reactivate if OCCLUDED or LOST
        if obj.lifecycle_state in (ObjectLifecycle.OCCLUDED, ObjectLifecycle.LOST):
            obj.lifecycle_state = ObjectLifecycle.ACTIVE
        obj.last_seen = self._clock()
        self._state.timestamp = self._clock()
        self._notify_state_changed()
        self._notify_update_published("object_updated", object_id, "")
        return True, "Object updated"

    def _handle_object_removed(self, object_id: str) -> tuple[bool, str]:
        obj = self.query_object(object_id)
        if obj is None:
            return False, f"Object not found: {object_id}"
        obj.lifecycle_state = ObjectLifecycle.REMOVED
        self._state.timestamp = self._clock()
        self._notify_state_changed()
        self._notify_update_published("object_removed", object_id, "")
        return True, "Object removed"

    def _handle_full_refresh(self, payload: dict[str, Any]) -> tuple[bool, str]:
        try:
            new_state = WorldState(**payload)
        except Exception as e:
            return False, f"Deserialization error: {e}"
        self._state = new_state
        self._state.timestamp = self._clock()
        self._notify_state_changed()
        self._notify_update_published("full_refresh", "", "")
        return True, "Full refresh applied"

    # --- Notification helpers ---

    def _notify_state_changed(self) -> None:
        if self.on_state_changed:
            self.on_state_changed(self._state)

    def _notify_update_published(
        self, update_type: str, object_id: str, payload: str
    ) -> None:
        if self.on_update_published:
            self.on_update_published(update_type, object_id, payload)
