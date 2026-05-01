#!/bin/bash
set -e

# Source ROS2
source /opt/ros/jazzy/setup.bash

# Source local workspace if built
if [ -f /roboweave_ws/install/setup.bash ]; then
    source /roboweave_ws/install/setup.bash
fi

# Activate venv
source /roboweave_ws/.venv/bin/activate

exec "$@"
