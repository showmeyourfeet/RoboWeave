# Schema version
string schema_version

# URI locating the trajectory
string uri

# Capture timestamp (seconds)
float64 timestamp

# TF frame
string frame_id

# Expiry timestamp; 0.0 = no expiry
float64 valid_until

# Producing module
string source_module

# Number of waypoints in the trajectory
uint32 num_points

# Total duration of the trajectory in seconds
float64 duration_sec

# Arm this trajectory is for
string arm_id
