# Maximum end-effector linear velocity in m/s
float64 max_velocity

# Maximum end-effector angular velocity in rad/s
float64 max_angular_velocity

# Maximum contact force in Newtons
float64 force_limit

# Maximum joint torque in Nm
float64 torque_limit

# ID of the workspace limit definition to apply (empty = default)
string workspace_limit_id

# Maximum allowed duration for the VLA skill in seconds
float64 max_duration_sec

# Whether intentional contact with objects is allowed
bool allow_contact

# Minimum VLA confidence threshold; below this triggers monitor [0.0, 1.0]
float64 min_confidence_threshold
