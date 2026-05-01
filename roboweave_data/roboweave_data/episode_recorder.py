"""EpisodeRecorder - Manages episode lifecycle and disk persistence."""

from __future__ import annotations

import json
import os
import secrets
import shutil
import time
from pathlib import Path
from typing import Any

from roboweave_interfaces.episode import (
    EpisodeLabels,
    EpisodeLog,
    EpisodeStatus,
    FrameLog,
    SkillLog,
    SystemVersions,
)


class EpisodeRecorder:
    """Manages episode lifecycle: start, stop, pause, resume, label."""

    def __init__(self, storage_path: str) -> None:
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._active_episode: EpisodeLog | None = None

    def start(
        self,
        task_id: str,
        task_instruction: str = "",
        system_versions: SystemVersions | None = None,
    ) -> str:
        """Create a new episode. Returns episode_id. Raises if already recording."""
        if self._active_episode is not None:
            raise RuntimeError("episode already active")

        timestamp_ms = int(time.time() * 1000)
        random_hex = secrets.token_hex(4)
        episode_id = f"ep_{timestamp_ms}_{random_hex}"

        episode_dir = self._storage_path / episode_id
        episode_dir.mkdir(parents=True, exist_ok=True)
        (episode_dir / "frames").mkdir(exist_ok=True)

        self._active_episode = EpisodeLog(
            episode_id=episode_id,
            task_id=task_id,
            status=EpisodeStatus.RECORDING,
            start_time=time.time(),
            task_instruction=task_instruction,
            system_versions=system_versions,
        )
        return episode_id

    def stop(self, outcome: str = "success") -> EpisodeLog:
        """Stop the active episode. outcome: 'success' | 'failure'.
        Computes duration_sec, writes episode.json. Raises if no active episode."""
        if self._active_episode is None:
            raise RuntimeError("no active episode")

        end_time = time.time()
        if outcome == "success":
            status = EpisodeStatus.COMPLETED_SUCCESS
        else:
            status = EpisodeStatus.COMPLETED_FAILURE

        self._active_episode.status = status
        self._active_episode.end_time = end_time
        self._active_episode.duration_sec = end_time - self._active_episode.start_time

        self._write_episode_json()
        episode = self._active_episode
        self._active_episode = None
        return episode

    def pause(self) -> None:
        """Pause recording. Raises if not recording."""
        if self._active_episode is None:
            raise RuntimeError("no active episode")
        if self._active_episode.status != EpisodeStatus.RECORDING:
            raise RuntimeError("episode not recording")
        self._active_episode.status = EpisodeStatus.PAUSED

    def resume(self) -> None:
        """Resume recording. Raises if not paused."""
        if self._active_episode is None:
            raise RuntimeError("no active episode")
        if self._active_episode.status != EpisodeStatus.PAUSED:
            raise RuntimeError("episode not paused")
        self._active_episode.status = EpisodeStatus.RECORDING

    def merge_labels(self, labels: EpisodeLabels) -> None:
        """Merge provided labels into the active/completed episode."""
        if self._active_episode is None:
            raise RuntimeError("no active episode")
        # Merge non-default values from provided labels
        current = self._active_episode.labels
        for field_name in labels.model_fields:
            value = getattr(labels, field_name)
            default = labels.model_fields[field_name].default
            # For list fields, check if non-empty
            if isinstance(value, list) and len(value) > 0:
                setattr(current, field_name, value)
            elif isinstance(value, bool) and value:
                setattr(current, field_name, value)
            elif isinstance(value, str) and value != "" and value != (default or ""):
                setattr(current, field_name, value)
        self._write_episode_json()

    def add_skill_log(self, skill_log: SkillLog) -> None:
        """Append a SkillLog to the active episode."""
        if self._active_episode is not None:
            self._active_episode.skill_logs.append(skill_log)

    def add_frame_log(self, frame_log: FrameLog) -> None:
        """Append a FrameLog to the active episode."""
        if self._active_episode is not None:
            pass  # Frame logs are stored on disk, not in EpisodeLog

    @property
    def active_episode(self) -> EpisodeLog | None:
        return self._active_episode

    @property
    def status(self) -> EpisodeStatus | None:
        if self._active_episode is None:
            return None
        return self._active_episode.status

    def load_episode(self, episode_dir: Path) -> EpisodeLog:
        """Deserialize an EpisodeLog from episode.json on disk."""
        ep_json = episode_dir / "episode.json"
        return EpisodeLog.model_validate_json(ep_json.read_text())

    def list_episodes(self) -> list[Path]:
        """List all episode directories under storage_path, sorted by name."""
        if not self._storage_path.exists():
            return []
        dirs = [
            d for d in self._storage_path.iterdir()
            if d.is_dir() and d.name.startswith("ep_")
        ]
        return sorted(dirs)

    def delete_episode(self, episode_dir: Path) -> None:
        """Remove an entire episode directory from disk."""
        if episode_dir.exists():
            shutil.rmtree(episode_dir)

    def _write_episode_json(self) -> None:
        """Write the active episode to disk as episode.json."""
        if self._active_episode is None:
            return
        episode_dir = self._storage_path / self._active_episode.episode_id
        episode_dir.mkdir(parents=True, exist_ok=True)
        ep_json = episode_dir / "episode.json"
        ep_json.write_text(self._active_episode.model_dump_json(indent=2))
