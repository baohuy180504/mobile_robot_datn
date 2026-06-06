import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    bringup_dir = get_package_share_directory('amr_bringup')
    default_ekf_params = os.path.join(bringup_dir, 'config', 'ekf_odom.yaml')

    params_arg = DeclareLaunchArgument(
        'params_file',
        default_value=default_ekf_params,
        description='Full path to EKF odom parameter file'
    )

    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[LaunchConfiguration('params_file')],
        remappings=[
            # Giữ topic /odom cho Nav2/SLAM hiện tại, nhưng nguồn /odom bây giờ là EKF.
            ('odometry/filtered', '/odom'),
        ]
    )

    log_info = LogInfo(msg=[
        '\n',
        '╔════════════════════════════════════════════════════════════╗\n',
        '║ EKF ODOM - wheel/odom + imu/data -> /odom                 ║\n',
        '╠════════════════════════════════════════════════════════════╣\n',
        '║ Input 1 : /wheel/odom                                     ║\n',
        '║ Input 2 : /imu/data                                       ║\n',
        '║ Output  : /odom                                           ║\n',
        '║ TF      : odom -> base_footprint                          ║\n',
        '╚════════════════════════════════════════════════════════════╝\n',
    ])

    return LaunchDescription([
        params_arg,
        log_info,
        ekf_node,
    ])
