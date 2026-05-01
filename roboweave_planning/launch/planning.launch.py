"""ROS2 launch file for roboweave_planning."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for the planning node."""
    # Declare launch arguments
    planning_params_arg = DeclareLaunchArgument(
        "planning_params_path",
        default_value="",
        description="Path to planning parameters YAML file",
    )
    planning_backends_arg = DeclareLaunchArgument(
        "planning_backends_path",
        default_value="",
        description="Path to planning backends YAML file",
    )
    arm_id_arg = DeclareLaunchArgument(
        "arm_id",
        default_value="default_arm",
        description="Arm ID for planning",
    )

    # Planning node
    planning_node = Node(
        package="roboweave_planning",
        executable="planning_node",
        name="planning_node",
        parameters=[
            {
                "planning_params_path": LaunchConfiguration(
                    "planning_params_path"
                ),
                "planning_backends_path": LaunchConfiguration(
                    "planning_backends_path"
                ),
                "arm_id": LaunchConfiguration("arm_id"),
            }
        ],
        output="screen",
    )

    return LaunchDescription([
        planning_params_arg,
        planning_backends_arg,
        arm_id_arg,
        planning_node,
    ])
