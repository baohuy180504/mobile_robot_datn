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

    # ---------------------------------------------------------
    # 2. NODE OCTOMAP 3D (Xây Voxel từ mốc 2D + Camera)
    # ---------------------------------------------------------
    octomap_server_node = Node(
        package='octomap_server',
        executable='octomap_server_node',
        name='octomap_server',
        output='screen',
        parameters=[{
            'resolution': 0.05,             # Khớp với độ phân giải của bản đồ 2D
            'frame_id': 'map',              # Mượn hệ tọa độ gốc do SLAM 2D sinh ra
            'base_frame_id': 'base_footprint',
            'sensor_model.max_range': 4.0,  # Khoảng cách đo của Camera Astra
            'pointcloud_min_z': 0.1,        # Lọc sàn nhà
            'pointcloud_max_z': 1.5,        # Lọc trần nhà
            'occupancy_min_z': 0.1,
            'occupancy_max_z': 1.5,
            'latch': True                   
        }],
        remappings=[
            # Trỏ đúng vào luồng PointCloud 3D của Camera Astra
            ('cloud_in', '/camera/depth/points'), 
        ]
    )

    return LaunchDescription([
        slam_toolbox_node,
        octomap_server_node
    ])