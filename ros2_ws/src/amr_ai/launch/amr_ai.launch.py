import os
import shutil
import re

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node


def _parse_cpu_list(text):
    """'1' | '1-2' | '0,3-5' -> tập nhân, hoặc None nếu sai cú pháp."""
    cpus = set()
    for part in text.split(','):
        m = re.fullmatch(r'(\d+)(?:-(\d+))?', part.strip())
        if not m:
            return None
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        if b < a:
            return None
        cpus.update(range(a, b + 1))
    return cpus


def _ai_detector_actions(context, *args, **kwargs):
    """
    ai_detector = tiến trình suy luận GPU (YOLO person + pose). Ghim vào nhân CPU ai_cpus bằng
    "taskset -c": tiến trình bắt đầu đã ở nhân đó nên mọi luồng sinh sau đều thừa hưởng, và
    khi node khởi động lại vẫn được ghim. ai_cpus rỗng = không ghim.
    """
    ai_cpus = LaunchConfiguration('ai_cpus').perform(context).strip()
    prefix = None

    if not ai_cpus:
        msg = '[ai_detector] ai_cpus rỗng: KHÔNG ghim nhân CPU'
    else:
        cpus = _parse_cpu_list(ai_cpus)
        n = os.cpu_count() or 1
        if cpus is None:
            msg = f'[ai_detector] CẢNH BÁO: ai_cpus="{ai_cpus}" sai cú pháp (vd 1 | 1-2 | 0,3-5) -> KHÔNG ghim'
        elif max(cpus) >= n:
            msg = f'[ai_detector] CẢNH BÁO: ai_cpus="{ai_cpus}" vượt số nhân của máy ({n} nhân) -> KHÔNG ghim'
        elif shutil.which('taskset') is None:
            msg = '[ai_detector] CẢNH BÁO: không tìm thấy lệnh taskset -> KHÔNG ghim'
        else:
            prefix = f'taskset -c {ai_cpus}'
            msg = f'[ai_detector] ghim vào nhân CPU {ai_cpus} (dùng ai_cpus:= để đổi, để trống để tắt)'

    return [
        LogInfo(msg=msg),
        Node(
            package='amr_ai',
            executable='ai_detector',
            name='ai_detector_node',
            output='screen',
            parameters=[LaunchConfiguration('params_file')],
            prefix=prefix,
            condition=IfCondition(LaunchConfiguration('start_ai_detector'))
        ),
    ]


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

    start_ai_detector_arg = DeclareLaunchArgument(
        'start_ai_detector',
        default_value='true',
        description='Start AI fall detector node (chi nhan dien te nga)'
    )

    ai_cpus_arg = DeclareLaunchArgument(
        'ai_cpus',
        default_value='1',
        description='Nhan CPU cho ai_detector (suy luan GPU), vd 1 | 1-2 | 0,3-5. De trong = khong ghim'
    )

    start_auto_initial_pose_arg = DeclareLaunchArgument(
        'start_auto_initial_pose',
        default_value='true',
        description='Publish HOME initial pose for AMCL on startup'
    )

    start_esp32_gateway_arg = DeclareLaunchArgument(
        'start_esp32_gateway',
        default_value='true',
        description='Start ESP32 waypoint gateway'
    )

    start_esp32_alert_bridge_arg = DeclareLaunchArgument(
        'start_esp32_alert_bridge',
        default_value='true',
        description='Start ESP32 alert bridge node (forward alerts to ESP32 display)'
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

    ai_detector = OpaqueFunction(function=_ai_detector_actions)

    auto_initial_pose = Node(
        package='amr_ai',
        executable='auto_initial_pose',
        name='auto_initial_pose_node',
        output='screen',
        parameters=[params_file],
        condition=IfCondition(LaunchConfiguration('start_auto_initial_pose'))
    )

    esp32_gateway = Node(
        package='amr_navigation',
        executable='esp32_waypoint_server.py',
        name='esp32_waypoint_server',
        output='screen',
        condition=IfCondition(LaunchConfiguration('start_esp32_gateway'))
    )

    esp32_alert_bridge = Node(
        package='amr_ai',
        executable='esp32_alert_bridge',
        name='esp32_alert_bridge_node',
        output='screen',
        parameters=[params_file],
        condition=IfCondition(LaunchConfiguration('start_esp32_alert_bridge'))
    )

    log_info = LogInfo(msg=[
        '\n',
        '╔════════════════════════════════════════════════════════════╗\n',
        '║ AMR AI FOLLOW SYSTEM                                      ║\n',
        '╠════════════════════════════════════════════════════════════╣\n',
        '║ ai_mode_manager : mode + WP/Home + dung xe khi te nga     ║\n',
        '║ person_tracker  : YOLO + ReID + depth target              ║\n',
        '║ ai_detector     : nhan dien te nga (moi che do)           ║\n',
        '║ esp32_gateway   : ESP32 WPn/HOME/S -> amr_ai services     ║\n',
        '╚════════════════════════════════════════════════════════════╝\n',
    ])

    return LaunchDescription([
        params_file_arg,
        start_mode_manager_arg,
        start_person_tracker_arg,
        start_follow_goal_arg,
        start_follow_servo_arg,
        start_cmd_vel_safety_mux_arg,
        start_ai_detector_arg,
        ai_cpus_arg,
        start_auto_initial_pose_arg,
        start_esp32_gateway_arg,
        start_esp32_alert_bridge_arg,

        log_info,

        ai_mode_manager,
        person_tracker,
        follow_goal,
        follow_servo,
        cmd_vel_safety_mux,
        ai_detector,
        auto_initial_pose,
        esp32_gateway,
        esp32_alert_bridge,
    ])