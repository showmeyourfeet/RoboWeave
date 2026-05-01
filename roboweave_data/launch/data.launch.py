"""ROS2 launch file for roboweave_data."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for the data node."""
    # Declare launch arguments
    data_params_arg = DeclareLaunchArgument(
        "data_params_path",
        default_value="",
        description="Path to data_params.yaml configuration file",
    )
    storage_path_arg = DeclareLaunchArgument(
        "storage_path",
        default_value="/data/roboweave/episodes",
        description="Base directory for episode data storage",
    )
    frame_rate_arg = DeclareLaunchArgument(
        "frame_rate_hz",
        default_value="10.0",
        description="Frame capture rate in Hz",
    )

    # Data node
    data_node = Node(
        package="roboweave_data",
        executable="data_node",
        name="data_node",
        parameters=[
            {
                "data_params_path": LaunchConfiguration("data_params_path"),
                "storage_path": LaunchConfiguration("storage_path"),
                "frame_rate_hz": LaunchConfiguration("frame_rate_hz"),
            }
        ],
        output="screen",
    )

    return LaunchDescription([
        data_params_arg,
        storage_path_arg,
        frame_rate_arg,
        data_node,
    ])
