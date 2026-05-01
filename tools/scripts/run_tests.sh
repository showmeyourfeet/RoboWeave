#!/bin/bash
# Run all RoboWeave tests
set -e

PYTHON=".venv/bin/python"

echo "=== RoboWeave Test Suite ==="

# Check venv exists
if [ ! -f "$PYTHON" ]; then
    echo "ERROR: .venv not found. Run tools/scripts/setup_workspace.sh first."
    exit 1
fi

FAILED=0

run_test() {
    local pkg=$1
    local dir=$2
    echo ""
    echo "--- Testing $pkg ---"
    if [ -d "$dir/tests" ]; then
        $PYTHON -m pytest "$dir/tests/" -x -q --tb=short 2>&1 || FAILED=1
    else
        echo "  (no tests directory)"
    fi
}

# Test each package
run_test "roboweave_interfaces" "roboweave_interfaces"
run_test "roboweave_control" "roboweave_control"
run_test "roboweave_safety" "roboweave_safety"
run_test "roboweave_runtime" "roboweave_runtime"
run_test "roboweave_perception" "roboweave_perception"
run_test "roboweave_planning" "roboweave_planning"
run_test "roboweave_data" "roboweave_data"
run_test "roboweave_cloud_agent" "roboweave_cloud_agent"
run_test "roboweave_vla" "roboweave_vla"

echo ""
if [ $FAILED -eq 0 ]; then
    echo "=== ALL TESTS PASSED ==="
else
    echo "=== SOME TESTS FAILED ==="
    exit 1
fi
