import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # Lấy đường dẫn các package
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    amr_slam_dir = get_package_share_directory('amr_slam')
    amr_nav_dir = get_package_share_directory('amr_navigation')

    # Nếu chạy thẳng không truyền tham số, nó sẽ dùng my_perfect_map.yaml
    default_map_file = os.path.join(amr_slam_dir, 'maps', 'map1.yaml')

    map_arg = DeclareLaunchArgument(
        'map',
        default_value=default_map_file,
        description='Full path to map yaml file to load'
    )

    # Lấy giá trị map từ Terminal (do script truyền vào)
    map_config = LaunchConfiguration('map')
    # Trỏ đến file cấu hình
    params_file = os.path.join(amr_nav_dir, 'config', 'nav2_params_MPPI.yaml')
    # Gọi bộ khung Nav2
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')),
        launch_arguments={
            'map': map_config,
            'params_file': params_file,
            'use_sim_time': 'false', 
            'autostart': 'true'
        }.items()
    )

    return LaunchDescription([
        map_arg,
        nav2_launch
    ])