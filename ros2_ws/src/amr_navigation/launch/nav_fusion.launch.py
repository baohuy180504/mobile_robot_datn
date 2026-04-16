import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # 1. Khai báo các đường dẫn
    pkg_amr_description = get_package_share_directory('amr_description')
    pkg_amr_nav = get_package_share_directory('amr_navigation')
    
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    
    # Đường dẫn file bản đồ và cấu hình (Huy kiểm tra lại tên file đã lưu nhé)
    map_yaml_file = os.path.join(pkg_amr_nav, 'maps', 'my_room_map.yaml')
    octomap_bt_file = os.path.join(pkg_amr_nav, 'maps', 'my_room.bt')
    #octomap_bt_file = '/home/huy_ubuntu/test_ros/ros2_ws/src/amr_navigation/maps/my_room.bt'
    nav2_params_file = os.path.join(pkg_amr_nav, 'config', 'nav2_params_vslam.yaml')

    # 3. Map Server (Nạp bản đồ 2D tĩnh)
    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}, 
                    {'yaml_filename': map_yaml_file}]
    )
 
    # 4. AMCL (Định vị xe trên bản đồ 2D dùng LiDAR)
    amcl_node = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[nav2_params_file, {'use_sim_time': use_sim_time}]
    )

    # 5. Octomap Server (Nạp lại bản đồ 3D để hiển thị)
    octomap_server_node = Node(
        package='octomap_server',
        executable='octomap_server_node',
        name='octomap_server',
        output='screen',
        # ĐÃ XÓA DÒNG ARGUMENTS Ở ĐÂY
        parameters=[{
            'use_sim_time': use_sim_time,
            'frame_id': 'map',
            'base_frame_id': 'base_footprint',
            'resolution': 0.05,
            'octomap_path': octomap_bt_file,  # <--- ĐÂY LÀ CHÌA KHÓA PHÁ ÁN!
            'sensor_model.max_range': 4.0,
            'sensor_model.hit': 0.7,
            'sensor_model.miss': 0.4,
        }],
        remappings=[
            ('cloud_in', '/camera/astra/points')
        ]
    )

    # 6. Các Node điều khiển của Nav2 (Planner, Controller,...)
    lifecycle_nodes = ['map_server', 'amcl', 'controller_server', 'planner_server', 
                       'behavior_server', 'bt_navigator', 'waypoint_follower', 'velocity_smoother']
    
    nav_nodes = []
    # Các node logic điều hướng
    nav_nodes.append(Node(
        package='nav2_controller', executable='controller_server', name='controller_server',
        output='screen', parameters=[nav2_params_file, {'use_sim_time': use_sim_time}]))
    nav_nodes.append(Node(
        package='nav2_planner', executable='planner_server', name='planner_server',
        output='screen', parameters=[nav2_params_file, {'use_sim_time': use_sim_time}]))
    nav_nodes.append(Node(
        package='nav2_behaviors', executable='behavior_server', name='behavior_server',
        output='screen', parameters=[nav2_params_file, {'use_sim_time': use_sim_time}]))
    nav_nodes.append(Node(
        package='nav2_bt_navigator', executable='bt_navigator', name='bt_navigator',
        output='screen', parameters=[nav2_params_file, {'use_sim_time': use_sim_time}]))
    nav_nodes.append(Node(
        package='nav2_waypoint_follower', executable='waypoint_follower', name='waypoint_follower',
        output='screen', parameters=[nav2_params_file, {'use_sim_time': use_sim_time}]))
    nav_nodes.append(Node(
        package='nav2_velocity_smoother', executable='velocity_smoother', name='velocity_smoother',
        output='screen', parameters=[nav2_params_file, {'use_sim_time': use_sim_time}]))

    # Lifecycle Manager (Kích hoạt tất cả các node)
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}, 
                    {'autostart': True}, 
                    {'node_names': lifecycle_nodes}]
    )

    # Gom nhóm các node Nav2 để delay
    nav_stack = [lifecycle_manager] + nav_nodes
    delayed_nav = TimerAction(period=5.0, actions=nav_stack)


    return LaunchDescription([
        map_server_node,
        amcl_node,
        octomap_server_node,
        delayed_nav
    ])