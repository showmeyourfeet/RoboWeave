# Unique grasp identifier
string grasp_id

# 6-DOF grasp pose in base_link frame
geometry_msgs/Pose grasp_pose

# Approach direction unit vector [x, y, z]
float64[] approach_direction

# Required gripper opening width in meters
float64 gripper_width

# Grasp quality score [0.0, 1.0]
float64 grasp_score

# Collision quality score [0.0, 1.0]; higher = less collision risk
float64 collision_score

# Whether the grasp is reachable by IK
bool reachable

# Object regions matched by this grasp
string[] matched_regions

# IK joint solution for this grasp (empty if not computed)
float64[] ik_solution
