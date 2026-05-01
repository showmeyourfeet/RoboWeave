"""DataExporter - Exports episodes with manifest and rewritten URIs."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from roboweave_interfaces.episode import EpisodeLog, EpisodeStatus

from .episode_recorder import EpisodeRecorder

logger = logging.getLogger(__name__)


class DataExporter:
    """Exports episodes with manifest and rewritten URIs."""

    def __init__(self, storage_path: str) -> None:
        self._storage_path = Path(storage_path)
        self._recorder = EpisodeRecorder(storage_path)

    def export(
        self,
        episode_ids: list[str],
        output_dir: str,
        filter_tags: list[str] | None = None,
        filter_success: bool | None = None,
        filter_date_range: tuple[float, float] | None = None,
    ) -> dict:
        """Export episodes to output_dir. Returns manifest dict.
        Skips missing episodes with a warning."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        exported_episodes: list[EpisodeLog] = []

        for ep_id in episode_ids:
            ep_dir = self._storage_path / ep_id
            if not ep_dir.exists():
                logger.warning(f"Episode directory not found: {ep_id}, skipping")
                continue

            try:
                episode = self._recorder.load_episode(ep_dir)
            except Exception as e:
                logger.warning(f"Failed to load episode {ep_id}: {e}, skipping")
                continue

            # Apply filters
            if not self._passes_filters(
                episode, filter_tags, filter_success, filter_date_range
            ):
                continue

            # Copy episode data to output directory
            dest_dir = out_path / ep_id
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(ep_dir, dest_dir)

            # Rewrite URIs
            episode = self._rewrite_uris(episode, ep_id)

            # Write rewritten episode.json
            (dest_dir / "episode.json").write_text(
                episode.model_dump_json(indent=2)
            )

            exported_episodes.append(episode)

        manifest = self._build_manifest(exported_episodes)
        manifest_path = out_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        return manifest

    def _passes_filters(
        self,
        episode: EpisodeLog,
        filter_tags: list[str] | None,
        filter_success: bool | None,
        filter_date_range: tuple[float, float] | None,
    ) -> bool:
        """Check if episode passes all filter criteria."""
        if filter_success is not None:
            is_success = episode.status == EpisodeStatus.COMPLETED_SUCCESS
            if is_success != filter_success:
                return False

        if filter_tags is not None:
            ep_tags = episode.labels.tags
            if not all(tag in ep_tags for tag in filter_tags):
                return False

        if filter_date_range is not None:
            start_range, end_range = filter_date_range
            if episode.start_time < start_range or episode.start_time > end_range:
                return False

        return True

    def _rewrite_uris(self, episode_log: EpisodeLog, relative_base: str) -> EpisodeLog:
        """Rewrite all file:// URIs to be relative to the export directory."""
        data = episode_log.model_dump()
        self._rewrite_uris_in_dict(data, relative_base)
        return EpisodeLog.model_validate(data)

    def _rewrite_uris_in_dict(self, obj: Any, relative_base: str) -> None:
        """Recursively rewrite file:// URIs in a dict/list structure."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "uri" and isinstance(value, str) and value.startswith("file://"):
                    # Rewrite to be relative to export dir
                    path_part = value[len("file://"):]
                    obj[key] = f"file://{relative_base}/{path_part}"
                else:
                    self._rewrite_uris_in_dict(value, relative_base)
        elif isinstance(obj, list):
            for item in obj:
                self._rewrite_uris_in_dict(item, relative_base)

    def _build_manifest(self, episodes: list[EpisodeLog]) -> dict:
        """Build manifest.json content."""
        episode_entries = []
        for ep in episodes:
            entry = {
                "episode_id": ep.episode_id,
                "task_type": ep.labels.task_type,
                "success": ep.status == EpisodeStatus.COMPLETED_SUCCESS,
                "tags": ep.labels.tags,
                "frame_count": len(ep.skill_logs),  # approximate
                "duration_sec": ep.duration_sec,
                "system_versions": (
                    ep.system_versions.model_dump() if ep.system_versions else {}
                ),
            }
            episode_entries.append(entry)

        return {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "episode_count": len(episodes),
            "episodes": episode_entries,
        }
