# Requirements Document

## Introduction

The `roboweave_data` package is the data collection and pipeline layer of the RoboWeave hybrid robotics system. It passively subscribes to ROS2 topics to record episode data during task execution, automatically generates labels from episode metadata, mines failure samples for model retraining, and exports episodes in training-ready formats. A single `DataNode` hosts the ROS2 subscriptions and service servers, while the core logic (episode recording, skill logging, frame logging, label generation, failure mining, data export, version tracking) is implemented as pure-Python components testable without ROS2.

This is Phase 3.2 of the RoboWeave project, building on the already-implemented `roboweave_interfaces` (Pydantic models: `EpisodeLog`, `EpisodeStatus`, `EpisodeLabels`, `SkillLog`, `FrameLog`, `SystemVersions`, `DataRef`, `ImageRef`, `DepthRef`, `PointCloudRef`, `MaskRef`, `WorldStateRef`) and `roboweave_msgs` (ROS2 msg/srv definitions: `EpisodeControl.srv`, `GetSystemVersions.srv`, `TaskStatus.msg`, `ExecutionEvent.msg`, `WorldStateUpdate.msg`, `RobotStateMsg.msg`, `SafetyStatus.msg`).

Episode data is stored as JSON metadata plus binary files on disk, organized by episode ID. The package operates as a passive observer — it subscribes to topics but does not publish commands or alter system behavior.

## Glossary

- **Data_Node**: The main ROS2 node that subscribes to system topics, hosts the EpisodeControl and GetSystemVersions service servers, and coordinates the Episode_Recorder, Skill_Logger, Frame_Logger, Label_Generator, Failure_Miner, Data_Exporter, and Version_Tracker components.
- **Episode_Recorder**: A pure-Python component that manages episode lifecycle (start, stop, pause, resume), maintains episode state, and writes `EpisodeLog` JSON to disk upon episode completion.
- **Skill_Logger**: A pure-Python component that listens for skill-related execution events and produces `SkillLog` entries within the active episode.
- **Frame_Logger**: A pure-Python component that records frame-level sensor data (`FrameLog` entries) at a configurable rate during active recording.
- **Label_Generator**: A pure-Python component that auto-generates `EpisodeLabels` from a completed `EpisodeLog` by analyzing skill outcomes, failure codes, and recovery usage.
- **Failure_Miner**: A pure-Python component that scans completed episodes and tags those matching predefined failure patterns (grasp failure, low-confidence mask, VLA low confidence, human takeover, safety stop, etc.) for downstream model retraining.
- **Data_Exporter**: A pure-Python component that exports one or more episodes into a training-ready directory structure with a manifest file.
- **Version_Tracker**: A pure-Python component that captures a `SystemVersions` snapshot at episode start time by querying ROS2 parameters and package metadata.
- **EpisodeControl**: A ROS2 service (`EpisodeControl.srv`) that accepts actions: "start", "stop", "pause", "resume", "label" to control episode recording lifecycle.
- **GetSystemVersions**: A ROS2 service (`GetSystemVersions.srv`) that returns the current `SystemVersions` as a JsonEnvelope-wrapped JSON string.
- **Episode_Directory**: A directory on disk named by episode_id containing `episode.json` (the `EpisodeLog`), `frames/` (frame data files), and `exports/` (exported artifacts).
- **data_params.yaml**: A YAML configuration file defining runtime parameters for the Data_Node (storage path, frame logging rate, auto-record flag, failure mining thresholds).
- **JsonEnvelope**: The standard JSON transport wrapper defined in `roboweave_interfaces` containing `schema_name`, `schema_version`, `payload_json`, and `payload_hash`.

## Requirements

### Requirement 1: Episode Recorder Lifecycle

**User Story:** As a robotics developer, I want to start, stop, pause, and resume episode recording, so that I can capture complete task execution data for analysis and model training.

#### Acceptance Criteria

1. WHEN the Episode_Recorder receives a "start" action with a task_id, THE Episode_Recorder SHALL create a new `EpisodeLog` with a unique episode_id, set `status` to `RECORDING`, record the `start_time`, store the `task_id`, and create the Episode_Directory on disk.
2. WHEN the Episode_Recorder receives a "stop" action for an active episode, THE Episode_Recorder SHALL set the `EpisodeLog` `status` to `COMPLETED_SUCCESS` or `COMPLETED_FAILURE` based on the task outcome, compute `duration_sec` as `end_time - start_time`, and write the final `episode.json` to the Episode_Directory.
3. WHEN the Episode_Recorder receives a "pause" action for a recording episode, THE Episode_Recorder SHALL set the `EpisodeLog` `status` to `PAUSED` and stop accepting new `SkillLog` and `FrameLog` entries until resumed.
4. WHEN the Episode_Recorder receives a "resume" action for a paused episode, THE Episode_Recorder SHALL set the `EpisodeLog` `status` back to `RECORDING` and resume accepting `SkillLog` and `FrameLog` entries.
5. IF a "start" action is received while an episode is already recording, THEN THE Episode_Recorder SHALL return an error indicating that an episode is already active.
6. IF a "stop", "pause", or "resume" action is received with an episode_id that does not match the active episode, THEN THE Episode_Recorder SHALL return an error indicating that the episode_id is not recognized.
7. WHEN the Episode_Recorder receives a "label" action with `labels_json` for an active or completed episode, THE Episode_Recorder SHALL merge the provided `EpisodeLabels` into the episode's existing labels and persist the updated `episode.json`.

### Requirement 2: Skill Logger

**User Story:** As a data scientist, I want skill-level execution data recorded within each episode, so that I can analyze which skills succeed or fail and correlate skill performance with training data.

#### Acceptance Criteria

1. WHEN the Skill_Logger receives an execution event with `event_type` equal to `skill_started`, THE Skill_Logger SHALL create a new `SkillLog` entry with the `skill_call_id`, `skill_name`, `status` set to "running", and `start_time` from the event timestamp.
2. WHEN the Skill_Logger receives an execution event with `event_type` equal to `skill_succeeded` for a tracked skill, THE Skill_Logger SHALL update the corresponding `SkillLog` entry with `status` set to "succeeded", `end_time` from the event timestamp, and `runtime_ms` computed as `(end_time - start_time) * 1000`.
3. WHEN the Skill_Logger receives an execution event with `event_type` equal to `skill_failed` for a tracked skill, THE Skill_Logger SHALL update the corresponding `SkillLog` entry with `status` set to "failed", `end_time` from the event timestamp, `runtime_ms`, and `failure_code` from the event.
4. WHEN the Skill_Logger receives an execution event with `event_type` equal to `skill_timeout` for a tracked skill, THE Skill_Logger SHALL update the corresponding `SkillLog` entry with `status` set to "timeout", `end_time` from the event timestamp, and `failure_code` set to the event failure_code.
5. WHILE the Episode_Recorder status is `PAUSED`, THE Skill_Logger SHALL buffer incoming skill events and append them to the episode when recording resumes.
6. THE Skill_Logger SHALL append each completed `SkillLog` entry to the active `EpisodeLog.skill_logs` list.

### Requirement 3: Frame Logger

**User Story:** As a data scientist, I want frame-level sensor snapshots recorded at a configurable rate during episodes, so that I can use the data for VLA model training and behavior cloning.

#### Acceptance Criteria

1. WHILE the Episode_Recorder status is `RECORDING`, THE Frame_Logger SHALL capture a `FrameLog` entry at the rate specified by the `frame_rate_hz` parameter in data_params.yaml.
2. WHEN the Frame_Logger captures a frame, THE Frame_Logger SHALL populate the `FrameLog` with the current `timestamp`, the active `episode_id`, and `DataRef` references for available sensor data (rgb_ref, depth_ref, point_cloud_ref, mask_ref, robot_state_ref, world_state_ref).
3. WHILE the Episode_Recorder status is `PAUSED`, THE Frame_Logger SHALL stop capturing frames until recording resumes.
4. WHEN the Frame_Logger captures a frame, THE Frame_Logger SHALL write the frame data files to the `frames/` subdirectory of the Episode_Directory and store the corresponding file URIs in the `FrameLog` DataRef fields.
5. THE Frame_Logger SHALL use the `file://` URI scheme for locally stored frame data, with paths relative to the Episode_Directory.
6. IF a sensor data source is unavailable at capture time, THE Frame_Logger SHALL set the corresponding `DataRef` field to None in the `FrameLog` entry rather than failing the entire frame capture.

### Requirement 4: Label Generator

**User Story:** As a data scientist, I want episodes to be automatically labeled based on execution outcomes, so that I can filter and query training data without manual annotation.

#### Acceptance Criteria

1. WHEN an episode is stopped, THE Label_Generator SHALL auto-generate `EpisodeLabels` from the completed `EpisodeLog`.
2. THE Label_Generator SHALL set `EpisodeLabels.success` to `true` if the `EpisodeLog.status` is `COMPLETED_SUCCESS`, and `false` otherwise.
3. THE Label_Generator SHALL set `EpisodeLabels.failure_stage` by extracting the module prefix from the first `failure_code` in the episode (e.g., "PER_" maps to "perception", "GRP_" maps to "planning", "CTL_" maps to "control", "VLA_" maps to "vla", "SAF_" maps to "safety").
4. THE Label_Generator SHALL set `EpisodeLabels.failure_code` to the `failure_code` from the `EpisodeLog` if present.
5. THE Label_Generator SHALL set `EpisodeLabels.recovery_used` to `true` if any `SkillLog` entry in the episode has an event_type of `recovery_started` in the execution events.
6. THE Label_Generator SHALL set `EpisodeLabels.human_intervention` to `true` if any execution event in the episode has `event_type` equal to `safety_triggered` with a recovery candidate containing "teleop" or "manual".
7. THE Label_Generator SHALL extract `EpisodeLabels.task_type` from the `EpisodeLog.task_instruction` field.
8. THE Label_Generator SHALL extract `EpisodeLabels.object_categories` from the world state updates received during the episode.
9. FOR ALL completed episodes, THE Label_Generator SHALL produce an `EpisodeLabels` object where every field is populated (no empty strings for fields that can be derived from the episode data).

### Requirement 5: Failure Miner

**User Story:** As a machine learning engineer, I want failure episodes automatically identified and tagged by failure type, so that I can build targeted training datasets for model improvement.

#### Acceptance Criteria

1. WHEN an episode is completed, THE Failure_Miner SHALL scan the episode and apply failure tags based on predefined mining conditions.
2. WHEN an episode contains a `SkillLog` with `failure_code` matching `CTL_GRASP_SLIP` or any code with prefix `GRP_`, THE Failure_Miner SHALL add the tag `grasp_failure` to the episode labels.
3. WHEN an episode contains frame data where mask confidence is below the `mask_confidence_threshold` parameter (default 0.5), THE Failure_Miner SHALL add the tag `low_confidence_mask` to the episode labels.
4. WHEN an episode contains a `SkillLog` with `failure_code` matching `VLA_CONFIDENCE_LOW`, THE Failure_Miner SHALL add the tag `vla_low_confidence` to the episode labels.
5. WHEN an episode contains execution events indicating human takeover (event_type `safety_triggered` with recovery involving teleop), THE Failure_Miner SHALL add the tag `human_takeover` to the episode labels.
6. WHEN an episode contains execution events with `failure_code` matching `SAF_EMERGENCY_STOP` or `SAF_FORCE_LIMIT`, THE Failure_Miner SHALL add the tag `safety_stop` to the episode labels.
7. WHEN an episode contains a recovery that succeeded (execution event with `event_type` equal to `recovery_succeeded`), THE Failure_Miner SHALL add the tag `recovery_success` to the episode labels.
8. WHEN an episode contains a `SkillLog` where all grasp candidates were unreachable (failure_code `IK_NO_SOLUTION` across all grasp attempts), THE Failure_Miner SHALL add the tag `all_grasps_unreachable` to the episode labels.
9. THE Failure_Miner SHALL persist the updated tags to the episode's `episode.json` file.

### Requirement 6: Data Exporter

**User Story:** As a machine learning engineer, I want to export episodes in a training-ready format with a manifest, so that I can feed the data directly into model training pipelines.

#### Acceptance Criteria

1. WHEN the Data_Exporter is invoked with a list of episode_ids and an output directory, THE Data_Exporter SHALL copy the episode data (episode.json and frame files) into the output directory organized by episode_id.
2. THE Data_Exporter SHALL generate a `manifest.json` file in the output directory containing a list of exported episodes with their episode_id, task_type, success status, label tags, frame count, and duration_sec.
3. THE Data_Exporter SHALL support filtering episodes by label tags, success status, and date range before export.
4. WHEN the Data_Exporter exports an episode, THE Data_Exporter SHALL rewrite all `DataRef` URIs in the exported `episode.json` and `FrameLog` entries to use paths relative to the export output directory.
5. IF an episode_id provided to the Data_Exporter does not exist on disk, THEN THE Data_Exporter SHALL skip that episode, log a warning, and continue exporting the remaining episodes.
6. THE Data_Exporter SHALL include the `SystemVersions` snapshot in each exported episode's metadata, so that training pipelines can track which model versions produced the data.

### Requirement 7: Version Tracker

**User Story:** As a machine learning engineer, I want a snapshot of all system component versions captured at episode start, so that I can correlate training data with the exact software versions that produced it.

#### Acceptance Criteria

1. WHEN an episode is started, THE Version_Tracker SHALL capture a `SystemVersions` snapshot and attach it to the `EpisodeLog.system_versions` field.
2. THE Version_Tracker SHALL populate `SystemVersions.roboweave_version` from the `roboweave_interfaces._version` module.
3. THE Version_Tracker SHALL populate `SystemVersions.timestamp` with the current time at snapshot capture.
4. THE Version_Tracker SHALL populate available version fields (`perception_models`, `vla_models`, `planner_backend`, `planner_version`, `controller_version`) by querying ROS2 parameters from the respective nodes when available.
5. IF a version field cannot be determined (node not running or parameter not set), THE Version_Tracker SHALL set that field to an empty string rather than raising an error.
6. WHEN the GetSystemVersions service is called, THE Version_Tracker SHALL return the most recently captured `SystemVersions` snapshot wrapped in a JsonEnvelope.

### Requirement 8: Data Node Lifecycle and Topic Subscriptions

**User Story:** As a system integrator, I want a single ROS2 node that subscribes to all relevant system topics and hosts the data services, so that I can launch the data collection subsystem with a single command.

#### Acceptance Criteria

1. THE Data_Node SHALL subscribe to the following ROS2 topics: `/roboweave/task_status` (TaskStatus), `/roboweave/execution_events` (ExecutionEvent), `/roboweave/world_state_update` (WorldStateUpdate), `/roboweave/robot_state` (RobotStateMsg), `/roboweave/safety_status` (SafetyStatus).
2. THE Data_Node SHALL host the ROS2 service server `/roboweave/data/episode_control` (EpisodeControl).
3. THE Data_Node SHALL host the ROS2 service server `/roboweave/data/get_system_versions` (GetSystemVersions).
4. WHEN the Data_Node receives a TaskStatus message with status "running" and `auto_record` is enabled in data_params.yaml, THE Data_Node SHALL automatically start a new episode via the Episode_Recorder if no episode is currently active.
5. WHEN the Data_Node receives a TaskStatus message with status "succeeded" or "failed" and an episode is active, THE Data_Node SHALL automatically stop the episode via the Episode_Recorder.
6. WHEN the Data_Node receives an ExecutionEvent message, THE Data_Node SHALL forward the event to the Skill_Logger for processing.
7. WHEN the Data_Node receives a SafetyStatus message, THE Data_Node SHALL store the latest safety status for inclusion in frame data and label generation.
8. THE Data_Node SHALL load configuration from data_params.yaml at startup.
9. WHEN the Data_Node shuts down, THE Data_Node SHALL stop any active episode recording and flush all pending data to disk.

### Requirement 9: EpisodeControl Service Handler

**User Story:** As a task executor, I want a ROS2 service to control episode recording, so that the runtime can programmatically start and stop data collection during task execution.

#### Acceptance Criteria

1. WHEN an EpisodeControl request with action "start" is received, THE Data_Node SHALL delegate to the Episode_Recorder to start a new episode with the provided task_id, and return the generated episode_id with `success=true`.
2. WHEN an EpisodeControl request with action "stop" is received, THE Data_Node SHALL delegate to the Episode_Recorder to stop the episode, trigger the Label_Generator and Failure_Miner, and return `success=true`.
3. WHEN an EpisodeControl request with action "pause" is received, THE Data_Node SHALL delegate to the Episode_Recorder to pause the episode and return `success=true`.
4. WHEN an EpisodeControl request with action "resume" is received, THE Data_Node SHALL delegate to the Episode_Recorder to resume the episode and return `success=true`.
5. WHEN an EpisodeControl request with action "label" is received with `labels_json`, THE Data_Node SHALL delegate to the Episode_Recorder to merge the labels and return `success=true`.
6. IF the Episode_Recorder returns an error for any action, THEN THE Data_Node SHALL return `success=false` with the error message.
7. IF the action string is not one of "start", "stop", "pause", "resume", "label", THEN THE Data_Node SHALL return `success=false` with a message indicating the action is not recognized.

### Requirement 10: GetSystemVersions Service Handler

**User Story:** As a system operator, I want to query the current system versions via a ROS2 service, so that I can verify which software versions are running.

#### Acceptance Criteria

1. WHEN a GetSystemVersions request is received, THE Data_Node SHALL delegate to the Version_Tracker to retrieve the current `SystemVersions` snapshot.
2. THE Data_Node SHALL wrap the `SystemVersions` in a JsonEnvelope and return it in the `versions_json` response field with `success=true`.
3. IF the Version_Tracker has not yet captured a snapshot, THEN THE Data_Node SHALL capture a fresh snapshot before returning.

### Requirement 11: Episode Data Serialization

**User Story:** As a developer, I want episode data reliably serialized to and deserialized from JSON on disk, so that episodes can be stored, loaded, and exported without data loss.

#### Acceptance Criteria

1. THE Episode_Recorder SHALL serialize `EpisodeLog` to JSON using Pydantic's `model_dump_json` method and write it to `episode.json` in the Episode_Directory.
2. THE Episode_Recorder SHALL deserialize `EpisodeLog` from `episode.json` using Pydantic's `model_validate_json` method when loading an existing episode.
3. FOR ALL valid `EpisodeLog` objects, serializing to JSON and deserializing back SHALL produce an equivalent `EpisodeLog` object (round-trip property).
4. FOR ALL valid `FrameLog` objects, serializing to JSON and deserializing back SHALL produce an equivalent `FrameLog` object (round-trip property).
5. FOR ALL valid `EpisodeLabels` objects, serializing to JSON and deserializing back SHALL produce an equivalent `EpisodeLabels` object (round-trip property).
6. FOR ALL valid `SystemVersions` objects, serializing to JSON and deserializing back SHALL produce an equivalent `SystemVersions` object (round-trip property).

### Requirement 12: Configuration File

**User Story:** As a system integrator, I want a well-defined YAML configuration file for data collection parameters, so that I can tune recording behavior without code changes.

#### Acceptance Criteria

1. THE data_params.yaml file SHALL define the `storage_path` (base directory for episode data), `frame_rate_hz` (frame capture rate), `auto_record` (boolean to enable automatic episode start/stop from TaskStatus), and `max_episodes` (maximum number of episodes to retain on disk).
2. THE data_params.yaml file SHALL define failure mining thresholds: `mask_confidence_threshold` (default 0.5), `tracking_error_threshold`, and `vla_confidence_threshold`.
3. THE Data_Node SHALL accept a ROS2 parameter specifying the file path to data_params.yaml.
4. THE Data_Node SHALL accept ROS2 parameters that override values from data_params.yaml at launch time.

### Requirement 13: Launch File

**User Story:** As a system integrator, I want a ROS2 launch file that starts the data node with configurable parameters, so that I can integrate the data collection subsystem into the full system launch.

#### Acceptance Criteria

1. THE data.launch.py file SHALL launch the Data_Node with default parameters from data_params.yaml.
2. THE data.launch.py file SHALL accept launch arguments for the data params file path and storage path.
3. WHEN launch arguments are provided, THE data.launch.py file SHALL pass them as ROS2 parameter overrides to the Data_Node.

### Requirement 14: Pydantic ↔ ROS2 Message Converters

**User Story:** As a developer, I want reliable conversion functions between Pydantic models and ROS2 messages for data collection types, so that the data node can interoperate with both the Pydantic-based interfaces package and the ROS2 message layer.

#### Acceptance Criteria

1. THE Converter SHALL provide a function to convert a `roboweave_msgs/msg/TaskStatus` ROS2 message to a dictionary containing task_id, status, progress, current_node_id, failure_code, and message.
2. THE Converter SHALL provide a function to convert a `roboweave_msgs/msg/ExecutionEvent` ROS2 message to a `roboweave_interfaces.event.ExecutionEvent` Pydantic model.
3. THE Converter SHALL provide a function to convert a `roboweave_msgs/msg/SafetyStatus` ROS2 message to a dictionary containing safety_level, e_stop_active, collision_detected, and active_violations.
4. THE Converter SHALL provide a function to convert a `roboweave_interfaces.episode.EpisodeLabels` Pydantic model to a JsonEnvelope-wrapped JSON string and vice versa.
5. THE Converter SHALL provide a function to convert a `roboweave_interfaces.episode.SystemVersions` Pydantic model to a JsonEnvelope-wrapped JSON string and vice versa.
6. FOR ALL valid `ExecutionEvent` Pydantic models, converting to a ROS2 message and back SHALL produce an equivalent Pydantic model (round-trip property).

### Requirement 15: Disk Storage Management

**User Story:** As a system operator, I want episode storage managed automatically, so that the disk does not fill up during long-running data collection sessions.

#### Acceptance Criteria

1. WHEN the number of episodes on disk exceeds the `max_episodes` parameter, THE Data_Node SHALL delete the oldest completed episodes (by start_time) until the count is within the limit.
2. THE Data_Node SHALL only delete episodes with status `COMPLETED_SUCCESS` or `COMPLETED_FAILURE`, and SHALL preserve episodes with status `RECORDING` or `PAUSED`.
3. WHEN an episode is deleted for storage management, THE Data_Node SHALL remove the entire Episode_Directory including all frame data files.
4. IF the `max_episodes` parameter is set to 0, THE Data_Node SHALL retain all episodes without automatic deletion.
