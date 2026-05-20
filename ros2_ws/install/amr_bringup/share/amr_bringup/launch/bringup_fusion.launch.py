"""
bringup_fusion.launch.py — package: amr_bringup

Mục tiêu:
  - Khởi động phần cứng robot, KHÔNG dùng UKF.
  - Arduino bridge là nguồn duy nhất publish /odom và TF odom -> base_footprint.
  - robot_state_publisher publish TF cố định từ URDF.
  - Astra chỉ chạy depth, driver KHÔNG publish TF để tránh trùng TF.
  - TF camera_depth_optical_frame được publish bằng static_transform_publisher.

Chạy:
  ros2 launch amr_bringup bringup_fusion.launch.py
"""

import os
from launch import LaunchDescription
from launch.actions import LogInfo
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    desc_pkg = get_package_share_directory('amr_description')
    bringup_pkg = get_package_share_directory('amr_bringup')

    urdf_file = os.path.join(desc_pkg, 'urdf', 'robot.urdf')
    with open(urdf_file, 'r') as f:
        robot_description = f.read()

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': False,
        }]
    )

    lidar_node = Node(
        package='sllidar_ros2',
        executable='sllidar_node',
        name='sllidar_node',
        output='screen',
        parameters=[{
            'channel_type': 'serial',
            'serial_port': '/dev/rplidar',
            'serial_baudrate': 115200,
            'frame_id': 'laser_frame',
            'inverted': False,
            'angle_compensate': True,
            'scan_mode': 'Sensitivity',

            # Giữ đúng cấu hình LiDAR hiện tại của bạn: 180 độ.
            # Nếu RViz cho thấy hướng quét không đúng phía cần dùng, chỉ chỉnh tại đây.
            'angle_min': 1.570796,
            'angle_max': 4.712389,
        }]
    )

    arduino_driver = Node(
        package='amr_control',
        executable='arduino_bridge',
        name='arduino_bridge',
        output='screen',
        remappings=[
            ('cmd_vel', '/cmd_vel_safe'),
        ]
    )

    scan_filter_node = Node(
        package='laser_filters',
        executable='scan_to_scan_filter_chain',
        name='scan_to_scan_filter_chain',
        output='screen',
        parameters=[
            os.path.join(bringup_pkg, 'config', 'box_filter.yaml')
        ],
        remappings=[
            ('scan', '/scan'),
            ('scan_filtered', '/scan_filtered'),
        ]
    )

    astra_camera_node = Node(
        package='astra_camera',
        executable='astra_camera_node',
        name='astra_camera',
        output='screen',
        parameters=[{
            # Bật cả color + depth để amr_ai dùng RGB cho YOLO/ReID,
            # depth dùng để tính khoảng cách người và phục vụ pointcloud/octomap.
            'enable_depth': True,
            'enable_color': True,
            'enable_ir': False,

            # Giữ 640x480 để đồng bộ với code AI cũ và model test.
            # Nếu Jetson/USB tải nặng, giảm fps xuống 10.
            'depth_width': 640,
            'depth_height': 480,
            'depth_fps': 15,

            'color_width': 640,
            'color_height': 480,
            'color_fps': 15,

            # Frame ID thống nhất với URDF + static TF.
            'camera_link_frame_id': 'camera_link',
            'depth_frame_id': 'camera_depth_frame',
            'depth_optical_frame_id': 'camera_depth_optical_frame',
            'color_frame_id': 'camera_color_frame',
            'color_optical_frame_id': 'camera_color_optical_frame',

            # Rất quan trọng: tắt TF từ driver để tránh trùng TF.
            # TF chính vẫn do robot_state_publisher + static_transform_publisher quản lý.
            'publish_tf': False,

            # Nếu driver hỗ trợ depth_align:
            # True giúp depth cùng hệ tọa độ ảnh màu, thuận lợi lấy depth theo bbox YOLO.
            # Nếu chạy bị lỗi hoặc pointcloud bất thường, đổi lại False.
            'depth_align': True,

            'use_uvc_camera': False,
            'use_sim_time': False,
        }],
        remappings=[
            ('depth/points', '/camera/depth/points'),
            ('depth/image_raw', '/camera/depth/image_raw'),
            ('depth/camera_info', '/camera/depth/camera_info'),

            ('color/image_raw', '/camera/color/image_raw'),
            ('color/camera_info', '/camera/color/camera_info'),
        ]
    )

    # Quaternion của RPY = roll -pi/2, pitch 0, yaw -pi/2.
    # camera_link: X forward, Y left, Z up
    # optical:     X right,   Y down, Z forward
    static_tf_camera_optical = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='camera_depth_optical_tf',
        output='screen',
        arguments=[
            '0', '0', '0',
            '-0.5', '0.5', '-0.5', '0.5',
            'camera_link',
            'camera_depth_optical_frame',
        ]
    )

    static_tf_camera_color_optical = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='camera_color_optical_tf',
        output='screen',
        arguments=[
            '0', '0', '0',
            '-0.5', '0.5', '-0.5', '0.5',
            'camera_link',
            'camera_color_optical_frame',
        ]
    )

    log_start = LogInfo(msg=[
        '\n',
        '╔═══════════════════════════════════════════════════════════╗\n',
        '║ BRINGUP FUSION - NO UKF                                   ║\n',
        '╠═══════════════════════════════════════════════════════════╣\n',
        '║ TF dynamic : arduino_bridge  odom -> base_footprint       ║\n',
        '║ TF fixed   : robot_state_publisher + camera optical TF    ║\n',
        '║ LiDAR      : /scan -> /scan_filtered                      ║\n',
        '║ Camera     : color + depth + pointcloud, 640x480 @15fps   ║\n',
        '╚═══════════════════════════════════════════════════════════╝\n'
    ])

    return LaunchDescription([
        log_start,
        robot_state_publisher,
        lidar_node,
        arduino_driver,
        scan_filter_node,
        astra_camera_node,
        static_tf_camera_optical,
        static_tf_camera_color_optical,
    ])
