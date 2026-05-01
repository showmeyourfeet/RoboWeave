"""Simulation system launch — no real hardware, mock backends.

Suitable for MVP-0 (simulation minimal loop) testing.
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        # Safety Supervisor
        Node(
            package='roboweave_safety',
            executable='safety_supervisor',
            name='safety_supervisor',
            output='screen',
        ),

        # Control with sim driver
        Node(
            package='roboweave_control',
            executable='control_node',
            name='control_node',
            output='screen',
        ),

        # Runtime
        Node(
            package='roboweave_runtime',
            executable='runtime_node',
            name='runtime_node',
            output='screen',
        ),

        # Data collection
        Node(
            package='roboweave_data',
            executable='data_node',
            name='data_node',
            output='screen',
        ),
    ])
