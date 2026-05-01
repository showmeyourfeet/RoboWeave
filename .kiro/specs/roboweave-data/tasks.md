# Implementation Plan: roboweave-data

## Overview

Implement the `roboweave_data` ROS2 ament_python package following the same structure as `roboweave_control` and `roboweave_planning`. Tasks proceed bottom-up: package scaffolding → configuration → pure-Python core components (EpisodeRecorder, SkillLogger, FrameLogger, LabelGenerator, FailureMiner, DataExporter, VersionTracker) → converters → DataNode ROS2 shell → launch file → tests. Each task builds on the previous, and property-based tests are placed close to the code they validate.

## Tasks

- [ ] 1. Scaffold the roboweave_data package
  - [ ] 1.1 Create package directory structure and boilerplate files
    - Create `roboweave_data/` top-level directory with `setup.py`, `setup.cfg`, `package.xml`, `resource/roboweave_data` marker file
    - Create inner `roboweave_data/roboweave_data/__init__.py`
    - Create `roboweave_data/tests/__init__.py` and `roboweave_data/tests/conftest.py`
    - Create `roboweave_data/config/` and `roboweave_data/launch/` directories with `.gitkeep` files
    - Mirror `roboweave_control` package layout: `setup.py` with ament data_files, `package.xml` with rclpy/roboweave_msgs/roboweave_interfaces dependencies, `setup.cfg` with install scripts path
    - Entry point: `data_node = roboweave_data.data_node:main`
    - _Requirements: 8.1, 12.1, 13.1_

  - [ ] 1.2 Create data_params.yaml configuration file
    - Create `roboweave_data/config/data_params.yaml` with: `storage_path: "/data/roboweave/episodes"`, `frame_rate_hz: 10.0`, `auto_record: true`, `max_episodes: 100`, `mask_confidence_threshold: 0.5`, `tracking_error_threshold: 0.05`, `vla_confidence_threshold: 0.3`
    - _Requirements: 12.1, 12.2_

- [ ] 2. Implement EpisodeRecorder
  - [ ] 2.1 Create EpisodeRecorder with episode lifecycle management
    - Create `roboweave_data/roboweave_data/episode_recorder.py`
    - Implement `__init__(self, storage_path: str)` storing the base storage path
    - Implement `start(task_id, task_instruction, system_versions)` that creates a new `EpisodeLog` with unique `episode_id` (format `ep_{timestamp_ms}_{random_hex8}`), sets `status=RECORDING`, records `start_time`, stores `task_id`, creates the episode directory and `frames/` subdirectory on disk, returns `episode_id`
    - Implement `stop(outcome)` that sets status to `COMPLETED_SUCCESS` or `COMPLETED_FAILURE` based on outcome, computes `duration_sec = end_time - start_time`, writes `episode.json` via `EpisodeLog.model_dump_json()`
    - Implement `pause()` that sets status to `PAUSED`, raises `RuntimeError` if not recording
    - Implement `resume()` that sets status back to `RECORDING`, raises `RuntimeError` if not paused
    - Implement `merge_labels(labels)` that merges provided `EpisodeLabels` into the episode and re-writes `episode.json`
    - Implement `add_skill_log(skill_log)` and `add_frame_log(frame_log)` to append entries to the active episode
    - Implement `load_episode(episode_dir)` using `EpisodeLog.model_validate_json()`
    - Implement `list_episodes()` and `delete_episode(episode_dir)`
    - Enforce state machine: start raises if already recording (Req 1.5), stop/pause/resume raise if no active episode or wrong state (Req 1.6)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 11.1, 11.2_

  - [ ]* 2.2 Write property test for episode state machine transitions
    - **Property 1: Episode state machine transitions**
    - **Validates: Requirements 1.1, 1.3, 1.4, 1.5**

  - [ ]* 2.3 Write property test for episode duration computation
    - **Property 2: Episode duration computation**
    - **Validates: Requirements 1.2**

  - [ ]* 2.4 Write property test for label merging
    - **Property 3: Label merging preserves provided values**
    - **Validates: Requirements 1.7**

- [ ] 3. Implement SkillLogger
  - [ ] 3.1 Create SkillLogger with execution event processing
    - Create `roboweave_data/roboweave_data/skill_logger.py`
    - Implement `__init__()` with `_pending_skills` dict and `_buffer` list
    - Implement `process_event(event)` that handles `skill_started` (create `SkillLog` with `status="running"`, `start_time`), `skill_succeeded` (finalize with `status="succeeded"`, compute `runtime_ms`), `skill_failed` (finalize with `status="failed"`, set `failure_code`), `skill_timeout` (finalize with `status="timeout"`, set `failure_code`)
    - Return completed `SkillLog` when a skill ends, `None` for start events
    - Implement `buffer_event(event)` and `flush_buffer()` for pause support
    - Expose `pending_skills` property
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 3.2 Write property test for skill lifecycle
    - **Property 4: Skill lifecycle produces correct SkillLog**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.6**

  - [ ]* 3.3 Write property test for paused event buffering
    - **Property 5: Paused skill events are buffered and recovered**
    - **Validates: Requirements 2.5**

- [ ] 4. Implement FrameLogger
  - [ ] 4.1 Create FrameLogger with rate-limited frame capture
    - Create `roboweave_data/roboweave_data/frame_logger.py`
    - Implement `__init__(frame_rate_hz, episode_dir)` storing rate and directory
    - Implement `maybe_capture(episode_id, timestamp, rgb_data, depth_data, robot_state_json, world_state_json, safety_status)` that returns `None` if elapsed time since last capture is less than `1.0 / frame_rate_hz`, otherwise writes binary data to `frames/{frame_index:06d}_{type}.{ext}` files, creates `FrameLog` with `file://` URIs relative to episode directory, sets unavailable sensor `DataRef` fields to `None`
    - Implement `reset()` to clear the rate limiter state
    - Expose `frame_count` property
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ]* 4.2 Write property test for frame rate limiting
    - **Property 6: Frame rate limiting**
    - **Validates: Requirements 3.1**

  - [ ]* 4.3 Write property test for partial sensor capture
    - **Property 7: Frame capture with partial sensor data**
    - **Validates: Requirements 3.2, 3.4, 3.5, 3.6**

- [ ] 5. Checkpoint - Verify core recording components
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement LabelGenerator
  - [ ] 6.1 Create LabelGenerator with auto-labeling logic
    - Create `roboweave_data/roboweave_data/label_generator.py`
    - Define `FAILURE_STAGE_MAP` class constant: `{"PER_": "perception", "GRP_": "planning", "IK_": "planning", "MOT_": "planning", "CTL_": "control", "VLA_": "vla", "SAF_": "safety"}`
    - Implement `generate(episode_log, execution_events, object_categories)` that produces `EpisodeLabels` with:
      - `success`: `True` if `status == COMPLETED_SUCCESS`
      - `failure_stage`: mapped from failure code prefix via `FAILURE_STAGE_MAP`
      - `failure_code`: from episode or first failed skill
      - `recovery_used`: `True` if any event has `event_type == recovery_started`
      - `human_intervention`: `True` if any `safety_triggered` event has recovery containing "teleop" or "manual"
      - `task_type`: extracted from `task_instruction`
      - `object_categories`: from provided categories list
    - Ensure all derivable fields are populated (no empty strings for fields that can be derived)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9_

  - [ ]* 6.2 Write property test for label generation correctness
    - **Property 8: Label generation correctness**
    - **Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9**

- [ ] 7. Implement FailureMiner
  - [ ] 7.1 Create FailureMiner with failure pattern matching and tagging
    - Create `roboweave_data/roboweave_data/failure_miner.py`
    - Implement `__init__(mask_confidence_threshold, vla_confidence_threshold)` with configurable thresholds
    - Implement `scan(episode_log, frame_logs, execution_events)` that returns a list of failure tags by checking:
      - `grasp_failure`: any skill `failure_code` matches `CTL_GRASP_SLIP` or prefix `GRP_`
      - `low_confidence_mask`: any frame's `mask_ref.mask_confidence < mask_confidence_threshold`
      - `vla_low_confidence`: any skill `failure_code` matches `VLA_CONFIDENCE_LOW`
      - `human_takeover`: any `safety_triggered` event with recovery containing "teleop"
      - `safety_stop`: any event `failure_code` matches `SAF_EMERGENCY_STOP` or `SAF_FORCE_LIMIT`
      - `recovery_success`: any event `event_type == recovery_succeeded`
      - `all_grasps_unreachable`: all grasp-related skills have `failure_code == IK_NO_SOLUTION`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

  - [ ]* 7.2 Write property test for failure mining tag correctness
    - **Property 9: Failure mining tag correctness**
    - **Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8**

  - [ ]* 7.3 Write unit tests for FailureMiner edge cases
    - Test clean episode with no failures returns empty tags (Req 5.1)
    - Test episode with multiple overlapping failure conditions returns all matching tags
    - _Requirements: 5.1, 5.9_

- [ ] 8. Implement DataExporter
  - [ ] 8.1 Create DataExporter with export, filtering, and manifest generation
    - Create `roboweave_data/roboweave_data/data_exporter.py`
    - Implement `__init__(storage_path)` storing the base storage path
    - Implement `export(episode_ids, output_dir, filter_tags, filter_success, filter_date_range)` that:
      - Loads each episode from disk, applies filter criteria (tags, success, date range)
      - Copies episode data (episode.json and frames/) into output directory organized by episode_id
      - Rewrites all `file://` URIs to be relative to the export output directory
      - Generates `manifest.json` with episode_id, task_type, success, tags, frame_count, duration_sec, system_versions for each exported episode
      - Skips missing episodes with a warning, continues exporting remaining
    - Implement `_rewrite_uris(episode_log, relative_base)` to rewrite DataRef URIs
    - Implement `_build_manifest(episodes)` to build manifest dict
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ]* 8.2 Write property test for export URI rewriting
    - **Property 12: Export URI rewriting**
    - **Validates: Requirements 6.4**

  - [ ]* 8.3 Write property test for manifest completeness
    - **Property 13: Export manifest completeness**
    - **Validates: Requirements 6.2, 6.6**

  - [ ]* 8.4 Write property test for export filtering correctness
    - **Property 14: Export filtering correctness**
    - **Validates: Requirements 6.3**

  - [ ]* 8.5 Write unit tests for DataExporter edge cases
    - Test export with missing episode_id skips and logs warning (Req 6.5)
    - Test export with empty episode list produces empty manifest
    - _Requirements: 6.5_

- [ ] 9. Implement VersionTracker
  - [ ] 9.1 Create VersionTracker with system version snapshot capture
    - Create `roboweave_data/roboweave_data/version_tracker.py`
    - Implement `__init__(node=None)` storing optional ROS2 node reference
    - Implement `capture_snapshot()` that creates a `SystemVersions` with:
      - `roboweave_version` from `roboweave_interfaces._version.SCHEMA_VERSION`
      - `timestamp` set to current time
      - `perception_models`, `vla_models`, `planner_backend`, `planner_version`, `controller_version` queried from ROS2 parameters on respective nodes (best-effort)
      - Unavailable fields set to empty string (no exceptions)
    - Expose `latest_snapshot` property
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 9.2 Write unit tests for VersionTracker
    - Test `roboweave_version` matches `SCHEMA_VERSION` (Req 7.2)
    - Test `timestamp` is recent (Req 7.3)
    - Test unavailable fields default to empty string (Req 7.5)
    - _Requirements: 7.2, 7.3, 7.5_

- [ ] 10. Checkpoint - Verify all pure-Python components
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement Pydantic ↔ ROS2 message converters and JSON round-trip tests
  - [ ] 11.1 Create data converters module
    - Create `roboweave_data/roboweave_data/converters.py` following the `roboweave_control/converters.py` dict-fallback pattern with `HAS_ROS2` guard
    - Implement `task_status_msg_to_dict(msg)` converting TaskStatus msg to dict with task_id, status, progress, current_node_id, failure_code, message
    - Implement `execution_event_msg_to_model(msg)` converting ExecutionEvent msg to `roboweave_interfaces.event.ExecutionEvent` Pydantic model
    - Implement `execution_event_model_to_msg_dict(event)` for round-trip testing
    - Implement `safety_status_msg_to_dict(msg)` converting SafetyStatus msg to dict with safety_level, e_stop_active, collision_detected, active_violations
    - Implement `episode_labels_to_json_envelope(labels)` / `json_envelope_to_episode_labels(json_str)` for EpisodeLabels ↔ JsonEnvelope
    - Implement `system_versions_to_json_envelope(versions)` / `json_envelope_to_system_versions(json_str)` for SystemVersions ↔ JsonEnvelope
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [ ]* 11.2 Write property test for JSON round-trip of Pydantic models
    - **Property 10: Episode data JSON round-trip**
    - **Validates: Requirements 11.3, 11.4, 11.5, 11.6**

  - [ ]* 11.3 Write property test for converter round-trip
    - **Property 11: Converter round-trip preserves models**
    - **Validates: Requirements 14.2, 14.4, 14.5, 14.6**

  - [ ]* 11.4 Write unit tests for converters
    - Test `task_status_msg_to_dict` produces correct dict keys (Req 14.1)
    - Test `safety_status_msg_to_dict` produces correct dict keys (Req 14.3)
    - _Requirements: 14.1, 14.3_

- [ ] 12. Implement DataNode ROS2 node
  - [ ] 12.1 Create DataNode with topic subscriptions, service servers, and component wiring
    - Create `roboweave_data/roboweave_data/data_node.py` with `HAS_ROS2` fallback pattern matching `ControlNode`
    - Declare ROS2 parameters and load config from `data_params.yaml`
    - Instantiate all components: `EpisodeRecorder`, `SkillLogger`, `FrameLogger`, `LabelGenerator`, `FailureMiner`, `DataExporter`, `VersionTracker`
    - Create subscribers for 5 topics: `/roboweave/task_status` (TaskStatus), `/roboweave/execution_events` (ExecutionEvent), `/roboweave/world_state_update` (WorldStateUpdate), `/roboweave/robot_state` (RobotStateMsg), `/roboweave/safety_status` (SafetyStatus)
    - Create service servers: `/roboweave/data/episode_control` (EpisodeControl), `/roboweave/data/get_system_versions` (GetSystemVersions)
    - Store latest sensor data for FrameLogger consumption
    - Implement `main()` entry point
    - _Requirements: 8.1, 8.2, 8.3, 8.8_

  - [ ] 12.2 Implement topic callbacks
    - Implement `_on_task_status(msg)`: auto-start episode if `auto_record` enabled and status is "running" with no active episode; auto-stop if status is "succeeded" or "failed" with active episode
    - Implement `_on_execution_event(msg)`: convert via converter, forward to SkillLogger; buffer if paused; append completed SkillLog to EpisodeRecorder
    - Implement `_on_world_state_update(msg)`: store latest world state, extract object categories for label generation
    - Implement `_on_robot_state(msg)`: store latest robot state, trigger FrameLogger `maybe_capture` if recording
    - Implement `_on_safety_status(msg)`: store latest safety status for frame data and label generation
    - _Requirements: 8.4, 8.5, 8.6, 8.7_

  - [ ] 12.3 Implement EpisodeControl service handler
    - Implement `_handle_episode_control(request, response)` dispatching to EpisodeRecorder based on action string
    - "start": capture VersionTracker snapshot, delegate to EpisodeRecorder.start(), return episode_id
    - "stop": delegate to EpisodeRecorder.stop(), trigger LabelGenerator.generate() and FailureMiner.scan(), merge results, persist tags to episode.json, enforce max_episodes cleanup
    - "pause": delegate to EpisodeRecorder.pause()
    - "resume": delegate to EpisodeRecorder.resume(), flush SkillLogger buffer
    - "label": delegate to EpisodeRecorder.merge_labels()
    - Return `success=false` with error message on any exception or unrecognized action
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 5.9_

  - [ ] 12.4 Implement GetSystemVersions service handler
    - Implement `_handle_get_system_versions(request, response)` delegating to VersionTracker
    - Capture fresh snapshot if none exists yet
    - Wrap SystemVersions in JsonEnvelope and return in `versions_json` field with `success=true`
    - _Requirements: 10.1, 10.2, 10.3_

  - [ ] 12.5 Implement storage management and shutdown
    - Implement `_enforce_max_episodes()` that deletes oldest completed episodes (by start_time) when count exceeds `max_episodes`; only delete `COMPLETED_SUCCESS` or `COMPLETED_FAILURE` episodes; preserve `RECORDING` and `PAUSED` episodes; skip deletion when `max_episodes` is 0
    - Implement `_shutdown()` that stops any active episode and flushes pending data to disk
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 8.9_

  - [ ]* 12.6 Write property test for storage management
    - **Property 15: Storage management preserves active episodes**
    - **Validates: Requirements 15.1, 15.2, 15.4**

  - [ ]* 12.7 Write unit tests for DataNode handlers
    - Test unrecognized action returns `success=false` (Req 9.7)
    - Test `max_episodes=0` retains all episodes (Req 15.4)
    - Test shutdown flushes active episode (Req 8.9)
    - _Requirements: 8.9, 9.7, 15.4_

- [ ] 13. Checkpoint - Verify DataNode and service handlers
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Create launch file and finalize package
  - [ ] 14.1 Create data.launch.py
    - Create `roboweave_data/launch/data.launch.py` that launches the DataNode with default parameters from data_params.yaml
    - Accept launch arguments for data params file path and storage path
    - Pass launch arguments as ROS2 parameter overrides to the DataNode
    - _Requirements: 13.1, 13.2, 13.3_

  - [ ] 14.2 Add ROS2 parameter override support to DataNode
    - Ensure DataNode accepts a ROS2 parameter for the data_params.yaml file path
    - Ensure ROS2 parameters override values from data_params.yaml at launch time
    - _Requirements: 12.3, 12.4_

  - [ ]* 14.3 Write unit tests for configuration and launch
    - Test data_params.yaml contains all required keys (Req 12.1, 12.2)
    - Test launch file accepts expected arguments (Req 13.2)
    - _Requirements: 12.1, 12.2, 13.2_

- [ ] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate the 15 universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All property tests use Hypothesis with `max_examples=100` and `deadline=None`
- All pure-Python component tests run without ROS2 dependency
- The package mirrors `roboweave_control` and `roboweave_planning` conventions: ament_python build, dict-fallback converters, `HAS_ROS2` guard pattern
