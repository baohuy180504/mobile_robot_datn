import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node

def generate_launch_description():
    desc_pkg = get_package_share_directory('amr_description')
    urdf_file = os.path.join(desc_pkg, 'urdf', 'robot.urdf') # Đã sửa thành robot.urdf theo tên bạn gửi trước đó

    # Đọc nội dung URDF
    with open(urdf_file, 'r') as f:
        robot_description = f.read()

    # 1. Phát tán khung xương (TF Tree)
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description, 'use_sim_time': False}]
    )

    # 2. Đánh thức LiDAR 2D (RPLidar / SLLidar)
    lidar_node = Node(
        package='sllidar_ros2',
        executable='sllidar_node',
        name='sllidar_node',
        parameters=[{
            'channel_type': 'serial',
            'serial_port': '/dev/rplidar', 
            'serial_baudrate': 115200,
            'frame_id': 'laser_frame',
            'inverted': False,
            'angle_compensate': True,
            'scan_mode': 'Sensitivity',
            # GÓC QUÉT: Đơn vị Radian (3.14159 rad = 180 độ)
            'angle_min': 1.570796, 
            'angle_max': 4.712389
        }],
        output='screen'
    )

    # 3. Giao tiếp với não dưới (Arduino)
    arduino_driver = Node(
        package='amr_control',
        executable='arduino_bridge', 
        name='arduino_bridge',
        output='screen'
    )

    filter_node = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        parameters=[os.path.join(
            get_package_share_directory('amr_bringup'),
            'config', 'box_filter.yaml'
        )],
        remappings=[
            ('scan', '/scan'),
            ('scan_filtered', '/scan_filtered')
        ]
    )

    return LaunchDescription([
        robot_state_publisher,
        lidar_node,
        filter_node,
        arduino_driver
    ])