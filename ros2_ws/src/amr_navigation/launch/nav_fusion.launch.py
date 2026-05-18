import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    amr_nav_dir = get_package_share_directory('amr_navigation')
    amr_slam_dir = get_package_share_directory('amr_slam')

    default_map = os.path.join(amr_slam_dir, 'maps', 'map3.yaml')
    default_octomap = os.path.join(amr_slam_dir, 'maps', 'map3_3d.bt')
    default_params = os.path.join(amr_nav_dir, 'config', 'nav2_params_fusion.yaml')

    map_arg = DeclareLaunchArgument(
        'map',
        default_value=default_map,
        description='Full path to 2D map YAML'
    )

    octomap_arg = DeclareLaunchArgument(
        'octomap',
        default_value=default_octomap,
        description='Full path to saved 3D OctoMap .bt'
    )

    params_arg = DeclareLaunchArgument(
        'params_file',
        default_value=default_params,
        description='Full path to Nav2 fusion parameter file'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation clock'
    )

    autostart_arg = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Autostart Nav2 lifecycle nodes'
    )

    # 3D OctoMap realtime giống logic mô phỏng:
    # - load bản đồ .bt đã lưu
    # - tiếp tục nhận cloud live từ Astra depth camera
    # - publish /octomap_binary, /octomap_full, /occupied_cells_vis_array, /map3d
    octomap_server = Node(
        package='octomap_server',
        executable='octomap_server_node',
        name='octomap_server',
        output='screen',
        remappings=[
            ('cloud_in', '/camera/depth/points'),
            ('projected_map', '/map3d'),
        ],
        parameters=[{
            'use_sim_time': False,
            'frame_id': 'map',
            'base_frame_id': 'base_footprint',
            'resolution': 0.05,
            'octomap_path': LaunchConfiguration('octomap'),

            # Giới hạn chiều cao giống lúc SLAM 3D.
            'pointcloud_min_z': 0.05,
            'pointcloud_max_z': 2.00,
            'occupancy_min_z': 0.05,
            'occupancy_max_z': 2.00,

            # Sensor model giống fusion_slam/mô phỏng.
            'sensor_model.max_range': 4.5,
            'sensor_model.hit': 0.7,
            'sensor_model.miss': 0.4,
            'sensor_model.min': 0.12,
            'sensor_model.max': 0.97,

            # Một số bản octomap_server ROS2 Humble dùng key dạng slash.
            'sensor_model/max_range': 4.5,
            'sensor_model/hit': 0.7,
            'sensor_model/miss': 0.4,
            'sensor_model/min': 0.12,
            'sensor_model/max': 0.97,

            'occupancy_threshold': 0.5,
            'compress_map': True,

            # Nếu vật cao bị loại nhầm, đổi filter_ground:=false khi launch để test riêng.
            # Ở bản mặc định để False để tránh lọc nhầm tấm bìa/người/vật mỏng.
            'filter_ground': False,
        }]
    )

    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map': LaunchConfiguration('map'),
            'params_file': LaunchConfiguration('params_file'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'autostart': LaunchConfiguration('autostart'),
        }.items()
    )

    log_info = LogInfo(msg=[
        '\n',
        '╔════════════════════════════════════════════════════════════╗\n',
        '║ AMR NAV FUSION v15 - LIKE VIDEO                           ║\n',
        '╠════════════════════════════════════════════════════════════╣\n',
        '║ Nav2       : giữ thông số MPPI 2D gốc                     ║\n',
        '║ Costmap    : LiDAR + Astra VoxelLayer                     ║\n',
        '║ OctoMap    : load .bt + update live /camera/depth/points  ║\n',
        '║ 3D topics  : /octomap_binary /occupied_cells_vis_array    ║\n',
        '╚════════════════════════════════════════════════════════════╝\n',
    ])

    return LaunchDescription([
        map_arg,
        octomap_arg,
        params_arg,
        use_sim_time_arg,
        autostart_arg,
        log_info,
        octomap_server,
        nav2_launch,
    ])
