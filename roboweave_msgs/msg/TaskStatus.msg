# Task identifier
string task_id

# Current status: "pending" | "running" | "paused" | "succeeded" | "failed" | "cancelled"
string status

# Execution progress [0.0, 1.0]
float64 progress

# ID of the plan node currently being executed
string current_node_id

# Failure code if status is "failed" (e.g. "TSK_PRECONDITION_FAILED")
string failure_code

# Human-readable status message
string message
