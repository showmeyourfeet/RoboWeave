"""ROS2 launch file for roboweave_perception."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for the perception node."""
    # Declare launch arguments
    perception_params_arg = DeclareLaunchArgument(
        "perception_params_path",
        default_value="",
        description="Path to perception parameters YAML file",
    )
    model_registry_arg = DeclareLaunchArgument(
        "model_registry_path",
        default_value="",
        description="Path to model registry YAML file",
    )
    camera_id_arg = DeclareLaunchArgument(
        "camera_id",
        default_value="default_camera",
        description="Camera ID for perception",
    )

    # Perception node
    perception_node = Node(
        package="roboweave_perception",
        executable="perception_node",
        name="perception_node",
        parameters=[
            {
                "perception_params_path": LaunchConfiguration(
                    "perception_params_path"
                ),
                "model_registry_path": LaunchConfiguration(
                    "model_registry_path"
                ),
                "camera_id": LaunchConfiguration("camera_id"),
            }
        ],
        output="screen",
    )

    return LaunchDescription([
        perception_params_arg,
        model_registry_arg,
        camera_id_arg,
        perception_node,
    ])
