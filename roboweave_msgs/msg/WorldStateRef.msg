# Schema version
string schema_version

# URI locating the world state snapshot
string uri

# Capture timestamp (seconds)
float64 timestamp

# TF frame
string frame_id

# Expiry timestamp; 0.0 = no expiry
float64 valid_until

# Producing module
string source_module

# Number of tracked objects in the snapshot
uint32 num_objects

# Robot identifier
string robot_id
