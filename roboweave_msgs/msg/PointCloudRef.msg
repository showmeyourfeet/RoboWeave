# Schema version
string schema_version

# URI locating the point cloud
string uri

# Capture timestamp (seconds)
float64 timestamp

# TF frame
string frame_id

# Expiry timestamp; 0.0 = no expiry
float64 valid_until

# Producing module
string source_module

# Number of points in the cloud
uint32 num_points

# Whether the cloud includes per-point color
bool has_color

# Whether the cloud includes per-point normals
bool has_normals

# Storage format: "ply" | "pcd" | "ros_pc2"
string format
