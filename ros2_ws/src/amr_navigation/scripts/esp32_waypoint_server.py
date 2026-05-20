#!/usr/bin/env python3

import socket
import threading
import time

import rclpy
from rclpy.node import Node

from amr_interfaces.srv import SelectZone, SetAiMode


class Esp32WaypointServer(Node):
    """
    ESP32 TCP gateway.

    Vai trò mới:
    - Nhận TCP command từ ESP32: A / B / H / S
    - Không gửi Nav2 trực tiếp nữa
    - Gửi yêu cầu sang ai_mode_manager:
        A/B/H -> /amr_ai/select_zone
        S     -> /amr_ai/set_mode command STOP
    """

    def __init__(self):
        super().__init__('esp32_waypoint_server')

        # =========================
        # Parameters
        # =========================
        self.declare_parameter('host', '0.0.0.0')
        self.declare_parameter('tcp_port', 5000)
        self.declare_parameter('debounce_sec', 0.8)

        self.host = self.get_parameter('host').value
        self.tcp_port = int(self.get_parameter('tcp_port').value)
        self.debounce_sec = float(self.get_parameter('debounce_sec').value)

        self.last_cmd_time = {}

        # =========================
        # Service clients to AI mode manager
        # =========================
        self.select_zone_client = self.create_client(
            SelectZone,
            '/amr_ai/select_zone'
        )

        self.set_mode_client = self.create_client(
            SetAiMode,
            '/amr_ai/set_mode'
        )

        # =========================
        # TCP server thread
        # =========================
        self.server_thread = threading.Thread(
            target=self.tcp_server_loop,
            daemon=True
        )
        self.server_thread.start()

        self.get_logger().info(
            f'ESP32 TCP gateway started at {self.host}:{self.tcp_port}'
        )
        self.get_logger().info(
            'Commands: A/B/H -> /amr_ai/select_zone, S -> /amr_ai/set_mode STOP'
        )

    # ==========================================================
    # TCP server
    # ==========================================================
    def tcp_server_loop(self):
        try:
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

        except Exception as exc:
            self.get_logger().error(f'TCP server error: {exc}')

    def handle_client(self, conn, addr):
        with conn:
            self.get_logger().info(f'ESP32 connected: {addr}')

            while rclpy.ok():
                try:
                    data = conn.recv(64)
                except ConnectionResetError:
                    self.get_logger().warn(f'ESP32 connection reset: {addr}')
                    break
                except Exception as exc:
                    self.get_logger().error(f'ESP32 recv error: {exc}')
                    break

                if not data:
                    break

                text = data.decode(errors='ignore').upper().strip()

                for ch in text:
                    if ch in ['A', 'B', 'H']:
                        self.handle_zone_command(ch)
                    elif ch == 'S':
                        self.handle_stop_command()
                    else:
                        if ch not in ['\n', '\r', ' ', '\t']:
                            self.get_logger().warn(f'Unknown ESP32 command: {ch}')

    # ==========================================================
    # Common debounce
    # ==========================================================
    def is_debounced(self, cmd: str) -> bool:
        now = time.time()

        if cmd in self.last_cmd_time:
            if now - self.last_cmd_time[cmd] < self.debounce_sec:
                self.get_logger().warn(f'Ignore duplicated command: {cmd}')
                return False

        self.last_cmd_time[cmd] = now
        return True

    # ==========================================================
    # Zone command A/B/H
    # ==========================================================
    def handle_zone_command(self, cmd: str):
        if not self.is_debounced(cmd):
            return

        zone_name = 'HOME' if cmd == 'H' else cmd

        if not self.select_zone_client.wait_for_service(timeout_sec=0.5):
            self.get_logger().error(
                'Service /amr_ai/select_zone is not available. '
                'Start ros2 launch amr_ai amr_ai.launch.py first.'
            )
            return

        req = SelectZone.Request()
        req.zone_name = zone_name

        self.get_logger().info(f'Send zone request to AI mode manager: {zone_name}')

        future = self.select_zone_client.call_async(req)
        future.add_done_callback(
            lambda future_done: self.zone_response_callback(future_done, zone_name)
        )

    def zone_response_callback(self, future, zone_name: str):
        try:
            response = future.result()
        except Exception as exc:
            self.get_logger().error(f'Select zone {zone_name} service failed: {exc}')
            return

        if response.accepted:
            self.get_logger().info(
                f'Zone {zone_name} accepted by AI mode manager: {response.message}'
            )
        else:
            self.get_logger().warn(
                f'Zone {zone_name} rejected by AI mode manager: {response.message}'
            )

    # ==========================================================
    # Stop command S
    # ==========================================================
    def handle_stop_command(self):
        if not self.is_debounced('S'):
            return

        if not self.set_mode_client.wait_for_service(timeout_sec=0.5):
            self.get_logger().error(
                'Service /amr_ai/set_mode is not available. '
                'Start ros2 launch amr_ai amr_ai.launch.py first.'
            )
            return

        req = SetAiMode.Request()
        req.mode = 0
        req.command = 'STOP'

        self.get_logger().warn('Send STOP request to AI mode manager')

        future = self.set_mode_client.call_async(req)
        future.add_done_callback(self.stop_response_callback)

    def stop_response_callback(self, future):
        try:
            response = future.result()
        except Exception as exc:
            self.get_logger().error(f'STOP service failed: {exc}')
            return

        if response.success:
            self.get_logger().warn(
                f'STOP accepted by AI mode manager: {response.message}'
            )
        else:
            self.get_logger().warn(
                f'STOP rejected by AI mode manager: {response.message}'
            )


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
