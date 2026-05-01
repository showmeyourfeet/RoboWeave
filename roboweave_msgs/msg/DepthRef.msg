# Schema version
string schema_version

# URI locating the depth image
string uri

# Capture timestamp (seconds)
float64 timestamp

# TF frame
string frame_id

# Expiry timestamp; 0.0 = no expiry
float64 valid_until

# Producing module
string source_module

# Depth encoding: "16UC1" | "32FC1"
string encoding

# Image width in pixels
uint32 width

# Image height in pixels
uint32 height

# Depth unit: "mm" | "m"
string depth_unit
