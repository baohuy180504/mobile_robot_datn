import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    pkg_amr_description = get_package_share_directory('amr_description')
    pkg_amr_slam = get_package_share_directory('amr_slam')
    pkg_amr_nav = get_package_share_directory('amr_navigation')
    pkg_nav2 = get_package_share_directory('nav2_bringup')

    nav2_params_file = os.path.join(pkg_amr_nav, 'config', 'nav2_params_fusion.yaml')
    rviz_config_dir = os.path.join(pkg_amr_slam, 'rviz', 'view_vslam_teleop.rviz')

    # 1. Khởi động Gazebo & Phần cứng
    bringup_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_amr_description, 'launch', 'gazebo.launch.py'))
    )

    # 2. Khởi động Bộ não Fusion (RTAB-Map lấy cả Scan và Depth)
    fusion_slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_amr_slam, 'launch', 'fusion_slam.launch.py'))
    )

    # 3. Khởi động Nav2 (Chỉ để lấy Costmap né vật cản, hỗ trợ nếu bạn dùng Nav Goal)
    nav = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_nav2, 'launch', 'navigation_launch.py')),
        launch_arguments={'use_sim_time': use_sim_time, 'params_file': nav2_params_file}.items()
    )

    # 4. Octomap Server: Nén đám mây điểm thành Voxel 3D
    octomap_node = Node(
        package='octomap_server',
        executable='octomap_server_node',
        name='octomap_server',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'resolution': 0.05,
            'frame_id': 'map', 
            'base_frame_id': 'base_footprint',
            'sensor_model/max_range': 4.0,
            'occupancy_min_z': 0.1, 
            'occupancy_max_z': 2.0,
        }],
        remappings=[
            ('cloud_in', '/rtabmap/cloud_map')
        ]
    )

    # 5. Khởi chạy RViz2
    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_dir],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen'
    )

    return LaunchDescription([
        bringup_sim,
        fusion_slam,
        nav,
        octomap_node,
        rviz2_node
    ])