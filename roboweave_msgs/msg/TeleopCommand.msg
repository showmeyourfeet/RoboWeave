# Standard header with timestamp
std_msgs/Header header

# Target arm identifier (e.g. "left_arm")
string arm_id

# End-effector velocity command (linear + angular)
geometry_msgs/Twist twist

# Gripper action: "open" | "close" | "none"
string gripper_action
