# RoboWeave Development Environment
# Base: ROS2 Humble on Ubuntu 22.04
FROM ros:jazzy-ros-base-noble

LABEL maintainer="RoboWeave Team <dev@roboweave.dev>"
LABEL description="RoboWeave development environment with Python 3.10+, ROS2 Jazzy, and all dependencies"

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    curl \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Create workspace
WORKDIR /roboweave_ws

# Copy all packages
COPY roboweave_interfaces/ roboweave_interfaces/
COPY roboweave_msgs/ roboweave_msgs/
COPY roboweave_control/ roboweave_control/
COPY roboweave_safety/ roboweave_safety/
COPY roboweave_runtime/ roboweave_runtime/
COPY roboweave_perception/ roboweave_perception/
COPY roboweave_planning/ roboweave_planning/
COPY roboweave_data/ roboweave_data/
COPY roboweave_cloud_agent/ roboweave_cloud_agent/
COPY roboweave_vla/ roboweave_vla/
COPY roboweave_bringup/ roboweave_bringup/
COPY docs/ docs/
COPY tools/ tools/

# Create venv and install Python packages
RUN uv venv .venv --python python3 && \
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

# Build ROS2 packages (roboweave_msgs)
SHELL ["/bin/bash", "-c"]
RUN source /opt/ros/jazzy/setup.bash && \
    colcon build --packages-select roboweave_msgs || true

# Set up entrypoint
COPY tools/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
