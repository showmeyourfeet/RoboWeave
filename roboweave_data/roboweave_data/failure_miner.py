"""FailureMiner - Scans episodes for failure patterns and adds tags."""

from __future__ import annotations

from roboweave_interfaces.episode import EpisodeLog, FrameLog, SkillLog
from roboweave_interfaces.event import EventType, ExecutionEvent


class FailureMiner:
    """Scans episodes for failure patterns and adds tags."""

    def __init__(
        self,
        mask_confidence_threshold: float = 0.5,
        vla_confidence_threshold: float = 0.3,
    ) -> None:
        self._mask_confidence_threshold = mask_confidence_threshold
        self._vla_confidence_threshold = vla_confidence_threshold

    def scan(
        self,
        episode_log: EpisodeLog,
        frame_logs: list[FrameLog] | None = None,
        execution_events: list[ExecutionEvent] | None = None,
    ) -> list[str]:
        """Return a list of failure tags to add to the episode."""
        tags: list[str] = []
        frames = frame_logs or []
        events = execution_events or []
        skill_logs = episode_log.skill_logs

        # grasp_failure: any skill failure_code matches CTL_GRASP_SLIP or prefix GRP_
        if any(
            sl.failure_code == "CTL_GRASP_SLIP" or sl.failure_code.startswith("GRP_")
            for sl in skill_logs
            if sl.failure_code
        ):
            tags.append("grasp_failure")

        # low_confidence_mask: any frame's mask_ref.mask_confidence < threshold
        if any(
            f.mask_ref is not None
            and f.mask_ref.mask_confidence < self._mask_confidence_threshold
            for f in frames
        ):
            tags.append("low_confidence_mask")

        # vla_low_confidence: any skill failure_code matches VLA_CONFIDENCE_LOW
        if any(
            sl.failure_code == "VLA_CONFIDENCE_LOW"
            for sl in skill_logs
            if sl.failure_code
        ):
            tags.append("vla_low_confidence")

        # human_takeover: any safety_triggered event with recovery containing "teleop"
        if any(
            e.event_type == EventType.SAFETY_TRIGGERED
            and any("teleop" in c.lower() for c in e.recovery_candidates)
            for e in events
        ):
            tags.append("human_takeover")

        # safety_stop: any event failure_code matches SAF_EMERGENCY_STOP or SAF_FORCE_LIMIT
        if any(
            e.failure_code in ("SAF_EMERGENCY_STOP", "SAF_FORCE_LIMIT")
            for e in events
            if e.failure_code
        ):
            tags.append("safety_stop")

        # recovery_success: any event event_type == recovery_succeeded
        if any(e.event_type == EventType.RECOVERY_SUCCEEDED for e in events):
            tags.append("recovery_success")

        # all_grasps_unreachable: all grasp-related skills have IK_NO_SOLUTION
        grasp_skills = [
            sl for sl in skill_logs
            if "grasp" in sl.skill_name.lower() or sl.failure_code.startswith("GRP_")
        ]
        if grasp_skills and all(
            sl.failure_code == "IK_NO_SOLUTION" for sl in grasp_skills
        ):
            tags.append("all_grasps_unreachable")

        return tags
