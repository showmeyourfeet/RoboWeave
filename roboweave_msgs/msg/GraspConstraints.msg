# Preferred grasp regions on the object (e.g. "handle", "rim")
string[] preferred_regions

# Regions to avoid during grasping
string[] avoid_regions

# Maximum allowable grasp force in Newtons
float64 max_force

# Minimum gripper opening width in meters
float64 min_gripper_width

# Maximum gripper opening width in meters
float64 max_gripper_width

# Hint for approach direction [x, y, z] in base_link frame; empty = no preference
float64[] approach_direction_hint
