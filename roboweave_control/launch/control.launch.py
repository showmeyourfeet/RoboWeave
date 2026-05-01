"""ROS2 launch file for roboweave_control."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for the control node."""
    # Declare launch arguments
    hardware_config_arg = DeclareLaunchArgument(
        "hardware_config_path",
        default_value="",
        description="Path to hardware configuration YAML file",
    )
    publish_rate_arg = DeclareLaunchArgument(
        "publish_rate_hz",
        default_value="50.0",
        description="Robot state publish rate in Hz",
    )
    velocity_scaling_arg = DeclareLaunchArgument(
        "default_velocity_scaling",
        default_value="0.5",
        description="Default velocity scaling for trajectory execution",
    )

    # Control node
    control_node = Node(
        package="roboweave_control",
        executable="control_node",
        name="control_node",
        parameters=[
            {
                "hardware_config_path": LaunchConfiguration("hardware_config_path"),
                "publish_rate_hz": LaunchConfiguration("publish_rate_hz"),
                "default_velocity_scaling": LaunchConfiguration("default_velocity_scaling"),
            }
        ],
        output="screen",
    )

    return LaunchDescription([
        hardware_config_arg,
        publish_rate_arg,
        velocity_scaling_arg,
        control_node,
    ])
