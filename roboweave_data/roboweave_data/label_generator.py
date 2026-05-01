"""LabelGenerator - Auto-generates EpisodeLabels from episode data."""

from __future__ import annotations

from roboweave_interfaces.episode import EpisodeLabels, EpisodeLog, EpisodeStatus
from roboweave_interfaces.event import EventType, ExecutionEvent


class LabelGenerator:
    """Auto-generates EpisodeLabels from episode data."""

    FAILURE_STAGE_MAP: dict[str, str] = {
        "PER_": "perception",
        "GRP_": "planning",
        "IK_": "planning",
        "MOT_": "planning",
        "CTL_": "control",
        "VLA_": "vla",
        "SAF_": "safety",
    }

    def generate(
        self,
        episode_log: EpisodeLog,
        execution_events: list[ExecutionEvent] | None = None,
        object_categories: list[str] | None = None,
    ) -> EpisodeLabels:
        """Generate labels from a completed episode."""
        events = execution_events or []

        success = episode_log.status == EpisodeStatus.COMPLETED_SUCCESS

        # Determine failure code
        failure_code = episode_log.failure_code
        if not failure_code:
            for sl in episode_log.skill_logs:
                if sl.status == "failed" and sl.failure_code:
                    failure_code = sl.failure_code
                    break

        # Map failure code prefix to failure stage
        failure_stage = ""
        if failure_code:
            for prefix, stage in self.FAILURE_STAGE_MAP.items():
                if failure_code.startswith(prefix):
                    failure_stage = stage
                    break

        # Check for recovery usage
        recovery_used = any(
            e.event_type == EventType.RECOVERY_STARTED for e in events
        )

        # Check for human intervention
        human_intervention = False
        for e in events:
            if e.event_type == EventType.SAFETY_TRIGGERED:
                for candidate in e.recovery_candidates:
                    if "teleop" in candidate.lower() or "manual" in candidate.lower():
                        human_intervention = True
                        break
            if human_intervention:
                break

        # Extract task type from instruction
        task_type = self._extract_task_type(episode_log.task_instruction)

        # Object categories
        categories = object_categories or []

        return EpisodeLabels(
            task_type=task_type,
            object_categories=categories,
            success=success,
            failure_stage=failure_stage,
            failure_code=failure_code,
            recovery_used=recovery_used,
            human_intervention=human_intervention,
        )

    def _extract_task_type(self, instruction: str) -> str:
        """Extract task type from task instruction."""
        if not instruction:
            return ""
        # Use the full instruction if short, otherwise first verb-noun phrase
        words = instruction.strip().split()
        if len(words) <= 4:
            return instruction.strip()
        # Take first 3-4 words as task type
        return " ".join(words[:3])
