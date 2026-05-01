# Whether the target pose is reachable
bool reachable

# Failure code if not reachable (e.g. "IK_NO_SOLUTION", "IK_JOINT_LIMIT")
string failure_code

# IK joint solution (empty if not reachable)
float64[] ik_solution

# Manipulability measure at the solution [0.0, 1.0]
float64 manipulability
