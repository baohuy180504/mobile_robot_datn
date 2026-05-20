import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    desc_pkg = get_package_share_directory('amr_description')
    urdf_file = os.path.join(desc_pkg, 'urdf', 'robot.urdf')

    # Đọc nội dung URDF
    with open(urdf_file, 'r') as f:
        robot_description = f.read()

    # 1. Phát tán khung xương
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description, 'use_sim_time': False}]
    )

    # 2. Đánh thức Camera 3D (Orbbec Astra)
    # Gói ros2_astra_camera thường có file launch riêng để lo việc trộn ảnh RGBD thành PointCloud
    astra_pkg = get_package_share_directory('astra_camera')
    camera_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(astra_pkg, 'launch', 'astra_mini.launch.py')) # Sửa tên file launch tùy theo dòng Astra bạn đang dùng
    )

    # 3. Giao tiếp Arduino
    arduino_driver = Node(
        package='amr_control',
        executable='arduino_bridge.py',
        name='arduino_bridge',
        output='screen'
    )

    return LaunchDescription([
        robot_state_publisher,
        camera_node,
        arduino_driver
    ])