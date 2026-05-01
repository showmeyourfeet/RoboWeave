"""Launch file for the roboweave_safety supervisor node."""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "..", "config"
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "safety_params_file",
            default_value=os.path.join(pkg_share, "safety_params.yaml"),
            description="Path to safety parameters YAML file",
        ),
        DeclareLaunchArgument(
            "workspace_limits_file",
            default_value=os.path.join(pkg_share, "workspace_limits.yaml"),
            description="Path to workspace limits YAML file",
        ),
        DeclareLaunchArgument(
            "publish_rate_hz",
            default_value="10.0",
            description="Safety status publish rate in Hz",
        ),
        DeclareLaunchArgument(
            "watchdog_timeout_sec",
            default_value="0.5",
            description="Robot state watchdog timeout in seconds",
        ),
        Node(
            package="roboweave_safety",
            executable="safety_supervisor",
            name="safety_supervisor",
            parameters=[{
                "safety_params_file": LaunchConfiguration("safety_params_file"),
                "workspace_limits_file": LaunchConfiguration("workspace_limits_file"),
                "publish_rate_hz": LaunchConfiguration("publish_rate_hz"),
                "watchdog_timeout_sec": LaunchConfiguration("watchdog_timeout_sec"),
            }],
            output="screen",
        ),
    ])
