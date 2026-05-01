# Gripper identifier (e.g. "left_gripper")
string gripper_id

# Gripper type: "parallel" | "vacuum" | "soft"
string type

# Current opening width in meters
float64 width

# Current grip force in Newtons
float64 force

# Whether the gripper is currently grasping an object
bool is_grasping

# ID of the grasped object (empty if not grasping)
string grasped_object_id
