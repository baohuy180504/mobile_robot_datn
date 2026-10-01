import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


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

    # --- Benchmark args (chỉ dùng khi đo hiệu năng cho paper) ---
    timing_csv_arg = DeclareLaunchArgument(
        'timing_csv',
        default_value='',
        description='Đường dẫn CSV để height_risk_projector ghi thời gian mỗi frame. '
                    'Để trống = tắt benchmark.'
    )

    # QUÉT N BẰNG THAM SỐ NÀY, không phải pixel_step.
    # Lý do: pipeline là pixel_step -> voxel grid. Voxel grid áp trần mật độ ở
    # 1 điểm/voxel, nên đổi pixel_step gần như không đổi số điểm ĐẦU RA (đã kiểm
    # chứng: N chỉ nhúc nhích 1.7k -> 2.1k). leaf_size mới quyết định số voxel.
    #
    # CẢNH BÁO: leaf_size đổi thì mật độ điểm/cell đổi -> tanh(N/density_ref_count)
    # đổi theo -> GIÁ TRỊ RISK KHÁC. Chỉ dùng để đo THỜI GIAN. Chạy vận hành
    # bình thường phải để 0.06 (giá trị density_ref_count=3.0 được tinh chỉnh theo nó).
    leaf_size_arg = DeclareLaunchArgument(
        'leaf_size',
        default_value='0.06',
        description='nav_leaf_size của depth_cloud_filter (m). Quét 0.06/0.04/0.02 để '
                    'đổi số điểm đầu vào N cho hình time-vs-points. Vận hành: giữ 0.06.'
    )

    pixel_step_arg = DeclareLaunchArgument(
        'pixel_step',
        default_value='3',
        description='nav_pixel_step của depth_cloud_filter (lấy mẫu thưa trên ảnh). '
                    'KHÔNG dùng để quét N (bị voxel grid làm bão hoà) — dùng leaf_size.'
    )

    debug_cloud_arg = DeclareLaunchArgument(
        'debug_cloud',
        default_value='true',
        description='Publish cloud XYZI /height_obstacles_cloud (chỉ để RViz). '
                    'Đặt false khi benchmark để không tính vào chi phí thuật toán.'
    )

    # E1 công bằng: thu hẹp crop của depth_cloud_filter để CẢ HAI layer nhận
    # cùng một tập điểm. Mặc định (2.0/3.2) là dải rộng dùng khi vận hành;
    # khi so sánh thuật toán, đặt half_width=0.80 và max_depth=2.40 để khớp
    # ROI của GHRF (y +-0.75 m, x tới 2.50 m; camera đặt tại x=0.22 m).
    crop_half_width_arg = DeclareLaunchArgument(
        'crop_half_width',
        default_value='2.00',
        description='min_x/max_x của depth_cloud_filter (m, ngang trong camera frame).'
    )

    crop_max_depth_arg = DeclareLaunchArgument(
        'crop_max_depth',
        default_value='3.20',
        description='max_depth của depth_cloud_filter (m, theo trục quang).'
    )

    # E4: quét sigma_depth_k để đo tác dụng của adaptive sigma.
    # sigma_k:=0.0 -> sigma phẳng = sigma_base (ablation), sigma_k:=0.03 -> mặc định.
    sigma_k_arg = DeclareLaunchArgument(
        'sigma_k',
        default_value='0.03',
        description='sigma_depth_k của GHRF. Đặt 0.0 để tắt adaptive sigma (ablation E4).'
    )

    # Chỉ GHRF mới cần height_risk_projector. VoxelLayer/STVL đọc thẳng
    # /camera/depth/points_filtered nên KHÔNG cần node này.
    # BẮT BUỘC đặt false khi test VoxelLayer/STVL, nếu không CPU của GHRF
    # bị tính vào cả 3 cấu hình -> so sánh vô nghĩa.
    run_projector_arg = DeclareLaunchArgument(
        'run_projector',
        default_value='true',
        description='Chạy node height_risk_projector (chỉ GHRF cần). '
                    'Đặt false khi test VoxelLayer/STVL.'
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
            'nav_leaf_size': ParameterValue(
                LaunchConfiguration('leaf_size'), value_type=float),
            'nav_pixel_step': ParameterValue(
                LaunchConfiguration('pixel_step'), value_type=int),

            'octomap_output_topic': '/octomap_cloud',
            'octomap_publish_hz': 2.0,
            'octomap_leaf_size': 0.08,
            'octomap_pixel_step': 3,

            # Dùng crop rộng trước để đảm bảo có dữ liệu 3D
            'min_depth': 0.25,
            'max_depth': ParameterValue(
                LaunchConfiguration('crop_max_depth'), value_type=float),

            # min_x = -crop_half_width, max_x = +crop_half_width
            'min_x': ParameterValue(
                PythonExpression(['-1.0 * ', LaunchConfiguration('crop_half_width')]),
                value_type=float),
            'max_x': ParameterValue(
                LaunchConfiguration('crop_half_width'), value_type=float),

            'min_y': -1.50,
            'max_y': 1.50,

            'restamp': False,
            'output_frame_id': '',
            'log_debug': False,
            'use_sim_time': False,
        }]
    )


    height_risk_projector = Node(
        package='amr_pointcloud_filter',
        executable='height_risk_projector',
        name='height_risk_projector',
        condition=IfCondition(LaunchConfiguration('run_projector')),
        output='screen',
        parameters=[{
            # Nhận cloud đã lọc nhẹ từ depth_cloud_filter.
            'input_topic': '/camera/depth/points_filtered',

            # Cloud XYZI chỉ để RViz/debug (intensity = risk*100).
            'output_cloud_topic': '/height_obstacles_cloud',
            # OccupancyGrid risk [0-100] mà ghrf_layer trong Nav2 đọc.
            'risk_grid_topic': '/ghrf_risk_grid',

            # Bắt buộc transform về base_footprint để z là chiều cao so với robot.
            'target_frame': 'base_footprint',
            'use_latest_tf': False,
            'tf_timeout_s': 0.15,

            # ROI phía trước robot, chỉnh sau khi xem RViz.
            'min_x': 0.10,
            'max_x': 2.50,
            'min_y': -0.75,
            'max_y': 0.75,

            # Vùng chiều cao cần bảo vệ (dùng cho tâm Gaussian z_center = (min+max)/2 = 0.75 m).
            # Đã tinh chỉnh thực nghiệm: 0.30 nằm ngay trên tầm LiDAR (0.2657 m),
            # 1.20 là trần tầm phủ của camera. z_center 0.75 m rơi đúng vào mặt bàn/ghế.
            'robot_min_z': 0.30,
            'robot_max_z': 1.20,

            # --- Tham số GHRF (Gaussian Height Risk Field) ---
            # sigma(d) = sigma_base + sigma_depth_k * d  (d = khoảng cách Euclid tới camera)
            'sigma_base': 0.05,            # m, sigma tại khoảng cách ~0
            'sigma_depth_k': ParameterValue(
                LaunchConfiguration('sigma_k'), value_type=float),
            'gaussian_cutoff_sigma': 3.5,  # bỏ điểm lệch quá 3.5*sigma khỏi z_center
            'density_ref_count': 3.0,      # N_ref trong tanh(count/N_ref)
            # Frame để tính depth cho adaptive sigma (origin camera). Fail-open về sigma_base nếu TF hỏng.
            'camera_frame_id': 'camera_depth_optical_frame',
            # Relabel grid sang frame này bằng 1 TF lookup trước khi publish (khớp global_frame local_costmap).
            'grid_publish_frame': 'odom',
            'risk_prune_epsilon': 0.05,    # xóa cell khi risk hiệu dụng (đã decay) < ngưỡng này

            # Lọc nhiễu theo ô 2D + giữ vật cản ngắn hạn.
            'grid_resolution': 0.05,
            'min_points_per_cell': 2,
            'memory_decay_time': 0.8,      # tau trong risk_eff = risk * exp(-age/tau)
            'publish_hz': 5.0,

            # Giới hạn số điểm xử lý mỗi frame để tránh tải Jetson quá cao.
            'max_input_points': 60000,
            'publish_risk_grid': True,

            # --- Benchmark (truyền từ dòng lệnh, xem DeclareLaunchArgument ở trên) ---
            'timing_csv_path': ParameterValue(
                LaunchConfiguration('timing_csv'), value_type=str),
            'publish_debug_cloud': ParameterValue(
                LaunchConfiguration('debug_cloud'), value_type=bool),

            'log_debug': True,
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
        '║ Nav2       : MPPI + GHRF layer (local_costmap)           ║\n',
        '║ GHRF       : /ghrf_risk_grid -> ghrf_layer (né vật cao)  ║\n',
        '║ OctoMap    : load .bt static (localization tham chiếu)   ║\n',
        '║ RViz       : ưu tiên xem /occupied_cells_vis_array        ║\n',
        '╚═══════════════════════════════════════════════════════════╝\n',
    ])

    return LaunchDescription([
        map_arg,
        octomap_arg,
        params_arg,
        use_sim_time_arg,
        autostart_arg,
        timing_csv_arg,
        leaf_size_arg,
        pixel_step_arg,
        debug_cloud_arg,
        run_projector_arg,
        sigma_k_arg,
        crop_half_width_arg,
        crop_max_depth_arg,
        log_info,
        depth_cloud_filter,
        height_risk_projector,
        #octomap_server,
        static_octomap_server,
        nav2_launch,
    ])