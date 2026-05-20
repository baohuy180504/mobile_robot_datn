#!/usr/bin/env python3

import math
import inspect
import time
from typing import Optional

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist

from amr_interfaces.msg import AiMode, PersonTarget


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


class FollowServoNode(Node):
    """
    Visual servo bám người bằng /amr_ai/person_target.

    Mục tiêu:
    - Giữ target gần giữa khung hình bằng angle_rad.
    - Giữ khoảng cách follow_distance_m bằng distance_m.
    - Publish /cmd_vel_follow.
    - Không publish trực tiếp /cmd_vel để tránh xung đột Nav2.
    """

    def __init__(self):
        super().__init__('follow_servo_node')

        self.declare_parameter('follow_distance_m', 2.0)
        self.declare_parameter('distance_tolerance_m', 0.25)

        self.declare_parameter('k_linear', 0.35)
        self.declare_parameter('k_angular', 1.25)

        self.declare_parameter('max_linear_x', 0.25)
        self.declare_parameter('min_linear_x', 0.03)
        self.declare_parameter('max_angular_z', 0.75)

        self.declare_parameter('angle_deadband_rad', 0.08)

        # Góc dùng để giảm tốc theo độ lệch target.
        # Target càng lệch tâm, xe càng giảm linear.x nhưng vẫn vừa tiến vừa cua.
        self.declare_parameter('slow_angle_rad', 0.70)
        self.declare_parameter('min_angle_speed_scale', 0.25)

        # Chỉ khi lệch quá lớn mới xoay tại chỗ.
        self.declare_parameter('hard_rotate_angle_rad', 0.85)

        # Với camera optical frame: angle_rad > 0 thường là target lệch sang phải ảnh.
        # Robot ROS angular.z > 0 là quay trái, nên mặc định angular_sign = -1.0.
        # Nếu test thấy xe quay ngược hướng, đổi thành +1.0 trong yaml.
        self.declare_parameter('angular_sign', -1.0)

        self.declare_parameter('target_timeout_s', 0.7)
        self.declare_parameter('command_rate_hz', 15.0)
        self.declare_parameter('cmd_vel_follow_topic', '/cmd_vel_follow')

        self.declare_parameter('enable_smoothing', True)
        self.declare_parameter('smoothing_alpha', 0.65)

        self.follow_distance_m = float(self.get_parameter('follow_distance_m').value)
        self.distance_tolerance_m = float(self.get_parameter('distance_tolerance_m').value)

        self.k_linear = float(self.get_parameter('k_linear').value)
        self.k_angular = float(self.get_parameter('k_angular').value)

        self.max_linear_x = float(self.get_parameter('max_linear_x').value)
        self.min_linear_x = float(self.get_parameter('min_linear_x').value)
        self.max_angular_z = float(self.get_parameter('max_angular_z').value)

        self.angle_deadband_rad = float(self.get_parameter('angle_deadband_rad').value)

        self.slow_angle_rad = float(self.get_parameter('slow_angle_rad').value)
        self.min_angle_speed_scale = float(self.get_parameter('min_angle_speed_scale').value)
        self.hard_rotate_angle_rad = float(self.get_parameter('hard_rotate_angle_rad').value)

        self.slow_angle_rad = max(0.05, self.slow_angle_rad)
        self.min_angle_speed_scale = clamp(self.min_angle_speed_scale, 0.0, 1.0)
        self.hard_rotate_angle_rad = max(self.angle_deadband_rad, self.hard_rotate_angle_rad)

        self.angular_sign = float(self.get_parameter('angular_sign').value)

        self.target_timeout_s = float(self.get_parameter('target_timeout_s').value)
        self.command_rate_hz = float(self.get_parameter('command_rate_hz').value)
        self.cmd_vel_follow_topic = self.get_parameter('cmd_vel_follow_topic').value

        self.enable_smoothing = bool(self.get_parameter('enable_smoothing').value)
        self.smoothing_alpha = float(self.get_parameter('smoothing_alpha').value)
        self.smoothing_alpha = clamp(self.smoothing_alpha, 0.0, 1.0)

        self.current_mode = AiMode.IDLE
        self.last_target: Optional[PersonTarget] = None
        self.last_target_time = 0.0

        self.prev_linear_x = 0.0
        self.prev_angular_z = 0.0

        self.cmd_pub = self.create_publisher(
            Twist,
            self.cmd_vel_follow_topic,
            10
        )

        self.mode_sub = self.create_subscription(
            AiMode,
            '/amr_ai/mode',
            self.mode_callback,
            10
        )

        self.target_sub = self.create_subscription(
            PersonTarget,
            '/amr_ai/person_target',
            self.target_callback,
            10
        )

        period = 1.0 / max(1.0, self.command_rate_hz)
        self.timer = self.create_timer(period, self.timer_callback)

        self.get_logger().info('Follow Servo Node started')
        self.get_logger().info(f'follow_distance_m={self.follow_distance_m}')
        self.get_logger().info(f'cmd_vel_follow_topic={self.cmd_vel_follow_topic}')
        self.get_logger().info(f'angular_sign={self.angular_sign}')

    # ==========================================================
    # Throttled logging helpers
    # ==========================================================
    def _log_throttle(self, level: str, period_sec: float, message: str):
        if not hasattr(self, "_last_throttle_log_time"):
            self._last_throttle_log_time = {}

        caller = inspect.currentframe().f_back
        key = f"{level}:{caller.f_lineno}"

        now = time.time()
        last = self._last_throttle_log_time.get(key, 0.0)

        if now - last < float(period_sec):
            return

        self._last_throttle_log_time[key] = now

        if level == "warn":
            self.get_logger().warn(message)
        else:
            self.get_logger().info(message)

    def log_info_throttle(self, period_sec: float, message: str):
        self._log_throttle("info", period_sec, message)

    def log_warn_throttle(self, period_sec: float, message: str):
        self._log_throttle("warn", period_sec, message)

    # ==========================================================
    # ROS callbacks
    # ==========================================================
    def mode_callback(self, msg: AiMode):
        old_mode = self.current_mode
        self.current_mode = int(msg.mode)

        if old_mode == AiMode.FOLLOW_ACTIVE and self.current_mode != AiMode.FOLLOW_ACTIVE:
            self.get_logger().warn('Exit FOLLOW_ACTIVE: publish zero follow command')
            self.publish_zero(reset_filter=True)

    def target_callback(self, msg: PersonTarget):
        self.last_target = msg
        self.last_target_time = time.time()

    def timer_callback(self):
        if self.current_mode != AiMode.FOLLOW_ACTIVE:
            self.publish_zero(reset_filter=True)
            return

        if self.last_target is None:
            self.log_warn_throttle(1.0, 'No person target received')
            self.publish_zero(reset_filter=True)
            return

        if time.time() - self.last_target_time > self.target_timeout_s:
            self.log_warn_throttle(0.5, 'Target timeout: stop follow servo')
            self.publish_zero(reset_filter=True)
            return

        if self.last_target.lost:
            self.log_warn_throttle(0.5, 'Target lost: stop follow servo')
            self.publish_zero(reset_filter=True)
            return

        distance_m = float(self.last_target.distance_m)
        angle_rad = float(self.last_target.angle_rad)

        if not math.isfinite(distance_m) or not math.isfinite(angle_rad):
            self.log_warn_throttle(0.5, 'Target distance/angle invalid: stop follow servo')
            self.publish_zero(reset_filter=True)
            return

        linear_x, angular_z = self.compute_servo_command(distance_m, angle_rad)

        self.publish_command(linear_x, angular_z)

        self.log_info_throttle(
            0.5,
            f'servo: dist={distance_m:.2f}, angle={angle_rad:.2f}, '
            f'vx={linear_x:.2f}, wz={angular_z:.2f}'
        )

    # ==========================================================
    # Control law
    # ==========================================================
    def compute_servo_command(self, distance_m: float, angle_rad: float):
        abs_angle = abs(angle_rad)
        distance_error = distance_m - self.follow_distance_m

        # Angular control: giữ người ở giữa ảnh.
        if abs_angle < self.angle_deadband_rad:
            angular_z = 0.0
        else:
            angular_z = self.angular_sign * self.k_angular * angle_rad
            angular_z = clamp(angular_z, -self.max_angular_z, self.max_angular_z)

        # Linear control: chỉ tiến, không lùi trong giai đoạn này.
        if distance_error <= self.distance_tolerance_m:
            linear_x = 0.0
        else:
            linear_x = self.k_linear * distance_error
            linear_x = clamp(linear_x, 0.0, self.max_linear_x)

            if 0.0 < linear_x < self.min_linear_x:
                linear_x = self.min_linear_x

        # Giảm tốc tuyến tính theo góc lệch, thay vì cắt cứng.
        # Khi target gần giữa ảnh: scale gần 1.0
        # Khi target lệch vừa: vẫn cho xe vừa tiến vừa cua
        # Khi target lệch quá lớn: hard rotate phía dưới sẽ cắt linear.x = 0
        angle_scale = 1.0 - min(abs_angle / self.slow_angle_rad, 1.0)
        angle_scale = max(self.min_angle_speed_scale, angle_scale)

        linear_x *= angle_scale

        # Chỉ xoay tại chỗ khi target lệch cực lớn.
        if abs_angle >= self.hard_rotate_angle_rad:
            linear_x = 0.0

        # Làm mượt lệnh, nhưng không làm mượt qua trạng thái zero khẩn.
        if self.enable_smoothing:
            alpha = self.smoothing_alpha
            linear_x = alpha * linear_x + (1.0 - alpha) * self.prev_linear_x
            angular_z = alpha * angular_z + (1.0 - alpha) * self.prev_angular_z

        self.prev_linear_x = linear_x
        self.prev_angular_z = angular_z

        return linear_x, angular_z

    def publish_command(self, linear_x: float, angular_z: float):
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.angular.z = float(angular_z)
        self.cmd_pub.publish(msg)

    def publish_zero(self, reset_filter: bool = False):
        if reset_filter:
            self.prev_linear_x = 0.0
            self.prev_angular_z = 0.0

        msg = Twist()
        self.cmd_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = FollowServoNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()