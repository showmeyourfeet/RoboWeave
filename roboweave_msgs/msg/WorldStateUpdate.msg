# Standard header with timestamp
std_msgs/Header header

# Update type: "object_added" | "object_updated" | "object_removed" | "full_refresh"
string update_type

# Object ID affected by this update (empty for full_refresh)
string object_id

# JSON payload with update details (JsonEnvelope format)
string payload_json
