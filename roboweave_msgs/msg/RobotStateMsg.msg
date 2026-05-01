# Robot identifier
string robot_id

# State of each arm
ArmState[] arms

# State of each gripper
GripperState[] grippers

# Base pose in world frame (identity if fixed base)
geometry_msgs/Pose base_pose

# Whether the robot is currently in motion
bool is_moving

# Current control mode: "position" | "velocity" | "effort" | "impedance"
string current_control_mode
