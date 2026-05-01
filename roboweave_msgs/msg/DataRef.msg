# Schema version for forward compatibility
# Valid values: "roboweave.v1"
string schema_version

# URI locating the data (e.g. "rostopic:///...", "shm:///...", "file:///...", "s3://...")
string uri

# Timestamp when the data was captured (seconds, epoch)
float64 timestamp

# TF frame in which the data is expressed
string frame_id

# Expiry timestamp; 0.0 means no expiry
float64 valid_until

# Name of the module that produced this data
string source_module
