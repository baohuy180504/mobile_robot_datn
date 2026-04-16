import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # Lấy đường dẫn file cấu hình
    slam_config_file = os.path.join(
        get_package_share_directory('amr_slam'),
        'config',
        'mapper_params_online_async.yaml'
    )

    # Khởi chạy Node SLAM Toolbox
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            slam_config_file,
            {'use_sim_time': False}  # Đảm bảo sử dụng thời gian thực, không phải thời gian mô phỏng
        ]
    )

    return LaunchDescription([slam_toolbox_node])