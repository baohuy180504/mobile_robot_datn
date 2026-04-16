import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    pkg_amr_description = get_package_share_directory('amr_description')
    pkg_amr_slam = get_package_share_directory('amr_slam')
    pkg_amr_nav = get_package_share_directory('amr_navigation')

    # 1. Chạy Gazebo
    bringup_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_amr_description, 'launch', 'gazebo.launch.py'))
    )

    # 2. Chạy Não bộ RTAB-Map (File vslam.launch.py mà chúng ta vừa tối ưu)
    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_amr_slam, 'launch', 'vslam.launch.py'))
    )

    return LaunchDescription([
        bringup_sim,
        slam
    ])