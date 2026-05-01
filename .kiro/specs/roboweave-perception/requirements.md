# Requirements Document

## Introduction

The `roboweave_perception` package is the perception layer of the RoboWeave hybrid robotics system. It provides open-vocabulary object detection, object segmentation, RGBD-to-point-cloud construction, 6-DOF pose estimation, and continuous pose tracking. Each capability is exposed as a ROS2 service (detection, segmentation, point cloud, pose estimation) or action (pose tracking), hosted by a single `PerceptionNode`. A backend plugin system allows swapping implementations (e.g., mock → GroundingDINO, mock → SAM2) without changing the node or service interfaces.

This is Phase 2.1 of the RoboWeave project, building on the already-implemented `roboweave_interfaces` (Pydantic models: `DetectionResult`, `SegmentationResult`, `PointCloudResult`, `PoseEstimationResult`, `SE3`, `BoundingBox3D`, `DataRef` hierarchy) and `roboweave_msgs` (ROS2 msg/srv/action definitions: `DetectObjects.srv`, `SegmentObject.srv`, `BuildPointCloud.srv`, `EstimatePose.srv`, `TrackPose.action`).

The MVP target uses mock/simple backends only. Real model backends (GroundingDINO, SAM2, FoundationPose) will be added in later phases.

## Glossary

- **Perception_Node**: The main ROS2 node that hosts all perception service and action servers, manages backend lifecycle, and loads configuration.
- **Detector**: A component that performs open-vocabulary object detection on an RGB image given a text query, returning bounding boxes, categories, and confidence scores.
- **Segmentor**: A component that produces a segmentation mask for a specified object given an RGB image and optional depth image.
- **Point_Cloud_Builder**: A component that constructs a 3D point cloud from a depth image and a segmentation mask, using camera intrinsics for projection.
- **Pose_Estimator**: A component that estimates the 6-DOF pose of an object from its point cloud.
- **Pose_Tracker**: A component that continuously tracks the pose of an object over time, exposed as a ROS2 action with periodic feedback.
- **Backend**: A swappable implementation of a perception capability (Detector, Segmentor, Point_Cloud_Builder, Pose_Estimator). Each backend conforms to an abstract interface and is selected via configuration.
- **Backend_Registry**: A configuration-driven mechanism that maps backend names to their implementing classes, allowing runtime selection of which backend to use for each capability.
- **Converter**: A set of functions that translate between `roboweave_interfaces` Pydantic models and `roboweave_msgs` ROS2 message types for the perception domain.
- **ImageRef**: A ROS2 message (and Pydantic model) referencing an RGB image stored at a URI, with encoding, width, and height metadata.
- **DepthRef**: A ROS2 message (and Pydantic model) referencing a depth image stored at a URI, with encoding, dimensions, and depth unit metadata.
- **MaskRef**: A ROS2 message (and Pydantic model) referencing a segmentation mask stored at a URI, with object_id, confidence, and pixel count.
- **PointCloudRef**: A ROS2 message (and Pydantic model) referencing a point cloud stored at a URI, with point count, color/normal flags, and format.
- **Detection**: A ROS2 message containing object_id, category, matched_query, 2D bounding box, confidence, and estimated camera-frame pose.
- **SE3**: A 6-DOF pose representation with position [x, y, z] and quaternion [x, y, z, w].
- **BoundingBox3D**: An axis-aligned 3D bounding box with center pose and size [x, y, z] in meters.
- **perception_params.yaml**: A YAML configuration file defining runtime parameters for the Perception_Node (confidence thresholds, tracking frequency, publish rates).
- **model_registry.yaml**: A YAML configuration file mapping each perception capability to its active backend name and backend-specific parameters.

## Requirements

### Requirement 1: Detector Abstract Interface and Mock Backend

**User Story:** As a robotics developer, I want a pluggable object detection interface with a working mock backend, so that I can develop and test the perception pipeline without requiring real ML models.

#### Acceptance Criteria

1. THE Detector SHALL define an abstract method `detect` that accepts an RGB image (as a numpy array), a text query string, and a confidence threshold, and returns a list of `DetectionResult` Pydantic models.
2. THE Detector SHALL define an abstract method `get_backend_name` that returns the string name of the active backend.
3. WHEN the mock Detector backend receives a `detect` call, THE mock Detector backend SHALL return a list containing one synthetic `DetectionResult` with the category derived from the query string, a bounding box within the image dimensions, and a confidence of 1.0.
4. IF the RGB image provided to `detect` is empty (zero width or zero height), THEN THE Detector SHALL raise a `ValueError` with a descriptive message.
5. IF the query string provided to `detect` is empty, THEN THE Detector SHALL raise a `ValueError` with a descriptive message.

### Requirement 2: Segmentor Abstract Interface and Mock Backend

**User Story:** As a robotics developer, I want a pluggable segmentation interface with a working mock backend, so that I can develop downstream components (point cloud, pose) without requiring a real segmentation model.

#### Acceptance Criteria

1. THE Segmentor SHALL define an abstract method `segment` that accepts an RGB image (as a numpy array), an object_id string, and an optional 2D bounding box hint, and returns a `SegmentationResult` Pydantic model.
2. THE Segmentor SHALL define an abstract method `get_backend_name` that returns the string name of the active backend.
3. WHEN the mock Segmentor backend receives a `segment` call with a bounding box hint, THE mock Segmentor backend SHALL generate a rectangular mask matching the bounding box region and return a `SegmentationResult` with the mask URI, a confidence of 1.0, and the pixel count equal to the bounding box area.
4. WHEN the mock Segmentor backend receives a `segment` call without a bounding box hint, THE mock Segmentor backend SHALL generate a centered rectangular mask covering 25% of the image area.
5. IF the RGB image provided to `segment` is empty (zero width or zero height), THEN THE Segmentor SHALL raise a `ValueError` with a descriptive message.

### Requirement 3: Point Cloud Builder Abstract Interface and Simple Backend

**User Story:** As a robotics developer, I want a point cloud builder that converts masked RGBD data into a 3D point cloud, so that downstream pose estimation can operate on 3D geometry.

#### Acceptance Criteria

1. THE Point_Cloud_Builder SHALL define an abstract method `build` that accepts a depth image (as a numpy array), a binary mask (as a numpy array), camera intrinsics (fx, fy, cx, cy), and an object_id string, and returns a `PointCloudResult` Pydantic model.
2. THE Point_Cloud_Builder SHALL define an abstract method `get_backend_name` that returns the string name of the active backend.
3. WHEN the simple Point_Cloud_Builder backend receives a `build` call, THE simple Point_Cloud_Builder backend SHALL project each masked pixel into 3D using the pinhole camera model with the provided intrinsics, producing a point cloud in the camera frame.
4. WHEN the simple Point_Cloud_Builder backend produces a point cloud, THE simple Point_Cloud_Builder backend SHALL compute the center pose as the centroid of all projected points and the 3D bounding box as the axis-aligned extent of all projected points.
5. WHEN the simple Point_Cloud_Builder backend produces a point cloud, THE simple Point_Cloud_Builder backend SHALL set `num_points` in the result to the count of valid projected points (depth > 0 within the mask).
6. IF the mask contains zero foreground pixels, THEN THE Point_Cloud_Builder SHALL return a `PointCloudResult` with `num_points` set to 0 and `center_pose` set to None.
7. IF the depth image and mask have different dimensions, THEN THE Point_Cloud_Builder SHALL raise a `ValueError` with a descriptive message.

### Requirement 4: Pose Estimator Abstract Interface and Mock Backend

**User Story:** As a robotics developer, I want a pluggable pose estimation interface with a mock backend, so that I can test the full perception-to-manipulation pipeline without a real pose estimation model.

#### Acceptance Criteria

1. THE Pose_Estimator SHALL define an abstract method `estimate` that accepts a `PointCloudResult` Pydantic model, an object_id string, and an estimation method string, and returns a `PoseEstimationResult` Pydantic model.
2. THE Pose_Estimator SHALL define an abstract method `get_backend_name` that returns the string name of the active backend.
3. WHEN the mock Pose_Estimator backend receives an `estimate` call, THE mock Pose_Estimator backend SHALL return a `PoseEstimationResult` with the pose set to the `center_pose` from the input `PointCloudResult`, a confidence of 1.0, and an identity covariance (36-element list with 1.0 on the diagonal).
4. IF the input `PointCloudResult` has `num_points` equal to 0, THEN THE Pose_Estimator SHALL return a `PoseEstimationResult` with confidence 0.0 and a default identity pose.
5. IF the input `PointCloudResult` has `center_pose` set to None, THEN THE Pose_Estimator SHALL return a `PoseEstimationResult` with confidence 0.0 and a default identity pose.

### Requirement 5: Pose Tracker (ROS2 Action)

**User Story:** As a skill developer, I want continuous pose tracking for a target object via a ROS2 action, so that manipulation skills can receive real-time pose updates during execution.

#### Acceptance Criteria

1. THE Pose_Tracker SHALL host a ROS2 action server for the `TrackPose` action on the `/roboweave/perception/track_pose` endpoint.
2. WHEN a TrackPose goal is received, THE Pose_Tracker SHALL begin periodically re-estimating the pose of the specified object_id at the requested `tracking_frequency_hz` using the Detector, Segmentor, Point_Cloud_Builder, and Pose_Estimator pipeline.
3. WHILE tracking is active, THE Pose_Tracker SHALL publish feedback containing the current estimated `PoseStamped`, the tracking confidence, and the elapsed tracking time in seconds.
4. WHEN a cancel request is received during tracking, THE Pose_Tracker SHALL stop the tracking loop and return a result with `final_status` set to `cancelled`.
5. IF the Detector fails to detect the tracked object for a configurable number of consecutive frames (default 5), THEN THE Pose_Tracker SHALL stop tracking and return a result with `final_status` set to `lost` and error_code `PER_TRACKING_LOST`.
6. WHEN tracking completes normally (cancelled by the caller or externally stopped), THE Pose_Tracker SHALL return a result with `final_status` set to `completed`.
7. THE Pose_Tracker SHALL use the camera_id from the goal to select which camera feed to use for re-detection.

### Requirement 6: Perception Node Lifecycle

**User Story:** As a system integrator, I want a single ROS2 node that initializes all perception backends, hosts all perception services and actions, and manages configuration, so that I can launch the perception subsystem with a single command.

#### Acceptance Criteria

1. THE Perception_Node SHALL load perception_params.yaml and model_registry.yaml from file paths specified by ROS2 parameters.
2. THE Perception_Node SHALL instantiate the Detector, Segmentor, Point_Cloud_Builder, and Pose_Estimator backends based on the backend names specified in model_registry.yaml.
3. THE Perception_Node SHALL host the following ROS2 service servers: `/roboweave/perception/detect_objects` (DetectObjects), `/roboweave/perception/segment_object` (SegmentObject), `/roboweave/perception/build_point_cloud` (BuildPointCloud), `/roboweave/perception/estimate_pose` (EstimatePose).
4. THE Perception_Node SHALL host the ROS2 action server `/roboweave/perception/track_pose` (TrackPose) via the Pose_Tracker.
5. WHEN the Perception_Node starts, THE Perception_Node SHALL log the active backend name for each perception capability.
6. WHEN the Perception_Node shuts down, THE Perception_Node SHALL release all backend resources.
7. IF a backend specified in model_registry.yaml is not found in the Backend_Registry, THEN THE Perception_Node SHALL log an error and fall back to the mock backend for that capability.

### Requirement 7: DetectObjects Service Handler

**User Story:** As a skill developer, I want to call a ROS2 service to detect objects in a camera image, so that the runtime can identify objects for manipulation tasks.

#### Acceptance Criteria

1. WHEN a DetectObjects request is received, THE Perception_Node SHALL resolve the RGB image from the `rgb_ref` field in the request.
2. WHEN a DetectObjects request is received, THE Perception_Node SHALL call the Detector `detect` method with the resolved image, the `query` string, and the `confidence_threshold` from the request.
3. WHEN the Detector returns results, THE Perception_Node SHALL convert each `DetectionResult` Pydantic model to a `Detection` ROS2 message and return them in the response with `success=true`.
4. IF the Detector raises an exception, THEN THE Perception_Node SHALL return a response with `success=false`, error_code `PER_DETECTION_FAILED`, and the exception message.
5. IF the `rgb_ref` URI cannot be resolved to a valid image, THEN THE Perception_Node SHALL return a response with `success=false`, error_code `PER_DETECTION_FAILED`, and a message indicating the image could not be loaded.

### Requirement 8: SegmentObject Service Handler

**User Story:** As a skill developer, I want to call a ROS2 service to segment a detected object, so that I can obtain a precise mask for point cloud extraction.

#### Acceptance Criteria

1. WHEN a SegmentObject request is received, THE Perception_Node SHALL resolve the RGB image from the `rgb_ref` field and the depth image from the `depth_ref` field in the request.
2. WHEN a SegmentObject request is received, THE Perception_Node SHALL call the Segmentor `segment` method with the resolved RGB image, the `object_id` from the request, and any available bounding box hint.
3. WHEN the Segmentor returns a result, THE Perception_Node SHALL convert the `SegmentationResult` Pydantic model to a `MaskRef` ROS2 message and return it in the response with `success=true`.
4. IF the Segmentor raises an exception, THEN THE Perception_Node SHALL return a response with `success=false`, error_code `PER_SEGMENTATION_FAILED`, and the exception message.

### Requirement 9: BuildPointCloud Service Handler

**User Story:** As a skill developer, I want to call a ROS2 service to build a 3D point cloud from a depth image and mask, so that I can obtain 3D geometry for pose estimation and grasp planning.

#### Acceptance Criteria

1. WHEN a BuildPointCloud request is received, THE Perception_Node SHALL resolve the depth image from the `depth_ref` field and the mask from the `mask_ref` field in the request.
2. WHEN a BuildPointCloud request is received, THE Perception_Node SHALL call the Point_Cloud_Builder `build` method with the resolved depth image, the resolved mask, camera intrinsics obtained from the camera_info topic or configuration, and the `object_id` from the request.
3. WHEN the Point_Cloud_Builder returns a result, THE Perception_Node SHALL convert the `PointCloudResult` fields to the response, populating `point_cloud_ref` and `bbox_3d`, and return with `success=true`.
4. IF the Point_Cloud_Builder raises an exception, THEN THE Perception_Node SHALL return a response with `success=false`, error_code `PER_POINT_CLOUD_FAILED`, and the exception message.
5. IF the Point_Cloud_Builder returns a result with `num_points` equal to 0, THEN THE Perception_Node SHALL return a response with `success=false`, error_code `PER_POINT_CLOUD_EMPTY`, and a message indicating no valid points were produced.

### Requirement 10: EstimatePose Service Handler

**User Story:** As a skill developer, I want to call a ROS2 service to estimate the 6-DOF pose of an object from its point cloud, so that the planner can compute grasp poses and motion plans.

#### Acceptance Criteria

1. WHEN an EstimatePose request is received, THE Perception_Node SHALL resolve the point cloud from the `point_cloud_ref` field in the request.
2. WHEN an EstimatePose request is received, THE Perception_Node SHALL call the Pose_Estimator `estimate` method with the resolved point cloud data, the `object_id`, and the `method` string from the request.
3. WHEN the Pose_Estimator returns a result, THE Perception_Node SHALL convert the `PoseEstimationResult` to the response, populating `pose` as a `geometry_msgs/PoseStamped`, `confidence`, and `covariance`, and return with `success=true`.
4. IF the Pose_Estimator raises an exception, THEN THE Perception_Node SHALL return a response with `success=false`, error_code `PER_POSE_ESTIMATION_FAILED`, and the exception message.
5. IF the Pose_Estimator returns a result with confidence below a configurable minimum threshold (default 0.1), THEN THE Perception_Node SHALL return a response with `success=false`, error_code `PER_POSE_ESTIMATION_FAILED`, and a message indicating low confidence.

### Requirement 11: Pydantic ↔ ROS2 Message Converters

**User Story:** As a developer, I want reliable conversion functions between Pydantic models and ROS2 messages for perception types, so that the perception node can interoperate with both the Pydantic-based interfaces package and the ROS2 message layer.

#### Acceptance Criteria

1. THE Converter SHALL provide a function to convert a `roboweave_interfaces.perception.DetectionResult` Pydantic model to a `roboweave_msgs/msg/Detection` ROS2 message and vice versa.
2. THE Converter SHALL provide a function to convert a `roboweave_interfaces.perception.SegmentationResult` Pydantic model to a `roboweave_msgs/msg/MaskRef` ROS2 message and vice versa.
3. THE Converter SHALL provide a function to convert a `roboweave_interfaces.perception.PointCloudResult` Pydantic model to a `roboweave_msgs/msg/PointCloudRef` ROS2 message and vice versa.
4. THE Converter SHALL provide a function to convert a `roboweave_interfaces.perception.PoseEstimationResult` Pydantic model to a `geometry_msgs/PoseStamped` ROS2 message and vice versa.
5. THE Converter SHALL provide functions to convert `roboweave_interfaces.refs.ImageRef`, `DepthRef`, `MaskRef`, and `PointCloudRef` Pydantic models to their corresponding ROS2 messages and vice versa.
6. FOR ALL valid Pydantic perception models, converting to a ROS2 message and back SHALL produce an equivalent Pydantic model (round-trip property).

### Requirement 12: Backend Plugin System

**User Story:** As a robotics developer, I want a plugin system for perception backends, so that I can swap between mock, simple, and production ML model implementations without modifying the perception node code.

#### Acceptance Criteria

1. THE Backend_Registry SHALL maintain a mapping from capability name (detector, segmentor, point_cloud_builder, pose_estimator) and backend name to the implementing Python class.
2. THE Backend_Registry SHALL provide a `get_backend` method that accepts a capability name and a backend name and returns an instance of the corresponding backend class.
3. WHEN a backend name is registered for a capability, THE Backend_Registry SHALL verify that the class implements the required abstract interface for that capability.
4. IF `get_backend` is called with an unregistered backend name, THEN THE Backend_Registry SHALL raise a `KeyError` with a message listing the available backends for that capability.
5. THE Backend_Registry SHALL support registering new backends at import time via a decorator or explicit registration call, so that adding a new backend requires only creating a new module in the `backends/` directory.

### Requirement 13: Configuration Files

**User Story:** As a system integrator, I want well-defined YAML configuration files for perception parameters and backend selection, so that I can tune the perception subsystem and swap backends without code changes.

#### Acceptance Criteria

1. THE perception_params.yaml file SHALL define the default confidence threshold for detection, the default tracking frequency in Hz, the maximum consecutive missed frames before tracking is considered lost, and the minimum pose estimation confidence threshold.
2. THE model_registry.yaml file SHALL define, for each perception capability (detector, segmentor, point_cloud_builder, pose_estimator), the active backend name and a dictionary of backend-specific parameters.
3. THE Perception_Node SHALL accept ROS2 parameters specifying the file paths to perception_params.yaml and model_registry.yaml.
4. THE Perception_Node SHALL accept ROS2 parameters that override values from perception_params.yaml at launch time.

### Requirement 14: Launch File

**User Story:** As a system integrator, I want a ROS2 launch file that starts the perception node with configurable parameters, so that I can integrate the perception subsystem into the full system launch.

#### Acceptance Criteria

1. THE perception.launch.py file SHALL launch the Perception_Node with default parameters from perception_params.yaml and model_registry.yaml.
2. THE perception.launch.py file SHALL accept launch arguments for the perception params file path, model registry file path, and camera_id.
3. WHEN launch arguments are provided, THE perception.launch.py file SHALL pass them as ROS2 parameter overrides to the Perception_Node.
