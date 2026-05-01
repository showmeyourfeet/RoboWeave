# Arm identifier (e.g. "left_arm", "right_arm")
string arm_id

# Current joint positions in radians
float64[] joint_positions

# Current joint velocities in rad/s
float64[] joint_velocities

# Current joint efforts in Nm
float64[] joint_efforts

# End-effector pose in base_link frame
geometry_msgs/Pose eef_pose

# Manipulability measure at current configuration [0.0, 1.0]
float64 manipulability
