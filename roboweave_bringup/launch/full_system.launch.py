"""Full system launch file for RoboWeave.

Launches all subsystems: control, safety, runtime, perception, planning, vla, data.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import os


def generate_launch_description():
    # Declare common arguments
    profile_arg = DeclareLaunchArgument(
        'profile', default_value='sim',
        description='Configuration profile: sim, lab_robot, demo, production'
    )
    hardware_config_arg = DeclareLaunchArgument(
        'hardware_config_path', default_value='',
        description='Path to hardware configuration YAML'
    )

    return LaunchDescription([
        profile_arg,
        hardware_config_arg,

        # Safety Supervisor (independent process — launches first)
        Node(
            package='roboweave_safety',
            executable='safety_supervisor',
            name='safety_supervisor',
            output='screen',
        ),

        # Control Node
        Node(
            package='roboweave_control',
            executable='control_node',
            name='control_node',
            output='screen',
            parameters=[{
                'hardware_config_path': LaunchConfiguration('hardware_config_path'),
            }],
        ),

        # Runtime Node
        Node(
            package='roboweave_runtime',
            executable='runtime_node',
            name='runtime_node',
            output='screen',
        ),

        # Perception Node
        Node(
            package='roboweave_perception',
            executable='perception_node',
            name='perception_node',
            output='screen',
        ),

        # Planning Node
        Node(
            package='roboweave_planning',
            executable='planning_node',
            name='planning_node',
            output='screen',
        ),

        # VLA Node
        Node(
            package='roboweave_vla',
            executable='vla_node',
            name='vla_node',
            output='screen',
        ),

        # Data Node
        Node(
            package='roboweave_data',
            executable='data_node',
            name='data_node',
            output='screen',
        ),
    ])
