"""Launch file for the RoboWeave runtime node."""

import os

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "config", "runtime_params.yaml"
    )

    return LaunchDescription([
        Node(
            package="roboweave_runtime",
            executable="runtime_node",
            name="roboweave_runtime",
            parameters=[config_path],
            output="screen",
        ),
    ])
