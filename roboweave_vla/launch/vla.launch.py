"""ROS2 launch file for roboweave_vla."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for the VLA node."""
    vla_params_arg = DeclareLaunchArgument(
        "vla_params_path",
        default_value="",
        description="Path to vla_params.yaml configuration file",
    )
    vla_registry_arg = DeclareLaunchArgument(
        "vla_skill_registry_path",
        default_value="",
        description="Path to vla_skill_registry.yaml configuration file",
    )

    vla_node = Node(
        package="roboweave_vla",
        executable="vla_node",
        name="vla_node",
        parameters=[
            {
                "vla_params_path": LaunchConfiguration("vla_params_path"),
                "vla_skill_registry_path": LaunchConfiguration(
                    "vla_skill_registry_path"
                ),
            }
        ],
        output="screen",
    )

    return LaunchDescription([
        vla_params_arg,
        vla_registry_arg,
        vla_node,
    ])
