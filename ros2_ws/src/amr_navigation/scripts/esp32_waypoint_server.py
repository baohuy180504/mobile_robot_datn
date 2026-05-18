#!/usr/bin/env python3

import math
import socket
import threading
import time
from collections import deque

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from action_msgs.msg import GoalStatus


def yaw_to_quaternion(yaw):
    """
    Convert yaw angle in radian to quaternion.
    Roll = 0, Pitch = 0.
    """
    qz = math.sin(yaw / 2.0)
    qw = math.cos(yaw / 2.0)
    return 0.0, 0.0, qz, qw


class Esp32WaypointServer(Node):
    def __init__(self):
        super().__init__('esp32_waypoint_server')

        # =========================
        # Parameters
        # =========================
        self.declare_parameter('host', '0.0.0.0')
        self.declare_parameter('tcp_port', 5000)
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('debounce_sec', 0.8)

        # Tọa độ waypoint A
        self.declare_parameter('A.x', 1.5)
        self.declare_parameter('A.y', 0.0)
        self.declare_parameter('A.yaw', 0.0)

        # Tọa độ waypoint B
        self.declare_parameter('B.x', 1.5)
        self.declare_parameter('B.y', 1.0)
        self.declare_parameter('B.yaw', 3.14)

        # Tọa độ Home
        self.declare_parameter('H.x', 0.0)
        self.declare_parameter('H.y', 0.0)
        self.declare_parameter('H.yaw', 0.0)

        self.host = self.get_parameter('host').value
        self.tcp_port = self.get_parameter('tcp_port').value
        self.frame_id = self.get_parameter('frame_id').value
        self.debounce_sec = self.get_parameter('debounce_sec').value

        self.waypoints = {
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
            'H': (
                self.get_parameter('H.x').value,
                self.get_parameter('H.y').value,
                self.get_parameter('H.yaw').value
            ),
        }

        # =========================
        # Navigation state
        # =========================
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        self.task_queue = deque()
        self.queue_lock = threading.Lock()

        self.is_navigating = False
        self.current_task = None
        self.current_goal_handle = None

        self.last_cmd_time = {}

        # =========================
        # TCP server thread
        # =========================
        self.server_thread = threading.Thread(
            target=self.tcp_server_loop,
            daemon=True
        )
        self.server_thread.start()

        self.get_logger().info(
            f'ESP32 waypoint server started at {self.host}:{self.tcp_port}'
        )
        self.get_logger().info(f'Waypoints: {self.waypoints}')

    # ==========================================================
    # TCP server
    # ==========================================================
    def tcp_server_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.tcp_port))
            server.listen(5)

            self.get_logger().info('Waiting for ESP32 commands...')

            while rclpy.ok():
                try:
                    conn, addr = server.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(conn, addr),
                        daemon=True
                    )
                    client_thread.start()
                except OSError:
                    break

    def handle_client(self, conn, addr):
        with conn:
            self.get_logger().info(f'ESP32 connected: {addr}')

            while rclpy.ok():
                data = conn.recv(64)

                if not data:
                    break

                text = data.decode(errors='ignore').upper()

                for ch in text:
                    if ch in ['A', 'B', 'H']:
                        self.handle_waypoint_command(ch)
                    elif ch == 'S':
                        self.cancel_current_goal()

    # ==========================================================
    # Command handling
    # ==========================================================
    def handle_waypoint_command(self, cmd):
        now = time.time()

        # Chống dội nút / gửi trùng quá nhanh
        if cmd in self.last_cmd_time:
            if now - self.last_cmd_time[cmd] < self.debounce_sec:
                self.get_logger().warn(f'Ignore duplicated command: {cmd}')
                return

        self.last_cmd_time[cmd] = now

        if cmd not in self.waypoints:
            self.get_logger().warn(f'Unknown waypoint command: {cmd}')
            return

        with self.queue_lock:
            if self.is_navigating:
                self.task_queue.append(cmd)
                self.get_logger().info(
                    f'Received {cmd}. Robot is busy with {self.current_task}. '
                    f'Add {cmd} to queue. Queue = {list(self.task_queue)}'
                )
                return

            self.task_queue.append(cmd)
            self.get_logger().info(
                f'Received {cmd}. Robot is idle. Queue = {list(self.task_queue)}'
            )

        self.start_next_task()

    def start_next_task(self):
        with self.queue_lock:
            if self.is_navigating:
                return

            if not self.task_queue:
                self.get_logger().info('Task queue is empty. Robot is idle.')
                self.current_task = None
                return

            cmd = self.task_queue.popleft()
            self.current_task = cmd
            self.is_navigating = True

        x, y, yaw = self.waypoints[cmd]

        self.get_logger().info(
            f'Start task {cmd}: x={x:.3f}, y={y:.3f}, yaw={yaw:.3f}'
        )

        self.send_nav2_goal(cmd, x, y, yaw)

    # ==========================================================
    # Nav2 action
    # ==========================================================
    def send_nav2_goal(self, cmd, x, y, yaw):
        if not self.nav_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error(
                'Nav2 action server /navigate_to_pose is not available'
            )

            with self.queue_lock:
                self.is_navigating = False
                self.current_task = None

            self.start_next_task()
            return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = PoseStamped()
        goal_msg.pose.header.frame_id = self.frame_id
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()

        goal_msg.pose.pose.position.x = float(x)
        goal_msg.pose.pose.position.y = float(y)
        goal_msg.pose.pose.position.z = 0.0

        qx, qy, qz, qw = yaw_to_quaternion(float(yaw))
        goal_msg.pose.pose.orientation.x = qx
        goal_msg.pose.pose.orientation.y = qy
        goal_msg.pose.pose.orientation.z = qz
        goal_msg.pose.pose.orientation.w = qw

        send_future = self.nav_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )

        send_future.add_done_callback(
            lambda future: self.goal_response_callback(future, cmd)
        )

    def goal_response_callback(self, future, cmd):
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error(f'Goal {cmd} was rejected by Nav2')

            with self.queue_lock:
                self.is_navigating = False
                self.current_task = None
                self.current_goal_handle = None

            self.start_next_task()
            return

        self.current_goal_handle = goal_handle
        self.get_logger().info(f'Goal {cmd} accepted by Nav2')

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda future: self.result_callback(future, cmd)
        )

    def result_callback(self, future, cmd):
        result = future.result()
        status = result.status

        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info(f'Goal {cmd} reached successfully')

        elif status == GoalStatus.STATUS_CANCELED:
            self.get_logger().warn(f'Goal {cmd} was canceled')

        elif status == GoalStatus.STATUS_ABORTED:
            self.get_logger().error(f'Goal {cmd} was aborted')

        else:
            self.get_logger().warn(
                f'Goal {cmd} finished with status: {status}'
            )

        with self.queue_lock:
            self.is_navigating = False
            self.current_task = None
            self.current_goal_handle = None

        # Hiện tại: đến goal xong thì tự động chạy task tiếp theo
        # Sau này nếu cần xác nhận người ở khu A/B,
        # ta sẽ KHÔNG gọi start_next_task() ngay tại đây,
        # mà chuyển sang trạng thái WAIT_CONFIRM.
        self.start_next_task()

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback

        self.get_logger().info(
            f'Current task: {self.current_task}, '
            f'distance remaining: {feedback.distance_remaining:.3f} m, '
            f'queue: {list(self.task_queue)}'
        )

    # ==========================================================
    # Cancel
    # ==========================================================
    def cancel_current_goal(self):
        if self.current_goal_handle is None:
            self.get_logger().warn('No active goal to cancel')
            return

        self.get_logger().warn('Cancel current Nav2 goal')
        self.current_goal_handle.cancel_goal_async()

        with self.queue_lock:
            self.task_queue.clear()
            self.get_logger().warn('Task queue cleared')


def main(args=None):
    rclpy.init(args=args)
    node = Esp32WaypointServer()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()