#!/usr/bin/env python3

import ipaddress
import os
import re
import socket
import time
import cv2
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from amr_interfaces.msg import AiAlert


class Esp32AlertBridgeNode(Node):
    """
    Chuyển cảnh báo TÉ NGÃ (alert_type='FALL') từ /amr_ai/alert sang ESP32:
      - UDP  : mã lệnh 'A' (ESP32 hiển thị cảnh báo)
      - TCP  : 1 ảnh snapshot RGB565 (lấy từ ảnh debug của ai_detector_node)

    Cảnh báo được gửi ở MỌI chế độ (IDLE, NAV_*, FOLLOW_*, ALERT_STOPPED...).
    Đã bỏ cảnh báo lửa/khói/bảo hộ (mã B, C, D không còn được gửi).

    Địa chỉ ESP32 KHÔNG hardcode trong code/yaml. Thứ tự ưu tiên:
      1) tham số esp32_ip (nếu khác rỗng, dùng để debug/ghi đè tạm)
      2) file network.env:  ESP32_ALERT_IP=..., (tùy chọn) ESP32_ALERT_UDP_PORT,
         ESP32_ALERT_TCP_PORT. File được đọc lại MỖI LẦN có sự cố mới nên đổi
         IP xong không cần restart node. Chưa có IP -> ghi cảnh báo, không gửi.
    ESP32_ALERT_IP có thể là IPv4 HOẶC hostname mDNS (vd amr-display.local, tên do
    firmware màn hình tự quảng bá): khi đó đổi WiFi không phải sửa gì trên Jetson.
    Hostname được phân giải mỗi sự cố mới; nếu lần này phân giải thất bại thì dùng
    lại IP của lần thành công gần nhất.

    Latch: mỗi sự cố FALL chỉ gửi 1 lần (UDP + ảnh). Khi ai_detector trả về
    NORMAL liên tục >= normal_reset_sec thì latch nội bộ được reset để sự cố
    tiếp theo gửi lại được. Màn hình ESP32 KHÔNG tự xóa.
    """

    FALL_CMD = 'A'
    DEFAULT_ENV_FILE = '~/mobile_robot/ros2_ws/config/network.env'
    HOSTNAME_RE = re.compile(r'^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$')

    def __init__(self):
        super().__init__('esp32_alert_bridge_node')

        # Để trống: lấy từ network.env. Chỉ điền khi cần ghi đè tạm để debug.
        self.declare_parameter('esp32_ip', '')
        self.declare_parameter('esp32_udp_port', 4210)
        self.declare_parameter('esp32_tcp_port', 4211)
        self.declare_parameter('network_env_file', self.DEFAULT_ENV_FILE)

        self.declare_parameter('alert_topic', '/amr_ai/alert')
        self.declare_parameter('debug_image_topic', '/amr_ai/debug/alert/image')

        self.declare_parameter('snapshot_width', 296)
        self.declare_parameter('snapshot_height', 296)

        # Chỉ gửi ảnh 1 lần cho mỗi incident
        self.declare_parameter('image_send_delay_s', 0.35)
        self.declare_parameter('image_wait_timeout_s', 2.0)

        self.declare_parameter('normal_reset_sec', 1.0)

        self.declare_parameter('socket_timeout_s', 5.0)

        self.esp32_ip_param = str(self.get_parameter('esp32_ip').value).strip()
        self.esp32_udp_port = int(self.get_parameter('esp32_udp_port').value)
        self.esp32_tcp_port = int(self.get_parameter('esp32_tcp_port').value)
        self.network_env_path = os.path.expanduser(
            str(self.get_parameter('network_env_file').value)
        )

        self.alert_topic = self.get_parameter('alert_topic').value
        self.debug_image_topic = self.get_parameter('debug_image_topic').value

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

        # Latch incident
        self.latched_alert_type = None
        self.normal_since = None

        # Pending image one-shot
        self.pending_image_cmd = None
        self.pending_image_alert_type = None
        self.pending_image_start_time = 0.0
        self.pending_image_due_time = 0.0
        self.pending_target = None

        # Địa chỉ ESP32 lần gần nhất (để log khi thay đổi) và chống spam cảnh báo
        self.last_target = None
        self.host_ip_cache = {}
        self.retry_after = 0.0
        self._last_warn_time = {}

        self.alert_sub = self.create_subscription(
            AiAlert,
            self.alert_topic,
            self.alert_callback,
            10
        )

        self.image_sub = self.create_subscription(
            Image,
            self.debug_image_topic,
            self.debug_image_callback,
            qos_profile_sensor_data
        )

        self.timer = self.create_timer(0.05, self.timer_callback)

        self.get_logger().warn('ESP32 Alert Bridge started - FALL only, LATCH mode')
        self.get_logger().info(f'Network env file: {self.network_env_path}')
        self.get_logger().info(f'Alert topic: {self.alert_topic}')
        self.get_logger().info(f'Debug image topic: {self.debug_image_topic}')

        if self.resolve_target() is None:
            self.get_logger().warn(
                'ESP32 alert IP chưa được cấu hình. Sửa ESP32_ALERT_IP trong '
                f'{self.network_env_path} (không cần restart node).'
            )

    # ==========================================================
    # Địa chỉ ESP32 (network.env)
    # ==========================================================
    def warn_throttled(self, key: str, message: str, period_s: float = 10.0):
        now = time.time()
        if now - self._last_warn_time.get(key, 0.0) >= period_s:
            self._last_warn_time[key] = now
            self.get_logger().warn(message)

    @staticmethod
    def parse_env_file(path: str) -> dict:
        """Đọc file KEY=VALUE (bỏ dòng trống, comment #, 'export ', dấu nháy)."""
        values = {}
        with open(path, 'r', encoding='utf-8') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('export '):
                    line = line[len('export '):].strip()
                if '=' not in line:
                    continue
                key, val = line.split('=', 1)
                val = re.split(r'\s#', val, maxsplit=1)[0]      # bỏ comment cuối dòng
                values[key.strip()] = val.strip().strip('"').strip("'")
        return values

    @staticmethod
    def to_port(value, default: int) -> int:
        try:
            port = int(value)
            if 1 <= port <= 65535:
                return port
        except (TypeError, ValueError):
            pass
        return default

    def is_valid_host(self, host: str) -> bool:
        try:
            ipaddress.IPv4Address(host)
            return True
        except ValueError:
            return bool(self.HOSTNAME_RE.match(host)) and not host.replace('.', '').isdigit()

    def resolve_ip(self, host: str):
        """IPv4 -> giữ nguyên. Hostname (vd amr-display.local) -> IPv4; lỗi thì dùng IP gần nhất."""
        try:
            ipaddress.IPv4Address(host)
            return host
        except ValueError:
            pass

        try:
            ip = socket.gethostbyname(host)
            if self.host_ip_cache.get(host) != ip:
                self.get_logger().warn(f'Phân giải {host} -> {ip}')
            self.host_ip_cache[host] = ip
            return ip
        except OSError as exc:
            cached = self.host_ip_cache.get(host)
            if cached:
                self.warn_throttled(
                    'resolve_cached',
                    f'Không phân giải được {host} ({exc}); dùng IP lần trước: {cached}'
                )
                return cached
            self.warn_throttled(
                'resolve_fail',
                f'Không phân giải được {host}: {exc}. Kiểm tra mDNS trên Jetson '
                f'(avahi-daemon + libnss-mdns) hoặc điền IP vào network.env.'
            )
            return None

    def resolve_target(self):
        """
        Trả về (host, udp_port, tcp_port) hoặc None nếu chưa có / sai cấu hình.
        Đọc lại network.env ở mỗi lần gọi -> đổi IP không cần restart.
        """
        env = {}
        try:
            env = self.parse_env_file(self.network_env_path)
        except FileNotFoundError:
            if not self.esp32_ip_param:
                self.warn_throttled(
                    'env_missing',
                    f'Không thấy file {self.network_env_path}. '
                    f'Tạo file với dòng ESP32_ALERT_IP=<ip màn hình ESP32>.'
                )
        except Exception as exc:
            self.warn_throttled('env_error', f'Không đọc được {self.network_env_path}: {exc}')

        host = self.esp32_ip_param or env.get('ESP32_ALERT_IP', '').strip()
        source = 'param esp32_ip' if self.esp32_ip_param else self.network_env_path

        if not host:
            return None

        if not self.is_valid_host(host):
            self.warn_throttled(
                'bad_host', f'ESP32_ALERT_IP không hợp lệ: {host!r} (nguồn: {source})'
            )
            return None

        ip = self.resolve_ip(host)
        if ip is None:
            return None

        target = (
            ip,
            self.to_port(env.get('ESP32_ALERT_UDP_PORT'), self.esp32_udp_port),
            self.to_port(env.get('ESP32_ALERT_TCP_PORT'), self.esp32_tcp_port),
        )

        if target != self.last_target:
            self.last_target = target
            shown = host if host == ip else f'{host} -> {ip}'
            self.get_logger().warn(
                f'ESP32 alert target: {shown} (UDP {target[1]}, TCP {target[2]}) | nguồn: {source}'
            )

        return target

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

        if alert_type == 'FALL' and bool(msg.active):
            self.handle_fall(alert_type, now)
        elif alert_type == 'NORMAL':
            # NORMAL chỉ reset latch nội bộ, không gửi gì về ESP32
            self.handle_normal(now)
        # Loại khác (FIRE/SMOKE/PPE cũ...): bỏ qua hoàn toàn.

    def handle_fall(self, alert_type: str, now: float):
        self.normal_since = None

        # Cùng sự cố đang latch rồi thì không gửi lại lệnh và ảnh
        if self.latched_alert_type == alert_type:
            return

        # Chưa có địa chỉ ESP32 hợp lệ: KHÔNG latch, để khi cấu hình xong thì
        # sự cố đang diễn ra vẫn được gửi. Thử lại tối đa 1 lần/giây.
        if now < self.retry_after:
            return

        target = self.resolve_target()
        if target is None:
            self.retry_after = now + 1.0
            self.warn_throttled(
                'no_target',
                f'Có cảnh báo {alert_type} nhưng chưa có IP ESP32 hợp lệ -> chưa gửi được.'
            )
            return

        # Cảnh báo mới
        self.latched_alert_type = alert_type
        self.pending_target = target

        self.send_udp_cmd(self.FALL_CMD, target)

        # Đặt lịch gửi ảnh 1 lần sau một khoảng delay ngắn,
        # để debug image mới nhất kịp publish sau alert.
        self.pending_image_cmd = self.FALL_CMD
        self.pending_image_alert_type = alert_type
        self.pending_image_start_time = now
        self.pending_image_due_time = now + self.image_send_delay_s

        self.get_logger().warn(
            f'NEW INCIDENT: {alert_type}, sent cmd={self.FALL_CMD}, image scheduled'
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
            self.pending_target = None

    def timer_callback(self):
        if self.pending_image_cmd is None:
            return

        now = time.time()

        if now < self.pending_image_due_time:
            return

        timed_out = (now - self.pending_image_start_time) > self.image_wait_timeout_s

        # Chờ có ảnh debug
        if self.latest_debug_image is None:
            if timed_out:
                self.get_logger().warn(
                    f'No debug image for {self.pending_image_alert_type}, skip one-shot image'
                )
                self.clear_pending_image()
            return

        # Chờ ảnh mới hơn thời điểm alert một chút
        if self.latest_debug_stamp_sec < self.pending_image_start_time:
            if not timed_out:
                return

            self.get_logger().warn(
                'Debug image not updated after alert, sending latest old frame anyway'
            )

        cmd = self.pending_image_cmd
        alert_type = self.pending_image_alert_type

        ok = self.send_image(cmd, self.latest_debug_image, self.pending_target)

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
        self.pending_target = None

    def send_udp_cmd(self, cmd: str, target):
        host, udp_port, _ = target
        try:
            self.udp_sock.sendto(cmd.encode('ascii'), (host, udp_port))
            self.get_logger().info(f'Sent UDP alert cmd: {cmd} -> {host}:{udp_port}')
        except Exception as exc:
            self.get_logger().warn(f'Failed to send UDP cmd {cmd} to {host}:{udp_port}: {exc}')

    def send_image(self, cmd: str, img_bgr, target) -> bool:
        if img_bgr is None:
            self.get_logger().warn('No image available, skip TCP image')
            return False

        if target is None:
            self.get_logger().warn('No ESP32 target, skip TCP image')
            return False

        host, _, tcp_port = target

        try:
            img = self.letterbox_bgr(
                img_bgr,
                self.snapshot_width,
                self.snapshot_height
            )
            payload = self.bgr_to_rgb565_le(img)

            header = (
                f'AMRI,{cmd},{self.snapshot_width},'
                f'{self.snapshot_height},{len(payload)}\n'
            ).encode('ascii')

            self.get_logger().info(
                f'Sending one-shot image: cmd={cmd} -> {host}:{tcp_port}, '
                f'{self.snapshot_width}x{self.snapshot_height}, '
                f'{len(payload)} bytes'
            )

            with socket.create_connection(
                (host, tcp_port),
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
