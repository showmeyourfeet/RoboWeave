"""SkillLogger - Converts execution events into SkillLog entries."""

from __future__ import annotations

from roboweave_interfaces.episode import SkillLog
from roboweave_interfaces.event import EventType, ExecutionEvent


class SkillLogger:
    """Converts execution events into SkillLog entries."""

    def __init__(self) -> None:
        self._pending_skills: dict[str, SkillLog] = {}
        self._buffer: list[ExecutionEvent] = []

    def process_event(self, event: ExecutionEvent) -> SkillLog | None:
        """Process an event. Returns a completed SkillLog when a skill ends,
        or None if the event starts/updates a skill in progress."""
        skill_call_id = event.context.get("skill_call_id", "")

        if event.event_type == EventType.SKILL_STARTED:
            skill_name = event.context.get("skill_name", "")
            log = SkillLog(
                skill_call_id=skill_call_id,
                skill_name=skill_name,
                status="running",
                start_time=event.timestamp,
            )
            self._pending_skills[skill_call_id] = log
            return None

        if event.event_type in (
            EventType.SKILL_SUCCEEDED,
            EventType.SKILL_FAILED,
            EventType.SKILL_TIMEOUT,
        ):
            log = self._pending_skills.pop(skill_call_id, None)
            if log is None:
                return None

            log.end_time = event.timestamp
            runtime_ms = int((event.timestamp - log.start_time) * 1000)
            log.runtime_ms = runtime_ms

            if event.event_type == EventType.SKILL_SUCCEEDED:
                log.status = "succeeded"
            elif event.event_type == EventType.SKILL_FAILED:
                log.status = "failed"
                log.failure_code = event.failure_code
            elif event.event_type == EventType.SKILL_TIMEOUT:
                log.status = "timeout"
                log.failure_code = event.failure_code

            return log

        return None

    def buffer_event(self, event: ExecutionEvent) -> None:
        """Buffer an event for later processing (used during pause)."""
        self._buffer.append(event)

    def flush_buffer(self) -> list[ExecutionEvent]:
        """Return and clear any buffered events."""
        events = list(self._buffer)
        self._buffer.clear()
        return events

    @property
    def pending_skills(self) -> dict[str, SkillLog]:
        """Skills currently in progress, keyed by skill_call_id."""
        return self._pending_skills
