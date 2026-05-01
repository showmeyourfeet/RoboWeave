#!/bin/bash
# RoboWeave workspace setup script
set -e

echo "=== RoboWeave Workspace Setup ==="

# Check uv
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Create venv
echo "Creating .venv..."
uv venv .venv --python python3 --clear 2>/dev/null || uv venv .venv --python python3

# Install all packages
echo "Installing packages..."
uv pip install --python .venv/bin/python \
    ./roboweave_interfaces[dev] \
    ./roboweave_control \
    ./roboweave_safety \
    ./roboweave_runtime \
    ./roboweave_perception \
    ./roboweave_planning \
    ./roboweave_data \
    ./roboweave_cloud_agent \
    ./roboweave_vla

echo ""
echo "=== Setup Complete ==="
echo "Activate with: source .venv/bin/activate"
echo "Run tests with: .venv/bin/python -m pytest"
