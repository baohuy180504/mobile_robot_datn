#!/usr/bin/env python3

import socket
import re
import threading
import time

import rclpy
from rclpy.node import Node

from std_msgs.msg import Bool
from amr_interfaces.srv import SelectZone, SetAiMode


class Esp32WaypointServer(Node):
    """
    ESP32 TCP gateway.

    Vai trò mới:
    - Nhận TCP command từ ESP32: WP1 / WP2 / ... / WP0 / S
    - Không gửi Nav2 trực tiếp nữa
    - Gửi yêu cầu sang ai_mode_manager:
        WPn/WP0 -> /amr_ai/select_zone
        S/STOP -> /amr_ai/set_mode command STOP
    """

    def __init__(self):
        super().__init__('esp32_waypoint_server')

        # =========================
        # Parameters
        # =========================
        self.declare_parameter('host', '0.0.0.0')
        self.declare_parameter('tcp_port', 5000)
        self.declare_parameter('debounce_sec', 0.8)
        # Timeout đồng bộ với manual_override_timeout_s của mux (mặc định 0.5s).
        # Đặt hơi cao hơn một chút để tránh nhấp nháy ở ranh giới.
        self.declare_parameter('manual_override_timeout_s', 0.6)

        self.host = self.get_parameter('host').value
        self.tcp_port = int(self.get_parameter('tcp_port').value)
        self.debounce_sec = float(self.get_parameter('debounce_sec').value)
        self.manual_override_timeout_s = float(
            self.get_parameter('manual_override_timeout_s').value
        )

        self.last_cmd_time = {}

        # Manual override state — sync với /amr_ai/manual_override
        self.manual_override_active: bool = False
        self.last_manual_override_time: float = 0.0

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

        # Subscribe /amr_ai/manual_override để biết khi nào teleop đang bật.
        # Khi engineer bấm START CONTROL trên web, web server publish Bool(True)
        # liên tục 5Hz. Khi STOP CONTROL, publish Bool(False) rồi ngừng.
        # Ta cũng check timeout để tự reset nếu heartbeat mất đột ngột.
        self.manual_override_sub = self.create_subscription(
            Bool,
            '/amr_ai/manual_override',
            self.manual_override_callback,
            10
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
            'Commands: WP0/WP1/WP2/... -> /amr_ai/select_zone, S/STOP -> /amr_ai/set_mode STOP'
        )
        self.get_logger().info(
            'Manual override: /amr_ai/manual_override — WP bị khóa khi teleop đang bật'
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
                commands = self.parse_commands(text)

                for cmd in commands:
                    if cmd in ['S', 'STOP']:
                        self.handle_stop_command()
                    elif self.is_waypoint_command(cmd):
                        self.handle_zone_command(cmd)
                    else:
                        self.get_logger().warn(f'Unknown ESP32 command: {cmd}')

    def parse_commands(self, text: str):
        """
        ESP32 gửi chuẩn: WP1, WP2, WP3..., WP0 hoặc S/STOP.
        Hàm này vẫn chịu được trường hợp có \n, dấu phẩy hoặc nhiều token trong một packet.
        """
        if not text:
            return []

        cleaned = text.replace(',', ' ').replace(';', ' ').replace('\r', ' ').replace('\n', ' ')
        parts = [p.strip().upper() for p in cleaned.split() if p.strip()]

        if parts:
            return parts

        # Fallback nếu ESP32 gửi dính chuỗi, ví dụ WP1WP2S
        return re.findall(r'WP[0-9]+|STOP|S', text.upper())

    def is_waypoint_command(self, cmd: str) -> bool:
        return re.fullmatch(r'WP[0-9]+', cmd.strip().upper()) is not None

    # ==========================================================
    # Manual override callback
    # ==========================================================
    def manual_override_callback(self, msg: Bool):
        self.manual_override_active = bool(msg.data)
        self.last_manual_override_time = time.time()

    def is_manual_override_active(self) -> bool:
        """
        True nếu teleop đang bật (web server publish Bool(True) < timeout_s trước).
        Dùng timeout để tự reset nếu heartbeat mất đột ngột (web server crash).
        """
        if not self.manual_override_active:
            return False
        return (time.time() - self.last_manual_override_time) <= self.manual_override_timeout_s

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
    # Waypoint command WP0/WP1/WP2/...
    # ==========================================================
    def handle_zone_command(self, cmd: str):
        if not self.is_debounced(cmd):
            return

        # Khóa nút vật lý khi engineer đang điều khiển tay qua web teleop.
        # Tránh ESP32 gửi WP làm xung đột với lệnh vận tốc từ teleop.
        if self.is_manual_override_active():
            self.get_logger().warn(
                f'Ignore zone command {cmd}: manual teleop override is active '
                '(engineer is driving via web control — press STOP CONTROL first)'
            )
            return

        zone_name = cmd.strip().upper()

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