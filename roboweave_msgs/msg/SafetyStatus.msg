# Standard header with timestamp
std_msgs/Header header

# Current safety level: "normal" | "warning" | "critical" | "emergency_stop"
string safety_level

# Whether emergency stop is currently active
bool e_stop_active

# Whether emergency stop is latched (requires manual release)
bool e_stop_latched

# Whether a collision has been detected
bool collision_detected

# Minimum distance to nearest human in meters
float32 min_human_distance

# List of currently active safety violations
string[] active_violations

# List of currently active safe zone IDs
string[] active_safe_zones

# Timestamp of last safety supervisor heartbeat (seconds)
float64 last_heartbeat
