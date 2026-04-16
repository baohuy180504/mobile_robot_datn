import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # Lấy đường dẫn các package
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    
    # TRỎ ĐẾN FILE MAP VỪA LƯU
    map_file = os.path.join(get_package_share_directory('amr_slam'), 'maps', 'my_perfect_map.yaml') 
    params_file = os.path.join(get_package_share_directory('amr_navigation'), 'config', 'nav2_params.yaml')

    # Gọi bộ khung Nav2
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')),
        launch_arguments={
            'map': map_file,
            'params_file': params_file,
            'use_sim_time': 'false', 
        }.items()
    )

    # # Khởi chạy RViz2 với giao diện chuyên dụng cho Nav2
    # rviz_node = Node(
    #     package='rviz2',
    #     executable='rviz2',
    #     name='rviz2',
    #     arguments=['-d', os.path.join(nav2_bringup_dir, 'rviz', 'nav2_default_view.rviz')],
    #     parameters=[{'use_sim_time': False}]
    # )

    return LaunchDescription([nav2_launch]) #, rviz_node])