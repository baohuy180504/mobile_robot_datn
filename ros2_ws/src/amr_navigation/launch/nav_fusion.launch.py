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

    depth_cloud_filter = Node(
        package='amr_pointcloud_filter',
        executable='depth_cloud_filter',
        name='depth_cloud_filter',
        output='screen',
        parameters=[{
            'input_topic': '/camera/depth/points',

            'nav_output_topic': '/camera/depth/points_filtered',
            'nav_publish_hz': 5.0,
            'nav_leaf_size': 0.06,
            'nav_pixel_step': 3,

            'octomap_output_topic': '/octomap_cloud',
            'octomap_publish_hz': 2.0,
            'octomap_leaf_size': 0.08,
            'octomap_pixel_step': 3,

            # Dùng crop rộng trước để đảm bảo có dữ liệu 3D
            'min_depth': 0.25,
            'max_depth': 3.20,

            'min_x': -2.00,
            'max_x': 2.00,

            'min_y': -1.50,
            'max_y': 1.50,

            'restamp': True,
            'output_frame_id': '',
            'log_debug': False,
            'use_sim_time': False,
        }]
    )

    static_octomap_server = Node(
        package='octomap_server',
        executable='octomap_server_node',
        name='static_octomap_server',
        namespace='static_octomap',
        output='screen',
        remappings=[
            ('projected_map', '/static_map3d'),
            ('octomap_binary', '/static_octomap_binary'),
            ('octomap_full', '/static_octomap_full'),
            ('occupied_cells_vis_array', '/static_occupied_cells_vis_array'),
        ],
        parameters=[{
            'use_sim_time': False,
            'frame_id': 'map',
            'base_frame_id': 'base_footprint',
            'resolution': 0.05,
            'octomap_path': LaunchConfiguration('octomap'),

            'pointcloud_min_z': 0.05,
            'pointcloud_max_z': 2.00,
            'occupancy_min_z': 0.05,
            'occupancy_max_z': 2.00,

            # Không cần cloud live cho static map.
            'filter_ground': False,
            'compress_map': True,
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
        '╔═══════════════════════════════════════════════════════════╗\n',
        '║ AMR NAV FUSION - LIVE OCTOMAP                             ║\n',
        '╠═══════════════════════════════════════════════════════════╣\n',
        '║ Nav2       : giữ thông số MPPI + VoxelLayer hiện tại      ║\n',
        '║ Cloud relay: /camera/depth/points -> /octomap_cloud       ║\n',
        '║ OctoMap    : load .bt + update live từ /octomap_cloud     ║\n',
        '║ RViz       : ưu tiên xem /occupied_cells_vis_array        ║\n',
        '╚═══════════════════════════════════════════════════════════╝\n',
    ])

    return LaunchDescription([
        map_arg,
        octomap_arg,
        params_arg,
        use_sim_time_arg,
        autostart_arg,
        log_info,
        depth_cloud_filter,
        #octomap_server,
        static_octomap_server,
        nav2_launch,
    ])
