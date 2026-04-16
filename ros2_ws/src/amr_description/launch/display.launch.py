from launch import LaunchDescription
from launch_ros.actions import Node
import os

def generate_launch_description():

    urdf_file = os.path.join(
        os.getenv('HOME'),
        'test_ros/ros2_ws/src/amr_description/urdf/robot.urdf'
    )

    return LaunchDescription([

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            arguments=[urdf_file],
            output='screen'
        ),

        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            output='screen'
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            output='screen'
        )
    ])
