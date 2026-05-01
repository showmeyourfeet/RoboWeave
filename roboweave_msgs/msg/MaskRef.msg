# Schema version
string schema_version

# URI locating the mask
string uri

# Capture timestamp (seconds)
float64 timestamp

# TF frame
string frame_id

# Expiry timestamp; 0.0 = no expiry
float64 valid_until

# Producing module
string source_module

# ID of the object this mask belongs to
string object_id

# Confidence score of the mask [0.0, 1.0]
float64 mask_confidence

# Number of pixels in the mask
uint32 pixel_count
