import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_amr_description = get_package_share_directory('amr_description')

    # 1. Đọc file URDF để gửi cho RViz2
    urdf_file = os.path.join(pkg_amr_description, 'urdf', 'robot.urdf')
    with open(urdf_file, 'r') as infp:
        robot_desc = infp.read()

    # 2. NODE QUAN TRỌNG: Robot State Publisher
    # Nhận URDF và phát tọa độ TF (các trục XYZ) cho RViz2 và SLAM
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_desc,
            'use_sim_time': True # Bắt buộc True để đồng bộ đồng hồ với Gazebo
        }]
    )

    # 3. Đường dẫn tới Thế giới (Mê cung)
    #world_file = os.path.join(pkg_amr_description, 'worlds', 'room.world')  #word cho 2d slam
    world_file = os.path.join(pkg_amr_description, 'worlds', 'room_vslam.world') #word cho visual slam
    # 4. Khởi chạy Gazebo
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')
        ),
        launch_arguments={'world': world_file}.items()
    )

    # 5. Thả robot vào mô phỏng
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-file', urdf_file, 
            '-entity', 'amr_bot', 
            '-x', '0.0',  # Ép X về 0
            '-y', '0.0',  # Ép Y về 0
            '-z', '0.03', # Thả rất thấp để không bị nảy
            '-Y', '0.0'   # Góc quay ban đầu thẳng tắp (Yaw)
        ],
        output='screen'
    )

    # Đường dẫn tới file ekf.yaml
    ekf_config_path = os.path.join(pkg_amr_description, 'config', 'ekf.yaml')
    
    # Khởi chạy Node robot_localization
    # ekf_node = Node(
    #     package='robot_localization',
    #     executable='ekf_node',
    #     name='ekf_filter_node',
    #     output='screen',
    #     parameters=[ekf_config_path, {'use_sim_time': True}]
    # )

    return LaunchDescription([
        robot_state_publisher_node,
        gazebo,
        spawn_entity
        #ekf_node
    ])