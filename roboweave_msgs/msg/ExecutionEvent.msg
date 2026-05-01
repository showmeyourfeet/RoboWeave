# Unique event identifier
string event_id

# Associated task identifier
string task_id

# Associated plan node identifier (empty if task-level event)
string node_id

# Event type: "skill_started" | "skill_succeeded" | "skill_failed" | "skill_timeout"
#   | "precondition_failed" | "postcondition_failed" | "safety_triggered"
#   | "recovery_started" | "recovery_succeeded" | "recovery_failed"
#   | "task_started" | "task_completed" | "task_failed"
string event_type

# Error code if applicable (e.g. "PER_NO_OBJECT_FOUND")
string failure_code

# Severity: "info" | "warning" | "error" | "critical"
string severity

# Human-readable event message
string message

# List of candidate recovery action names
string[] recovery_candidates

# Event timestamp (seconds, epoch)
float64 timestamp
