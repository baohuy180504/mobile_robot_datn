import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # 1. ÉP CỨNG THỜI GIAN THỰC (Sim-to-Real)
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    pkg_amr_slam = get_package_share_directory('amr_slam')
    pkg_amr_nav = get_package_share_directory('amr_navigation')
    pkg_nav2 = get_package_share_directory('nav2_bringup')
    pkg_slam = get_package_share_directory('slam_toolbox')

    nav2_params_file = os.path.join(pkg_amr_nav, 'config', 'nav2_params.yaml')
    slam_params_file = os.path.join(pkg_amr_slam, 'config', 'mapper_params_online_async.yaml')

    # [ĐÃ XÓA]: bringup_sim (Gazebo) - Xe thật không cần mô phỏng vật lý
    # [ĐÃ XÓA]: rviz2_node - RViz trên Jetson ngốn quá nhiều RAM, hãy mở trên Laptop

    # 2. Chạy SLAM Toolbox 
    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_slam, 'launch', 'online_async_launch.py')),
        launch_arguments={'use_sim_time': use_sim_time, 'slam_params_file': slam_params_file}.items()
    )

    # 3. Chạy Nav2 ở chế độ SLAM
    nav = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_nav2, 'launch', 'navigation_launch.py')),
        launch_arguments={'use_sim_time': use_sim_time, 'params_file': nav2_params_file}.items()
    )

    # 4. GHOST HAND: Đánh thức hệ thống sau 6 giây
    ghost_goal = TimerAction(
        period=6.0,
        actions=[
            Node(
                package='amr_navigation',
                executable='init_move.py',
                name='auto_goal_sender',
                output='screen'
            )
        ]
    )

    # 5. EXPLORE LITE: Khai báo thẳng Node ở đây (Không cần file launch phụ)
    explore_node = Node(
        package='explore_lite',
        executable='explore',
        name='explore',
        output='screen',
        parameters=[{
            'use_sim_time': False,
            'robot_base_frame': 'base_footprint', # Đã khóa theo URDF
            'costmap_topic': 'map',
            'visualize': True,
            'planner_frequency': 0.5,
            'progress_timeout': 30.0,
            'potential_scale': 3.0,
            'orientation_scale': 0.0,
            'gain_scale': 1.0,
            'transform_tolerance': 0.5,      
            'min_frontier_size': 0.3,        
        }]
    )

    # Thả xích AI Explore sau 20 giây
    delayed_explore = TimerAction(
        period=20.0,
        actions=[explore_node]
    )

    return LaunchDescription([
        slam,
        nav,
        ghost_goal,
        delayed_explore
    ])