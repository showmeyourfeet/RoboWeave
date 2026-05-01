cmake_minimum_required(VERSION 3.8)
project(roboweave_msgs)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(trajectory_msgs REQUIRED)
find_package(action_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  # Messages
  "msg/DataRef.msg"
  "msg/ImageRef.msg"
  "msg/DepthRef.msg"
  "msg/PointCloudRef.msg"
  "msg/MaskRef.msg"
  "msg/TrajectoryRef.msg"
  "msg/WorldStateRef.msg"
  "msg/JsonEnvelope.msg"
  "msg/Detection.msg"
  "msg/BoundingBox3D.msg"
  "msg/GraspConstraints.msg"
  "msg/GraspCandidate.msg"
  "msg/ReachabilityResult.msg"
  "msg/CollisionPair.msg"
  "msg/VLASafetyConstraints.msg"
  "msg/SafetyStatus.msg"
  "msg/RobotStateMsg.msg"
  "msg/ArmState.msg"
  "msg/GripperState.msg"
  "msg/TaskStatus.msg"
  "msg/ExecutionEvent.msg"
  "msg/WorldStateUpdate.msg"
  "msg/WorldStateStamped.msg"
  "msg/HITLRequestMsg.msg"
  "msg/TeleopCommand.msg"
  # Services
  "srv/DetectObjects.srv"
  "srv/SegmentObject.srv"
  "srv/BuildPointCloud.srv"
  "srv/EstimatePose.srv"
  "srv/PlanGrasp.srv"
  "srv/CheckReachability.srv"
  "srv/CheckCollision.srv"
  "srv/GripperCommand.srv"
  "srv/SafetyControl.srv"
  "srv/DispatchPlan.srv"
  "srv/TaskControl.srv"
  "srv/UpdateWorldState.srv"
  "srv/QueryWorldState.srv"
  "srv/ListSkills.srv"
  "srv/SkillHealth.srv"
  "srv/RequestRecovery.srv"
  "srv/EpisodeControl.srv"
  "srv/GetSystemVersions.srv"
  "srv/FilterVLAAction.srv"
  "srv/HITLRespond.srv"
  # Actions
  "action/PlanMotion.action"
  "action/TrackPose.action"
  "action/RunVLASkill.action"
  "action/ExecuteTrajectory.action"
  "action/CallSkill.action"
  DEPENDENCIES
    std_msgs
    geometry_msgs
    sensor_msgs
    trajectory_msgs
    action_msgs
)

ament_package()
