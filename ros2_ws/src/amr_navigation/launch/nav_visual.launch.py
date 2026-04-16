import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetRemap

def generate_launch_description():
    # 1. ÉP CỨNG THỜI GIAN THỰC (Sim-to-Real)
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    pkg_amr_slam = get_package_share_directory('amr_slam')
    pkg_amr_nav = get_package_share_directory('amr_navigation')

    # Trỏ đúng file cấu hình VSLAM chúng ta vừa sửa
    nav2_params_file = os.path.join(pkg_amr_nav, 'config', 'nav2_params_vslam.yaml')

    # [ĐÃ XÓA]: bringup_sim (Gazebo) - Xe thật không cần môi trường giả lập
    # [ĐÃ XÓA]: rviz2_node - RViz trên Jetson ngốn quá nhiều RAM, hãy mở trên Laptop

    # 2. Khởi chạy RTAB-Map ở chế độ Định vị (Localization)
    vslam_loc = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_amr_slam, 'launch', 'vslam_loc.launch.py'))
    )

    # 3. Danh sách các node Nav2 cần khởi động (KHÔNG CÓ AMCL)
    lifecycle_nodes = [
        'controller_server',
        'smoother_server',
        'planner_server',
        'behavior_server',
        'bt_navigator',
        'waypoint_follower',
        'velocity_smoother'
    ]

    # Từ điển ánh xạ chính xác Tên Node -> Tên Package
    nav2_packages = {
        'controller_server': 'nav2_controller',
        'smoother_server': 'nav2_smoother',
        'planner_server': 'nav2_planner',
        'behavior_server': 'nav2_behaviors',
        'bt_navigator': 'nav2_bt_navigator',
        'waypoint_follower': 'nav2_waypoint_follower',
        'velocity_smoother': 'nav2_velocity_smoother'
    }

    # Tạo danh sách các Node độc lập
    nav_nodes = []
    for node_name in lifecycle_nodes:
        nav_nodes.append(
            Node(
                package=nav2_packages[node_name],
                executable=node_name,
                name=node_name,
                output='screen',
                parameters=[nav2_params_file], # Node sẽ tự động lấy use_sim_time=False từ file yaml
                remappings=[
                    ('/initialpose', '/rtabmap/initialpose'), 
                    ('/map', '/rtabmap/map'),
                    #('/cmd_vel', '/cmd_vel_nav') # Bật lên nếu dùng mux để trộn vận tốc
                ]
            )
        )

    # Trình quản lý vòng đời (đánh thức các node)
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time},
                    {'autostart': True},
                    {'node_names': lifecycle_nodes}]
    )
    
    # Gom tất cả Nav2 vào một biến để delay chung (Đợi RTAB-Map lên trước)
    nav = [lifecycle_manager] + nav_nodes
    delayed_nav = TimerAction(period=8.0, actions=nav)

    return LaunchDescription([
        # Ép Nav2 dùng bản đồ và tọa độ từ RTAB-Map
        SetRemap(src='/initialpose', dst='/rtabmap/initialpose'),
        SetRemap(src='/map', dst='/rtabmap/map'), 
        
        vslam_loc,
        delayed_nav
    ])