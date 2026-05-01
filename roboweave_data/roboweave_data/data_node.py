"""DataNode - Main entry point for roboweave_data.

If ROS2 (rclpy) is available, runs as a ROS2 node.
Otherwise, provides the class structure for standalone use.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .converters import (
    execution_event_msg_to_model,
    safety_status_msg_to_dict,
    system_versions_to_json_envelope,
    task_status_msg_to_dict,
)
from .data_exporter import DataExporter
from .episode_recorder import EpisodeRecorder
from .failure_miner import FailureMiner
from .frame_logger import FrameLogger
from .label_generator import LabelGenerator
from .skill_logger import SkillLogger
from .version_tracker import VersionTracker

logger = logging.getLogger(__name__)

# Try importing ROS2
try:
    import rclpy
    from rclpy.node import Node

    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False
    Node = object  # type: ignore[assignment,misc]


class DataNode(Node):  # type: ignore[misc]
    """Main data collection node."""

    DEFAULT_STORAGE_PATH = "/data/roboweave/episodes"
    DEFAULT_FRAME_RATE_HZ = 10.0
    DEFAULT_AUTO_RECORD = True
    DEFAULT_MAX_EPISODES = 100
    DEFAULT_MASK_CONFIDENCE_THRESHOLD = 0.5
    DEFAULT_VLA_CONFIDENCE_THRESHOLD = 0.3

    def __init__(
        self,
        storage_path: str = DEFAULT_STORAGE_PATH,
        frame_rate_hz: float = DEFAULT_FRAME_RATE_HZ,
        auto_record: bool = DEFAULT_AUTO_RECORD,
        max_episodes: int = DEFAULT_MAX_EPISODES,
        mask_confidence_threshold: float = DEFAULT_MASK_CONFIDENCE_THRESHOLD,
        vla_confidence_threshold: float = DEFAULT_VLA_CONFIDENCE_THRESHOLD,
        data_params_path: str = "",
        **kwargs: Any,
    ) -> None:
        if HAS_ROS2:
            super().__init__("data_node", **kwargs)
            # Declare ROS2 parameters
            self.declare_parameter("storage_path", storage_path)
            self.declare_parameter("frame_rate_hz", frame_rate_hz)
            self.declare_parameter("auto_record", auto_record)
            self.declare_parameter("max_episodes", max_episodes)
            self.declare_parameter("mask_confidence_threshold", mask_confidence_threshold)
            self.declare_parameter("vla_confidence_threshold", vla_confidence_threshold)
            self.declare_parameter("data_params_path", data_params_path)
            # Read back from parameter server
            storage_path = self.get_parameter("storage_path").value
            frame_rate_hz = self.get_parameter("frame_rate_hz").value
            auto_record = self.get_parameter("auto_record").value
            max_episodes = self.get_parameter("max_episodes").value
            mask_confidence_threshold = self.get_parameter("mask_confidence_threshold").value
            vla_confidence_threshold = self.get_parameter("vla_confidence_threshold").value
            data_params_path = self.get_parameter("data_params_path").value

        # Load config from YAML if path provided
        if data_params_path:
            self._load_config(data_params_path, locals())

        self._storage_path = storage_path
        self._frame_rate_hz = frame_rate_hz
        self._auto_record = auto_record
        self._max_episodes = max_episodes

        # Instantiate components
        self._recorder = EpisodeRecorder(storage_path)
        self._skill_logger = SkillLogger()
        self._frame_logger: FrameLogger | None = None
        self._label_generator = LabelGenerator()
        self._failure_miner = FailureMiner(
            mask_confidence_threshold=mask_confidence_threshold,
            vla_confidence_threshold=vla_confidence_threshold,
        )
        self._data_exporter = DataExporter(storage_path)
        self._version_tracker = VersionTracker(node=self if HAS_ROS2 else None)

        # Latest sensor data
        self._latest_robot_state: dict | None = None
        self._latest_world_state: dict | None = None
        self._latest_safety_status: dict | None = None
        self._object_categories: list[str] = []
        self._execution_events: list[Any] = []

        # Set up ROS2 subscriptions and services
        if HAS_ROS2:
            self._setup_ros2()

        logger.info("DataNode initialized.")

    def _load_config(self, config_path: str, params: dict) -> None:
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        # Override defaults with YAML values (ROS2 params take precedence)

    def _setup_ros2(self) -> None:
        """Create ROS2 subscribers and service servers."""
        from roboweave_msgs.msg import (
            ExecutionEvent as ExecutionEventMsg,
            RobotStateMsg as RobotStateMsgType,
            SafetyStatus as SafetyStatusMsg,
            TaskStatus as TaskStatusMsg,
            WorldStateUpdate as WorldStateUpdateMsg,
        )
        from roboweave_msgs.srv import EpisodeControl, GetSystemVersions

        # Subscribers
        self.create_subscription(
            TaskStatusMsg, "/roboweave/task_status", self._on_task_status, 10
        )
        self.create_subscription(
            ExecutionEventMsg, "/roboweave/execution_events", self._on_execution_event, 10
        )
        self.create_subscription(
            WorldStateUpdateMsg, "/roboweave/world_state_update", self._on_world_state_update, 10
        )
        self.create_subscription(
            RobotStateMsgType, "/roboweave/robot_state", self._on_robot_state, 10
        )
        self.create_subscription(
            SafetyStatusMsg, "/roboweave/safety_status", self._on_safety_status, 10
        )

        # Service servers
        self.create_service(
            EpisodeControl, "/roboweave/data/episode_control", self._handle_episode_control
        )
        self.create_service(
            GetSystemVersions, "/roboweave/data/get_system_versions", self._handle_get_system_versions
        )

    # --- Topic callbacks ---

    def _on_task_status(self, msg: Any) -> None:
        """Auto-start/stop episodes based on task status if auto_record enabled."""
        try:
            status_dict = task_status_msg_to_dict(msg)
            status = status_dict.get("status", "")
            task_id = status_dict.get("task_id", "")

            if not self._auto_record:
                return

            if status == "running" and self._recorder.active_episode is None:
                versions = self._version_tracker.capture_snapshot()
                self._recorder.start(task_id, system_versions=versions)
                ep = self._recorder.active_episode
                if ep:
                    ep_dir = Path(self._storage_path) / ep.episode_id
                    self._frame_logger = FrameLogger(self._frame_rate_hz, ep_dir)
            elif status in ("succeeded", "failed") and self._recorder.active_episode is not None:
                outcome = "success" if status == "succeeded" else "failure"
                episode = self._recorder.stop(outcome)
                labels = self._label_generator.generate(
                    episode, self._execution_events, self._object_categories
                )
                self._recorder._active_episode = episode
                self._recorder.merge_labels(labels)
                self._recorder._active_episode = None
                tags = self._failure_miner.scan(episode, execution_events=self._execution_events)
                self._execution_events.clear()
                self._object_categories.clear()
                self._enforce_max_episodes()
        except Exception as e:
            logger.error(f"Error in _on_task_status: {e}")

    def _on_execution_event(self, msg: Any) -> None:
        """Forward to SkillLogger. Buffer if paused."""
        try:
            event = execution_event_msg_to_model(msg)
            self._execution_events.append(event)

            if self._recorder.status == "paused":
                self._skill_logger.buffer_event(event)
                return

            result = self._skill_logger.process_event(event)
            if result is not None:
                self._recorder.add_skill_log(result)
        except Exception as e:
            logger.error(f"Error in _on_execution_event: {e}")

    def _on_world_state_update(self, msg: Any) -> None:
        """Store latest world state, extract object categories."""
        try:
            if isinstance(msg, dict):
                self._latest_world_state = msg
            else:
                self._latest_world_state = {"raw": str(msg)}
            # Extract object categories if available
            if hasattr(msg, "objects"):
                for obj in msg.objects:
                    cat = getattr(obj, "category", "")
                    if cat and cat not in self._object_categories:
                        self._object_categories.append(cat)
        except Exception as e:
            logger.error(f"Error in _on_world_state_update: {e}")

    def _on_robot_state(self, msg: Any) -> None:
        """Store latest robot state, trigger FrameLogger."""
        try:
            if isinstance(msg, dict):
                self._latest_robot_state = msg
            else:
                self._latest_robot_state = {"raw": str(msg)}

            # Trigger frame capture if recording
            if (
                self._recorder.status == "recording"
                and self._frame_logger is not None
                and self._recorder.active_episode is not None
            ):
                import time

                ep = self._recorder.active_episode
                self._frame_logger.maybe_capture(
                    episode_id=ep.episode_id,
                    timestamp=time.time(),
                    robot_state_json=str(self._latest_robot_state),
                    world_state_json=str(self._latest_world_state) if self._latest_world_state else None,
                )
        except Exception as e:
            logger.error(f"Error in _on_robot_state: {e}")

    def _on_safety_status(self, msg: Any) -> None:
        """Store latest safety status."""
        try:
            self._latest_safety_status = safety_status_msg_to_dict(msg)
        except Exception as e:
            logger.error(f"Error in _on_safety_status: {e}")

    # --- Service handlers ---

    def _handle_episode_control(self, request: Any, response: Any) -> Any:
        """Dispatch to EpisodeRecorder based on action string."""
        try:
            action = request.action if hasattr(request, "action") else ""

            if action == "start":
                versions = self._version_tracker.capture_snapshot()
                task_id = getattr(request, "task_id", "")
                instruction = getattr(request, "task_instruction", "")
                ep_id = self._recorder.start(task_id, instruction, versions)
                ep_dir = Path(self._storage_path) / ep_id
                self._frame_logger = FrameLogger(self._frame_rate_hz, ep_dir)
                response.success = True
                response.episode_id = ep_id
                response.message = f"Episode started: {ep_id}"

            elif action == "stop":
                outcome = getattr(request, "outcome", "success")
                episode = self._recorder.stop(outcome)
                labels = self._label_generator.generate(
                    episode, self._execution_events, self._object_categories
                )
                # Re-attach episode for label merge
                self._recorder._active_episode = episode
                self._recorder.merge_labels(labels)
                tags = self._failure_miner.scan(
                    episode, execution_events=self._execution_events
                )
                # Persist tags
                if tags:
                    episode.labels.tags = tags
                    self._recorder._write_episode_json()
                self._recorder._active_episode = None
                self._execution_events.clear()
                self._object_categories.clear()
                self._enforce_max_episodes()
                response.success = True
                response.message = f"Episode stopped: {episode.episode_id}"

            elif action == "pause":
                self._recorder.pause()
                response.success = True
                response.message = "Episode paused"

            elif action == "resume":
                self._recorder.resume()
                # Flush buffered events
                buffered = self._skill_logger.flush_buffer()
                for event in buffered:
                    result = self._skill_logger.process_event(event)
                    if result is not None:
                        self._recorder.add_skill_log(result)
                if self._frame_logger:
                    self._frame_logger.reset()
                response.success = True
                response.message = "Episode resumed"

            elif action == "label":
                labels_json = getattr(request, "labels_json", "")
                if labels_json:
                    from roboweave_interfaces.episode import EpisodeLabels
                    labels = EpisodeLabels.model_validate_json(labels_json)
                    self._recorder.merge_labels(labels)
                response.success = True
                response.message = "Labels merged"

            else:
                response.success = False
                response.message = f"unrecognized action: {action}"

        except Exception as e:
            response.success = False
            response.message = str(e)

        return response

    def _handle_get_system_versions(self, request: Any, response: Any) -> Any:
        """Return SystemVersions via VersionTracker."""
        try:
            snapshot = self._version_tracker.capture_snapshot()
            response.versions_json = system_versions_to_json_envelope(snapshot)
            response.success = True
        except Exception as e:
            response.success = False
            response.message = str(e)
        return response

    # --- Storage management ---

    def _enforce_max_episodes(self) -> None:
        """Delete oldest completed episodes if count exceeds max_episodes."""
        if self._max_episodes == 0:
            return

        episodes = self._recorder.list_episodes()
        if len(episodes) <= self._max_episodes:
            return

        # Load episodes and sort by start_time, delete oldest completed
        completed = []
        for ep_dir in episodes:
            try:
                ep = self._recorder.load_episode(ep_dir)
                if ep.status in (
                    "completed_success",
                    "completed_failure",
                ):
                    completed.append((ep.start_time, ep_dir))
            except Exception:
                continue

        completed.sort(key=lambda x: x[0])
        to_delete = len(episodes) - self._max_episodes
        for i in range(min(to_delete, len(completed))):
            self._recorder.delete_episode(completed[i][1])

    def _shutdown(self) -> None:
        """Stop active episode, flush data."""
        if self._recorder.active_episode is not None:
            try:
                self._recorder.stop("failure")
            except Exception as e:
                logger.error(f"Error stopping episode on shutdown: {e}")


def main() -> None:
    """Entry point for the data node."""
    if HAS_ROS2:
        rclpy.init()
        node = DataNode()
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            node._shutdown()
            node.destroy_node()
            rclpy.shutdown()
    else:
        logger.warning("ROS2 not available. DataNode requires rclpy to run.")


if __name__ == "__main__":
    main()
