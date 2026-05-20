import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node


def generate_launch_description():
    amr_ai_dir = get_package_share_directory('amr_ai')

    default_params_file = os.path.join(
        amr_ai_dir,
        'config',
        'ai_params.yaml'
    )

    params_file_arg = DeclareLaunchArgument(
        'params_file',
        default_value=default_params_file,
        description='Full path to amr_ai params file'
    )

    start_mode_manager_arg = DeclareLaunchArgument(
        'start_mode_manager',
        default_value='true',
        description='Start AI mode manager'
    )

    start_person_tracker_arg = DeclareLaunchArgument(
        'start_person_tracker',
        default_value='true',
        description='Start person tracker node'
    )

    start_follow_goal_arg = DeclareLaunchArgument(
        'start_follow_goal',
        default_value='false',
        description='Start follow goal node'
    )

    start_follow_servo_arg = DeclareLaunchArgument(
        'start_follow_servo',
        default_value='true',
        description='Start visual servo follow node'
    )

    start_cmd_vel_safety_mux_arg = DeclareLaunchArgument(
        'start_cmd_vel_safety_mux',
        default_value='true',
        description='Start cmd_vel safety mux node'
    )

    start_esp32_gateway_arg = DeclareLaunchArgument(
        'start_esp32_gateway',
        default_value='true',
        description='Start ESP32 waypoint gateway'
    )

    params_file = LaunchConfiguration('params_file')

    ai_mode_manager = Node(
        package='amr_ai',
        executable='ai_mode_manager',
        name='ai_mode_manager',
        output='screen',
        parameters=[params_file],
        condition=IfCondition(LaunchConfiguration('start_mode_manager'))
    )

    person_tracker = Node(
        package='amr_ai',
        executable='person_tracker',
        name='person_tracker_node',
        output='screen',
        parameters=[params_file],
        condition=IfCondition(LaunchConfiguration('start_person_tracker'))
    )

    follow_goal = Node(
        package='amr_ai',
        executable='follow_goal',
        name='follow_goal_node',
        output='screen',
        parameters=[params_file],
        condition=IfCondition(LaunchConfiguration('start_follow_goal'))
    )

    follow_servo = Node(
        package='amr_ai',
        executable='follow_servo',
        name='follow_servo_node',
        output='screen',
        parameters=[params_file],
        condition=IfCondition(LaunchConfiguration('start_follow_servo'))
    )

    cmd_vel_safety_mux = Node(
        package='amr_ai',
        executable='cmd_vel_safety_mux',
        name='cmd_vel_safety_mux_node',
        output='screen',
        parameters=[params_file],
        condition=IfCondition(LaunchConfiguration('start_cmd_vel_safety_mux'))
    )


    esp32_gateway = Node(
        package='amr_navigation',
        executable='esp32_waypoint_server.py',
        name='esp32_waypoint_server',
        output='screen',
        condition=IfCondition(LaunchConfiguration('start_esp32_gateway'))
    )

    log_info = LogInfo(msg=[
        '\n',
        '╔════════════════════════════════════════════════════════════╗\n',
        '║ AMR AI FOLLOW SYSTEM                                      ║\n',
        '╠════════════════════════════════════════════════════════════╣\n',
        '║ ai_mode_manager : mode + lock A/B/Home                    ║\n',
        '║ person_tracker  : YOLO + ReID + depth target              ║\n',
        '║ follow_goal     : person target -> Nav2 goal              ║\n',
        '║ esp32_gateway   : ESP32 A/B/H/S -> amr_ai services        ║\n',
        '╚════════════════════════════════════════════════════════════╝\n',
    ])

    return LaunchDescription([
        params_file_arg,
        start_mode_manager_arg,
        start_person_tracker_arg,
        start_follow_goal_arg,
        start_follow_servo_arg,
        start_cmd_vel_safety_mux_arg,
        start_esp32_gateway_arg,

        log_info,

        ai_mode_manager,
        person_tracker,
        follow_goal,
        follow_servo,
        cmd_vel_safety_mux,
        esp32_gateway,
    ])