import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # ---------------------------------------------------------
    # 1. NODE SLAM 2D (Tạo bản đồ gầm xe bằng Lidar)
    # ---------------------------------------------------------
    # Lưu ý: Thay file 'mapper_params_online_async.yaml' bằng file cấu hình slam_toolbox của bạn nếu cần
    slam_toolbox_node = Node(
        parameters=[
            get_package_share_directory("amr_slam") + '/config/mapper_params_online_async.yaml',
            {'use_sim_time': False}
        ],
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen'
    )

    # THÊM MỚI: Node Van Giảm Áp (Bóp PointCloud từ 21Hz xuống 3Hz)
    throttle_node = Node(
        package='topic_tools',
        executable='throttle',
        name='pointcloud_throttle',
        # Tham số: [lệnh, topic_gốc, tần_số_mong_muốn, topic_mới]
        arguments=['messages', '/camera/depth/points', '3.0', '/camera/depth/points_throttled'],
        output='screen'
    )

    # ---------------------------------------------------------
    # 2. NODE OCTOMAP 3D (Xây Voxel từ mốc 2D + Camera)
    # ---------------------------------------------------------
    octomap_server_node = Node(
        package='octomap_server',
        executable='octomap_server_node',
        name='octomap_server',
        output='screen',
        parameters=[{
            'resolution': 0.08,             # Khớp với độ phân giải của bản đồ 2D
            'frame_id': 'odom',              # Mượn hệ tọa độ gốc do SLAM 2D sinh ra
            'base_frame_id': 'base_footprint',
            'sensor_model.max_range': 3.0,  # Khoảng cách đo của Camera Astra
            'pointcloud_min_z': 0.2,        # Lọc sàn nhà
            'pointcloud_max_z': 1.5,        # Lọc trần nhà
            'occupancy_min_z': 0.2,
            'occupancy_max_z': 1.5,
            # 2. Làm cho Octomap "khó tính" hơn với nhiễu
            'sensor_model.hit': 0.85,   # Mặc định là 0.7. Nâng lên 0.85: Phải thấy vật thể rất nhiều lần mới dám vẽ khối 3D.
            'sensor_model.miss': 0.2,   # Mặc định là 0.4. Giảm xuống 0.2: Chỉ cần không thấy vật thể 1 vài lần là xóa ngay khối 3D (xóa vệt nhiễu rất nhanh).
            'latch': True                   
        }],
        remappings=[
            ('cloud_in', '/camera/depth/points'),
            # ĐÃ THÊM: Đổi tên topic bản đồ chiếu 2D của Octomap thành tên vô nghĩa 
            # để tránh đụng độ với /map của SLAM Toolbox trong RViz2
            ('projected_map', '/octomap_dummy_2d_map')
        ]
    )

    return LaunchDescription([
        throttle_node,
        slam_toolbox_node,
        octomap_server_node
    ])
