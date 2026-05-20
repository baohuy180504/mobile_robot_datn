import os
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    desc_pkg = get_package_share_directory('amr_description')
    bringup_pkg = get_package_share_directory('amr_bringup')
    
    urdf_file = os.path.join(desc_pkg, 'urdf', 'robot.urdf')
    with open(urdf_file, 'r') as f:
        robot_description = f.read()

    # ----------------------------------------------------------------
    # 1. Robot State Publisher (TF Tree)
    # ----------------------------------------------------------------
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': False
        }]
    )

    # ----------------------------------------------------------------
    # 2. LiDAR RPLidar A1M8
    # ----------------------------------------------------------------
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
            # Góc 90°→270° = quét 180° phía trước robot
            # 'angle_min': 1.570796,
            # 'angle_max': 4.712389
            'angle_min': -1.570796,
            'angle_max':  1.570796
        }],
        output='screen'
    )

    # ----------------------------------------------------------------
    # 3. Arduino Bridge
    # ----------------------------------------------------------------
    arduino_driver = Node(
        package='amr_control',
        executable='arduino_bridge',
        name='arduino_bridge',
        output='screen'
    )

    # ----------------------------------------------------------------
    # 4. Laser Filter Node
    #
    # Ưu tiên: Dùng file YAML (box_filter.yaml) với format ROS2 đúng.
    # Nếu vẫn crash, comment block YAML và uncomment block INLINE bên dưới.
    # ----------------------------------------------------------------

    # --- CÁCH 1: YAML file (khuyến nghị) ---
    box_filter_config = os.path.join(bringup_pkg, 'config', 'box_filter.yaml')

    filter_node = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        name='scan_to_scan_filter_chain',
        parameters=[box_filter_config],
        remappings=[
            ('scan', '/scan'),
            ('scan_filtered', '/scan_filtered')
        ],
        output='screen'
    )

    return LaunchDescription([
        robot_state_publisher,
        lidar_node,
        filter_node,
        arduino_driver
    ])