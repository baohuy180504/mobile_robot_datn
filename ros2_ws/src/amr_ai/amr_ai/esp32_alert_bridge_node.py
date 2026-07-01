#!/usr/bin/env python3

import socket
import time
import cv2
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from amr_interfaces.msg import AiAlert, AiMode


class Esp32AlertBridgeNode(Node):
    def __init__(self):
        super().__init__('esp32_alert_bridge_node')

        self.declare_parameter('esp32_ip', '192.168.1.36')
        self.declare_parameter('esp32_udp_port', 4210)
        self.declare_parameter('esp32_tcp_port', 4211)

        self.declare_parameter('alert_topic', '/amr_ai/alert')
        self.declare_parameter('debug_image_topic', '/amr_ai/debug/alert/image')
        self.declare_parameter('mode_topic', '/amr_ai/mode')

        self.declare_parameter('snapshot_width', 296)
        self.declare_parameter('snapshot_height', 296)

        # Chỉ gửi ảnh 1 lần cho mỗi incident
        self.declare_parameter('image_send_delay_s', 0.35)
        self.declare_parameter('image_wait_timeout_s', 2.0)

        self.declare_parameter('normal_reset_sec', 1.0)

        self.declare_parameter('socket_timeout_s', 5.0)
 
        self.esp32_ip = self.get_parameter('esp32_ip').value
        self.esp32_udp_port = int(self.get_parameter('esp32_udp_port').value)
        self.esp32_tcp_port = int(self.get_parameter('esp32_tcp_port').value)

        self.alert_topic = self.get_parameter('alert_topic').value
        self.debug_image_topic = self.get_parameter('debug_image_topic').value
        self.mode_topic = self.get_parameter('mode_topic').value

        self.snapshot_width = int(self.get_parameter('snapshot_width').value)
        self.snapshot_height = int(self.get_parameter('snapshot_height').value)

        self.image_send_delay_s = float(self.get_parameter('image_send_delay_s').value)
        self.image_wait_timeout_s = float(self.get_parameter('image_wait_timeout_s').value)
        self.normal_reset_sec = float(self.get_parameter('normal_reset_sec').value)

        self.socket_timeout_s = float(self.get_parameter('socket_timeout_s').value)

        self.bridge = CvBridge()
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.latest_debug_image = None
        self.latest_debug_stamp_sec = 0.0

        # Theo dõi mode hiện tại để biết xe có đang THỰC SỰ bám người
        # (FOLLOW_ACTIVE) hay chỉ mới đang dò/khóa target (FOLLOW_DETECTING).
        # PPE warning chỉ gửi ra ESP32 khi đã FOLLOW_ACTIVE.
        self.current_mode = AiMode.IDLE
        self.PPE_ALERT_TYPES = {'MISSING_HELMET', 'MISSING_VEST', 'MISSING_PPE'}

        # Latch incident (dùng cho FALL / FIRE / SMOKE)
        self.latched_alert_type = None
        self.normal_since = None

        # PPE dùng cooldown riêng — gửi lại mỗi ppe_resend_cooldown_s giây
        # khi còn vi phạm, không phụ thuộc vào NORMAL để reset latch
        self.last_ppe_cmd_time = 0.0
        self.ppe_resend_cooldown_s = 1.5   # gửi mỗi 1.5 giây khi có vi phạm

        # Pending image one-shot
        self.pending_image_cmd = None
        self.pending_image_alert_type = None
        self.pending_image_start_time = 0.0
        self.pending_image_due_time = 0.0

        self.alert_sub = self.create_subscription(
            AiAlert,
            self.alert_topic,
            self.alert_callback,
            10
        )

        self.mode_sub = self.create_subscription(
            AiMode,
            self.mode_topic,
            self.mode_callback,
            10
        )

        self.image_sub = self.create_subscription(
            Image,
            self.debug_image_topic,
            self.debug_image_callback,
            qos_profile_sensor_data
        )

        self.timer = self.create_timer(0.05, self.timer_callback)

        self.get_logger().warn('ESP32 Alert Bridge started - LATCH mode')
        self.get_logger().info(f'ESP32 IP: {self.esp32_ip}')
        self.get_logger().info(f'UDP port: {self.esp32_udp_port}')
        self.get_logger().info(f'TCP image port: {self.esp32_tcp_port}')
        self.get_logger().info(f'Alert topic: {self.alert_topic}')
        self.get_logger().info(f'Debug image topic: {self.debug_image_topic}')
        self.get_logger().info(f'Mode topic: {self.mode_topic}')

    def mode_callback(self, msg: AiMode):
        self.current_mode = int(msg.mode)

    def debug_image_callback(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            self.latest_debug_image = frame
            self.latest_debug_stamp_sec = time.time()
        except Exception as exc:
            self.get_logger().warn(f'Failed to convert debug image: {exc}')

    def alert_callback(self, msg: AiAlert):
        alert_type = str(msg.alert_type).upper().strip()
        now = time.time()

        if alert_type == 'FALL':
            cmd = 'A'
        elif alert_type == 'FIRE':
            cmd = 'B'
        elif alert_type == 'SMOKE':
            cmd = 'C'
        elif alert_type in self.PPE_ALERT_TYPES:
            PPE_ALLOWED_MODES = {
                AiMode.IDLE,
                AiMode.FOLLOW_ACTIVE,
                AiMode.NAV_TO_ZONE,
                AiMode.RETURN_TO_ZONE,
            }
            if self.current_mode not in PPE_ALLOWED_MODES:
                self.get_logger().warn(
                    f'PPE alert BLOCKED: mode={self.current_mode}'
                )
                return

            # PPE dùng cooldown riêng thay vì latch chung.
            # Gửi lại mỗi ppe_resend_cooldown_s giây → liên tục khi còn vi phạm.
            if now - self.last_ppe_cmd_time < self.ppe_resend_cooldown_s:
                return

            self.last_ppe_cmd_time = now
            self.send_udp_cmd('D')

            self.pending_image_cmd = 'D'
            self.pending_image_alert_type = alert_type
            self.pending_image_start_time = now
            self.pending_image_due_time = now + self.image_send_delay_s

            self.get_logger().info(
                f'PPE alert sent: {alert_type}, next in {self.ppe_resend_cooldown_s}s'
            )
            return  # không đi qua latch bên dưới
        else:
            # NORMAL chỉ reset latch nội bộ, không gửi N về ESP32
            self.handle_normal(now)
            return

        self.normal_since = None

        # Nếu cùng loại cảnh báo đang latch rồi thì không gửi lại A/B/C và không gửi lại ảnh
        if self.latched_alert_type == alert_type:
            return

        # Cảnh báo mới
        self.latched_alert_type = alert_type

        self.send_udp_cmd(cmd)

        # Đặt lịch gửi ảnh 1 lần sau một khoảng delay ngắn,
        # để debug image mới nhất kịp publish sau alert.
        self.pending_image_cmd = cmd
        self.pending_image_alert_type = alert_type
        self.pending_image_start_time = now
        self.pending_image_due_time = now + self.image_send_delay_s

        self.get_logger().warn(
            f'NEW INCIDENT: {alert_type}, sent cmd={cmd}, image scheduled'
        )

    def handle_normal(self, now):
        if self.latched_alert_type is None:
            return

        if self.normal_since is None:
            self.normal_since = now
            return

        if now - self.normal_since >= self.normal_reset_sec:
            self.get_logger().info(
                f'AI returned NORMAL, internal latch reset from {self.latched_alert_type}. '
                f'ESP32 display is NOT cleared automatically.'
            )
            self.latched_alert_type = None
            self.normal_since = None
            self.pending_image_cmd = None
            self.pending_image_alert_type = None

    def timer_callback(self):
        if self.pending_image_cmd is None:
            return

        now = time.time()

        if now < self.pending_image_due_time:
            return

        # Chờ debug image mới hơn thời điểm alert một chút
        if self.latest_debug_image is None:
            if now - self.pending_image_start_time > self.image_wait_timeout_s:
                self.get_logger().warn(
                    f'No debug image for {self.pending_image_alert_type}, skip one-shot image'
                )
                self.clear_pending_image()
            return

        if self.latest_debug_stamp_sec < self.pending_image_start_time:
            if now - self.pending_image_start_time <= self.image_wait_timeout_s:
                return

            self.get_logger().warn(
                f'Debug image not updated after alert, sending latest old frame anyway'
            )

        cmd = self.pending_image_cmd
        alert_type = self.pending_image_alert_type

        ok = self.send_latest_image(cmd)

        if ok:
            self.get_logger().warn(f'One-shot image sent for {alert_type}')
        else:
            self.get_logger().warn(f'Failed to send one-shot image for {alert_type}')

        self.clear_pending_image()

    def clear_pending_image(self):
        self.pending_image_cmd = None
        self.pending_image_alert_type = None
        self.pending_image_start_time = 0.0
        self.pending_image_due_time = 0.0

    def send_udp_cmd(self, cmd: str):
        try:
            self.udp_sock.sendto(
                cmd.encode('ascii'),
                (self.esp32_ip, self.esp32_udp_port)
            )
            self.get_logger().info(f'Sent UDP alert cmd: {cmd}')
        except Exception as exc:
            self.get_logger().warn(f'Failed to send UDP cmd {cmd}: {exc}')

    def send_latest_image(self, cmd: str) -> bool:
        if self.latest_debug_image is None:
            self.get_logger().warn('No debug image available, skip TCP image')
            return False

        try:
            img = self.letterbox_bgr(
                self.latest_debug_image,
                self.snapshot_width,
                self.snapshot_height
            )
            payload = self.bgr_to_rgb565_le(img)

            header = (
                f'AMRI,{cmd},{self.snapshot_width},'
                f'{self.snapshot_height},{len(payload)}\n'
            ).encode('ascii')

            self.get_logger().info(
                f'Sending one-shot image: cmd={cmd}, '
                f'{self.snapshot_width}x{self.snapshot_height}, '
                f'{len(payload)} bytes'
            )

            with socket.create_connection(
                (self.esp32_ip, self.esp32_tcp_port),
                timeout=self.socket_timeout_s
            ) as sock:
                sock.settimeout(self.socket_timeout_s)
                sock.sendall(header)
                sock.sendall(payload)

                try:
                    ack = sock.recv(128)
                    ack_text = ack.decode(errors='ignore').strip()
                    self.get_logger().info(f'ESP32 image ACK: {ack_text}')
                except socket.timeout:
                    self.get_logger().warn('No ACK from ESP32 image TCP')

            return True

        except Exception as exc:
            self.get_logger().warn(f'Failed to send TCP image: {exc}')
            return False

    @staticmethod
    def letterbox_bgr(img_bgr, target_w, target_h):
        h, w = img_bgr.shape[:2]

        scale = min(target_w / float(w), target_h / float(h))
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))

        resized = cv2.resize(
            img_bgr,
            (new_w, new_h),
            interpolation=cv2.INTER_AREA
        )

        canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)

        x = (target_w - new_w) // 2
        y = (target_h - new_h) // 2

        canvas[y:y + new_h, x:x + new_w] = resized

        return canvas

    @staticmethod
    def bgr_to_rgb565_le(img_bgr):
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        r = (rgb[:, :, 0].astype(np.uint16) >> 3) & 0x1F
        g = (rgb[:, :, 1].astype(np.uint16) >> 2) & 0x3F
        b = (rgb[:, :, 2].astype(np.uint16) >> 3) & 0x1F

        rgb565 = (r << 11) | (g << 5) | b

        return rgb565.astype('<u2').tobytes()


def main(args=None):
    rclpy.init(args=args)
    node = Esp32AlertBridgeNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()