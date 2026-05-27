#!/usr/bin/env python3

import math
import re
import os
import json
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose

from amr_interfaces.msg import AiMode
from amr_interfaces.srv import SetAiMode, SelectZone


def yaw_to_quaternion(yaw: float):
    qz = math.sin(yaw / 2.0)
    qw = math.cos(yaw / 2.0)
    return 0.0, 0.0, qz, qw


class AiModeManager(Node):
    """
    Node trung tâm quản lý mode cho AMR.

    Vai trò:
    - Nhận lệnh đổi mode: /amr_ai/set_mode
    - Nhận lệnh chọn khu: /amr_ai/select_zone
    - Publish mode hiện tại: /amr_ai/mode
    - Gửi goal A/B/Home sang Nav2 khi hợp lệ
    """

    def __init__(self):
        super().__init__('ai_mode_manager')

        # =========================
        # Parameters
        # =========================
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('runtime_waypoints_file', '~/mobile_robot/ros2_ws/config/waypoints_runtime.json')

        # Waypoint A
        self.declare_parameter('A.x', 1.5)
        self.declare_parameter('A.y', 0.0)
        self.declare_parameter('A.yaw', 0.0)

        # Waypoint B
        self.declare_parameter('B.x', 1.5)
        self.declare_parameter('B.y', 1.0)
        self.declare_parameter('B.yaw', 3.14)

        # Home
        self.declare_parameter('H.x', 0.0)
        self.declare_parameter('H.y', 0.0)
        self.declare_parameter('H.yaw', 0.0)

        self.frame_id = self.get_parameter('frame_id').value

        self.fallback_waypoints = {
            'A': (
                self.get_parameter('A.x').value,
                self.get_parameter('A.y').value,
                self.get_parameter('A.yaw').value
            ),
            'B': (
                self.get_parameter('B.x').value,
                self.get_parameter('B.y').value,
                self.get_parameter('B.yaw').value
            ),
        }

        runtime_file = str(self.get_parameter('runtime_waypoints_file').value)
        self.runtime_waypoints_file = Path(os.path.expanduser(runtime_file))

        # =========================
        # State
        # =========================
        self.current_mode = AiMode.IDLE
        self.mode_detail = 'System initialized'
        self.current_goal_handle = None
        self.current_zone: Optional[str] = None

        # =========================
        # ROS interfaces
        # =========================
        self.mode_pub = self.create_publisher(
            AiMode,
            '/amr_ai/mode',
            10
        )

        self.set_mode_srv = self.create_service(
            SetAiMode,
            '/amr_ai/set_mode',
            self.handle_set_mode
        )

        self.select_zone_srv = self.create_service(
            SelectZone,
            '/amr_ai/select_zone',
            self.handle_select_zone
        )

        self.nav_client = ActionClient(
            self,
            NavigateToPose,
            'navigate_to_pose'
        )

        self.mode_timer = self.create_timer(0.5, self.publish_mode)

        self.get_logger().info('AI Mode Manager started')
        self.get_logger().info(f'Runtime waypoint file: {self.runtime_waypoints_file}')
        self.publish_mode()

    # ==========================================================
    # Mode helpers
    # ==========================================================
    def mode_name(self, mode: int) -> str:
        names = {
            AiMode.IDLE: 'IDLE',
            AiMode.NAV_TO_ZONE: 'NAV_TO_ZONE',
            AiMode.FOLLOW_DETECTING: 'FOLLOW_DETECTING',
            AiMode.FOLLOW_ACTIVE: 'FOLLOW_ACTIVE',
            AiMode.FOLLOW_STOPPED: 'FOLLOW_STOPPED',
            AiMode.RETURN_TO_ZONE: 'RETURN_TO_ZONE',
            AiMode.EMERGENCY_STOP: 'EMERGENCY_STOP',
        }
        return names.get(mode, f'UNKNOWN_{mode}')

    def set_mode(self, mode: int, detail: str = ''):
        old_mode = self.current_mode
        self.current_mode = mode
        self.mode_detail = detail

        self.get_logger().warn(
            f'Mode changed: {self.mode_name(old_mode)} -> '
            f'{self.mode_name(self.current_mode)} | {detail}'
        )

        self.publish_mode()

    def publish_mode(self):
        msg = AiMode()
        msg.stamp = self.get_clock().now().to_msg()
        msg.mode = int(self.current_mode)
        msg.mode_name = self.mode_name(self.current_mode)
        msg.detail = self.mode_detail
        self.mode_pub.publish(msg)

    def load_runtime_waypoints(self) -> Dict[str, Tuple[float, float, float]]:
        """
        Đọc waypoint runtime mỗi lần nhận lệnh.
        Quy chuẩn thống nhất:
          WP0/H/HOME = (0,0,0), cố định
          WP1, WP2, WP3... đọc từ waypoints_runtime.json
        Không map A/B/C nữa. ESP32 gửi trực tiếp WP1/WP2/... để tránh nhầm alias.
        """
        lookup: Dict[str, Tuple[float, float, float]] = {
            'WP0': (0.0, 0.0, 0.0),
            'H': (0.0, 0.0, 0.0),
            'HOME': (0.0, 0.0, 0.0),
        }

        data: Dict[str, Any] = {}

        if self.runtime_waypoints_file.exists():
            try:
                data = json.loads(self.runtime_waypoints_file.read_text())
                if not isinstance(data, dict):
                    data = {}
            except Exception as exc:
                self.get_logger().error(
                    f'Failed to read runtime waypoint file {self.runtime_waypoints_file}: {exc}'
                )
                data = {}

        raw_waypoints = data.get('waypoints', [])
        if isinstance(raw_waypoints, list):
            for item in raw_waypoints:
                if not isinstance(item, dict):
                    continue

                name = str(item.get('name', '')).strip().upper()
                match = re.fullmatch(r'WP([1-9][0-9]*)', name)
                if not match:
                    continue

                idx = int(match.group(1))

                try:
                    lookup[f'WP{idx}'] = (
                        float(item.get('x', 0.0)),
                        float(item.get('y', 0.0)),
                        float(item.get('yaw', 0.0)),
                    )
                except Exception:
                    continue

        # Đọc tương thích format cũ key zones, nhưng chỉ lấy tên WPn.
        # Các alias A/B/C cũ không còn được dùng nữa.
        raw_zones = data.get('zones', [])
        if isinstance(raw_zones, list):
            for item in raw_zones:
                if not isinstance(item, dict):
                    continue

                name = str(item.get('name', '')).strip().upper()
                match = re.fullmatch(r'WP([1-9][0-9]*)', name)
                if not match:
                    continue

                wp_name = f'WP{int(match.group(1))}'
                if wp_name in lookup:
                    continue

                try:
                    lookup[wp_name] = (
                        float(item.get('x', 0.0)),
                        float(item.get('y', 0.0)),
                        float(item.get('yaw', 0.0)),
                    )
                except Exception:
                    continue

        return lookup

    def resolve_zone_pose(self, zone_name: str) -> Optional[Tuple[str, Tuple[float, float, float]]]:
        z = zone_name.strip().upper()

        if not z:
            return None

        if z in ['H', 'HOME', 'WP0']:
            return 'WP0', (0.0, 0.0, 0.0)

        if not re.fullmatch(r'WP([1-9][0-9]*)', z):
            return None

        lookup = self.load_runtime_waypoints()

        if z in lookup:
            return z, lookup[z]

        return None

    def build_pose(self, zone_name: str) -> PoseStamped:
        resolved = self.resolve_zone_pose(zone_name)

        if resolved is None:
            raise KeyError(zone_name)

        _, (x, y, yaw) = resolved

        pose = PoseStamped()
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.header.frame_id = self.frame_id

        pose.pose.position.x = float(x)
        pose.pose.position.y = float(y)
        pose.pose.position.z = 0.0

        qx, qy, qz, qw = yaw_to_quaternion(float(yaw))
        pose.pose.orientation.x = qx
        pose.pose.orientation.y = qy
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw

        return pose

    def normalize_zone_name(self, zone_name: str) -> Optional[str]:
        resolved = self.resolve_zone_pose(zone_name)

        if resolved is None:
            return None

        canonical, _ = resolved
        return canonical

    def is_follow_related_mode(self) -> bool:
        return self.current_mode in [
            AiMode.FOLLOW_DETECTING,
            AiMode.FOLLOW_ACTIVE,
            AiMode.FOLLOW_STOPPED,
        ]

    # ==========================================================
    # Set mode service
    # ==========================================================
    def handle_set_mode(self, request, response):
        command = request.command.strip().upper()
        requested_mode = int(request.mode)

        self.get_logger().info(
            f'Received set_mode request: mode={requested_mode}, command={command}'
        )

        if command in ['START_FOLLOW', 'FOLLOW_START', 'START']:
            return self.start_follow(response)

        if command in ['STOP_FOLLOW', 'FOLLOW_STOP']:
            return self.stop_follow(response)

        if command in ['STOP', 'CANCEL', 'S']:
            return self.stop_or_cancel(response)

        if command in ['EMERGENCY_STOP', 'ESTOP', 'E_STOP']:
            return self.emergency_stop(response)

        if command in ['CLEAR_EMERGENCY', 'RESET_EMERGENCY']:
            return self.clear_emergency(response)

        if command in ['IDLE', 'RESET', 'CLEAR']:
            return self.force_idle(response)

        # Cho phép test nhanh bằng mode số, nhưng vẫn kiểm soát cơ bản
        if requested_mode in [
            AiMode.IDLE,
            AiMode.FOLLOW_DETECTING,
            AiMode.FOLLOW_ACTIVE,
            AiMode.FOLLOW_STOPPED,
            AiMode.EMERGENCY_STOP,
        ]:
            self.set_mode(requested_mode, f'Set directly by service command={command}')
            response.success = True
            response.message = f'Mode set to {self.mode_name(self.current_mode)}'
            response.current_mode = int(self.current_mode)
            return response

        response.success = False
        response.message = f'Unsupported command: {command}'
        response.current_mode = int(self.current_mode)
        return response

    def start_follow(self, response):
        if self.current_mode in [AiMode.NAV_TO_ZONE, AiMode.RETURN_TO_ZONE]:
            self.cancel_current_nav_goal()

        if self.current_mode == AiMode.EMERGENCY_STOP:
            response.success = False
            response.message = 'Cannot start follow while EMERGENCY_STOP is active'
            response.current_mode = int(self.current_mode)
            return response

        self.set_mode(
            AiMode.FOLLOW_DETECTING,
            'Start follow accepted. Waiting for target detection/enrollment.'
        )

        response.success = True
        response.message = 'Start follow accepted'
        response.current_mode = int(self.current_mode)
        return response

    def stop_follow(self, response):
        if self.current_mode in [
            AiMode.FOLLOW_DETECTING,
            AiMode.FOLLOW_ACTIVE,
            AiMode.FOLLOW_STOPPED,
        ]:
            self.cancel_current_nav_goal()
            self.set_mode(
                AiMode.FOLLOW_STOPPED,
                'Follow stopped. Waiting for A/B/Home selection.'
            )
            response.success = True
            response.message = 'Follow stopped'
            response.current_mode = int(self.current_mode)
            return response

        response.success = False
        response.message = f'Robot is not in follow mode. Current mode={self.mode_name(self.current_mode)}'
        response.current_mode = int(self.current_mode)
        return response

    def stop_or_cancel(self, response):
        self.cancel_current_nav_goal()

        if self.current_mode in [AiMode.FOLLOW_DETECTING, AiMode.FOLLOW_ACTIVE]:
            self.set_mode(
                AiMode.FOLLOW_STOPPED,
                'Stop command received during follow'
            )
        elif self.current_mode in [AiMode.NAV_TO_ZONE, AiMode.RETURN_TO_ZONE]:
            self.set_mode(
                AiMode.IDLE,
                'Navigation canceled by stop command'
            )
        else:
            self.set_mode(
                AiMode.IDLE,
                'Stop command received'
            )

        response.success = True
        response.message = 'Stop/cancel accepted'
        response.current_mode = int(self.current_mode)
        return response

    def emergency_stop(self, response):
        self.cancel_current_nav_goal()
        self.set_mode(
            AiMode.EMERGENCY_STOP,
            'Emergency stop activated'
        )

        response.success = True
        response.message = 'Emergency stop activated'
        response.current_mode = int(self.current_mode)
        return response

    def clear_emergency(self, response):
        if self.current_mode != AiMode.EMERGENCY_STOP:
            response.success = False
            response.message = 'Robot is not in EMERGENCY_STOP'
            response.current_mode = int(self.current_mode)
            return response

        self.set_mode(
            AiMode.IDLE,
            'Emergency cleared'
        )

        response.success = True
        response.message = 'Emergency cleared'
        response.current_mode = int(self.current_mode)
        return response

    def force_idle(self, response):
        self.cancel_current_nav_goal()
        self.set_mode(
            AiMode.IDLE,
            'Forced to IDLE'
        )

        response.success = True
        response.message = 'Mode forced to IDLE'
        response.current_mode = int(self.current_mode)
        return response

    # ==========================================================
    # Select zone service
    # ==========================================================
    def handle_select_zone(self, request, response):
        zone = self.normalize_zone_name(request.zone_name)

        if zone is None:
            response.accepted = False
            response.message = f'Unknown zone: {request.zone_name}'
            response.goal = PoseStamped()
            return response

        if zone == 'HOME':
            nav_key = 'HOME'
        else:
            nav_key = zone

        goal_pose = self.build_pose(nav_key)
        response.goal = goal_pose

        # Khóa lệnh chọn khu trong lúc đang detect/bám người
        if self.current_mode in [AiMode.FOLLOW_DETECTING, AiMode.FOLLOW_ACTIVE]:
            response.accepted = False
            response.message = (
                f'Reject zone {zone}: robot is in {self.mode_name(self.current_mode)}'
            )
            self.get_logger().warn(response.message)
            return response

        # Emergency stop thì không nhận lệnh điều hướng
        if self.current_mode == AiMode.EMERGENCY_STOP:
            response.accepted = False
            response.message = 'Reject zone command: robot is in EMERGENCY_STOP'
            self.get_logger().warn(response.message)
            return response

        # Đang chạy tới khu khác thì tạm thời không queue, tránh tự chạy lệnh cũ
        if self.current_mode in [AiMode.NAV_TO_ZONE, AiMode.RETURN_TO_ZONE]:
            response.accepted = False
            response.message = (
                f'Reject zone {zone}: robot is busy in {self.mode_name(self.current_mode)}'
            )
            self.get_logger().warn(response.message)
            return response

        # FOLLOW_STOPPED: cho phép chọn WPn/WP0 để quay về sau khi nhận hàng
        if self.current_mode == AiMode.FOLLOW_STOPPED:
            next_mode = AiMode.RETURN_TO_ZONE
            detail = f'Return to zone {zone} after follow stopped'
        else:
            next_mode = AiMode.NAV_TO_ZONE
            detail = f'Navigate to zone {zone}'

        if not self.send_nav2_goal(zone, goal_pose, next_mode, detail):
            response.accepted = False
            response.message = 'Nav2 action server is not available'
            return response

        response.accepted = True
        response.message = f'Zone {zone} accepted'
        return response

    # ==========================================================
    # Nav2
    # ==========================================================
    def send_nav2_goal(self, zone: str, pose: PoseStamped, next_mode: int, detail: str) -> bool:
        if not self.nav_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error('Nav2 action server /navigate_to_pose is not available')
            return False

        self.current_zone = zone
        self.set_mode(next_mode, detail)

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = pose

        send_future = self.nav_client.send_goal_async(
            goal_msg,
            feedback_callback=self.nav_feedback_callback
        )

        send_future.add_done_callback(
            lambda future: self.nav_goal_response_callback(future, zone)
        )

        return True

    def nav_goal_response_callback(self, future, zone: str):
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error(f'Nav2 rejected goal {zone}')
            self.current_goal_handle = None
            self.current_zone = None
            self.set_mode(AiMode.IDLE, f'Nav2 rejected goal {zone}')
            return

        self.current_goal_handle = goal_handle
        self.get_logger().info(f'Nav2 accepted goal {zone}')

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda future: self.nav_result_callback(future, zone)
        )

    def nav_result_callback(self, future, zone: str):
        result = future.result()
        status = result.status

        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f'Goal {zone} reached successfully')
            self.set_mode(AiMode.IDLE, f'Goal {zone} reached successfully')

        elif status == GoalStatus.STATUS_CANCELED:
            self.get_logger().warn(f'Goal {zone} was canceled')
            if self.current_mode != AiMode.EMERGENCY_STOP:
                self.set_mode(AiMode.IDLE, f'Goal {zone} canceled')

        elif status == GoalStatus.STATUS_ABORTED:
            self.get_logger().error(f'Goal {zone} was aborted')
            if self.current_mode != AiMode.EMERGENCY_STOP:
                self.set_mode(AiMode.IDLE, f'Goal {zone} aborted')

        else:
            self.get_logger().warn(f'Goal {zone} finished with status={status}')
            if self.current_mode != AiMode.EMERGENCY_STOP:
                self.set_mode(AiMode.IDLE, f'Goal {zone} finished with status={status}')

        self.current_goal_handle = None
        self.current_zone = None

    def nav_feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        self.get_logger().info(
            f'Mode={self.mode_name(self.current_mode)}, '
            f'zone={self.current_zone}, '
            f'distance_remaining={feedback.distance_remaining:.3f} m'
        )

    def cancel_current_nav_goal(self):
        if self.current_goal_handle is None:
            return

        try:
            self.get_logger().warn('Cancel current Nav2 goal')
            self.current_goal_handle.cancel_goal_async()
        except Exception as exc:
            self.get_logger().error(f'Failed to cancel Nav2 goal: {exc}')

        self.current_goal_handle = None
        self.current_zone = None


def main(args=None):
    rclpy.init(args=args)
    node = AiModeManager()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
