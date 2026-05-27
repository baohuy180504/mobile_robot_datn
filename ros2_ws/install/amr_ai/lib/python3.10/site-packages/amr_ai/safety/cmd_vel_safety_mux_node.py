#!/usr/bin/env python3

import math
import inspect
import time
from typing import Optional

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan

from amr_interfaces.msg import AiMode, PersonTarget


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def normalize_angle(angle: float) -> float:
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


class CmdVelSafetyMuxNode(Node):
    """
    Chọn nguồn cmd_vel an toàn:

    - FOLLOW_ACTIVE:
        lấy /cmd_vel_follow từ follow_servo_node.

    - NAV_TO_ZONE / RETURN_TO_ZONE:
        lấy /cmd_vel từ Nav2.

    - IDLE / FOLLOW_STOPPED / EMERGENCY_STOP:
        publish zero.

    Safety:
    - FOLLOW_ACTIVE mà target lost/timeout -> zero.
    - LiDAR phía trước quá gần -> zero.
    - LiDAR trong vùng slowdown -> giảm linear.x.
    """

    def __init__(self):
        super().__init__('cmd_vel_safety_mux_node')

        self.declare_parameter('nav_cmd_topic', '/cmd_vel')
        self.declare_parameter('follow_cmd_topic', '/cmd_vel_follow')
        self.declare_parameter('localize_cmd_topic', '/cmd_vel_localize')
        self.declare_parameter('output_cmd_topic', '/cmd_vel_safe')

        self.declare_parameter('mode_topic', '/amr_ai/mode')
        self.declare_parameter('target_topic', '/amr_ai/person_target')
        self.declare_parameter('scan_topic', '/scan_filtered')

        self.declare_parameter('mux_rate_hz', 20.0)

        self.declare_parameter('target_timeout_s', 0.7)
        self.declare_parameter('command_timeout_s', 0.5)
        self.declare_parameter('scan_timeout_s', 0.5)
        self.declare_parameter('require_scan_for_motion', True)

        self.declare_parameter('front_center_angle_rad', 0.0)
        self.declare_parameter('front_angle_deg', 35.0)
        self.declare_parameter('emergency_stop_distance_m', 0.45)
        self.declare_parameter('slowdown_distance_m', 0.80)

        self.nav_cmd_topic = self.get_parameter('nav_cmd_topic').value
        self.follow_cmd_topic = self.get_parameter('follow_cmd_topic').value
        self.localize_cmd_topic = self.get_parameter('localize_cmd_topic').value
        self.output_cmd_topic = self.get_parameter('output_cmd_topic').value

        self.mode_topic = self.get_parameter('mode_topic').value
        self.target_topic = self.get_parameter('target_topic').value
        self.scan_topic = self.get_parameter('scan_topic').value

        self.mux_rate_hz = float(self.get_parameter('mux_rate_hz').value)

        self.target_timeout_s = float(self.get_parameter('target_timeout_s').value)
        self.command_timeout_s = float(self.get_parameter('command_timeout_s').value)
        self.scan_timeout_s = float(self.get_parameter('scan_timeout_s').value)
        self.require_scan_for_motion = bool(self.get_parameter('require_scan_for_motion').value)

        self.front_center_angle_rad = float(self.get_parameter('front_center_angle_rad').value)
        self.front_angle_rad = math.radians(float(self.get_parameter('front_angle_deg').value))
        self.emergency_stop_distance_m = float(self.get_parameter('emergency_stop_distance_m').value)
        self.slowdown_distance_m = float(self.get_parameter('slowdown_distance_m').value)

        self.current_mode = AiMode.IDLE

        self.last_nav_cmd: Optional[Twist] = None
        self.last_nav_cmd_time = 0.0

        self.last_follow_cmd: Optional[Twist] = None
        self.last_follow_cmd_time = 0.0

        self.last_localize_cmd: Optional[Twist] = None
        self.last_localize_cmd_time = 0.0

        self.last_target: Optional[PersonTarget] = None
        self.last_target_time = 0.0

        self.front_min_distance = math.inf
        self.last_scan_time = 0.0

        self.output_pub = self.create_publisher(
            Twist,
            self.output_cmd_topic,
            10
        )

        self.mode_sub = self.create_subscription(
            AiMode,
            self.mode_topic,
            self.mode_callback,
            10
        )

        self.target_sub = self.create_subscription(
            PersonTarget,
            self.target_topic,
            self.target_callback,
            10
        )

        self.nav_cmd_sub = self.create_subscription(
            Twist,
            self.nav_cmd_topic,
            self.nav_cmd_callback,
            10
        )

        self.follow_cmd_sub = self.create_subscription(
            Twist,
            self.follow_cmd_topic,
            self.follow_cmd_callback,
            10
        )

        self.localize_cmd_sub = self.create_subscription(
            Twist,
            self.localize_cmd_topic,
            self.localize_cmd_callback,
            10
        )

        self.scan_sub = self.create_subscription(
            LaserScan,
            self.scan_topic,
            self.scan_callback,
            10
        )

        period = 1.0 / max(1.0, self.mux_rate_hz)
        self.timer = self.create_timer(period, self.timer_callback)

        self.get_logger().warn('Cmd Vel Safety Mux started')
        self.get_logger().warn(f'Nav2 cmd      : {self.nav_cmd_topic}')
        self.get_logger().warn(f'Follow cmd    : {self.follow_cmd_topic}')
        self.get_logger().warn(f'Localize cmd  : {self.localize_cmd_topic}')
        self.get_logger().warn(f'Output cmd    : {self.output_cmd_topic}')
        self.get_logger().warn(f'Scan topic  : {self.scan_topic}')
        self.get_logger().warn(f'front_center_angle_rad={self.front_center_angle_rad:.2f}')

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
        self.current_mode = int(msg.mode)

    def target_callback(self, msg: PersonTarget):
        self.last_target = msg
        self.last_target_time = time.time()

    def nav_cmd_callback(self, msg: Twist):
        self.last_nav_cmd = msg
        self.last_nav_cmd_time = time.time()

    def follow_cmd_callback(self, msg: Twist):
        self.last_follow_cmd = msg
        self.last_follow_cmd_time = time.time()

    def localize_cmd_callback(self, msg: Twist):
        self.last_localize_cmd = msg
        self.last_localize_cmd_time = time.time()

    def scan_callback(self, msg: LaserScan):
        self.front_min_distance = self.compute_front_min_distance(msg)
        self.last_scan_time = time.time()

    # ==========================================================
    # Main mux
    # ==========================================================
    def timer_callback(self):
        now = time.time()
        selected_cmd = Twist()
        source = 'zero'

        if self.current_mode == AiMode.FOLLOW_ACTIVE:
            if not self.is_target_safe(now):
                self.publish_zero()
                return

            if self.is_command_recent(self.last_follow_cmd_time, now):
                selected_cmd = self.copy_twist(self.last_follow_cmd)
                source = 'follow'
            else:
                self.log_warn_throttle(0.5, 'Follow cmd timeout: stop')
                self.publish_zero()
                return

        elif self.current_mode in [AiMode.NAV_TO_ZONE, AiMode.RETURN_TO_ZONE]:
            if self.is_command_recent(self.last_nav_cmd_time, now):
                selected_cmd = self.copy_twist(self.last_nav_cmd)
                source = 'nav2'
            else:
                self.publish_zero()
                return

        elif self.current_mode == AiMode.LOCALIZING:
            if self.is_command_recent(self.last_localize_cmd_time, now):
                selected_cmd = self.copy_twist(self.last_localize_cmd)
                source = 'localize'
            else:
                self.log_warn_throttle(0.5, 'Localize cmd timeout: stop')
                self.publish_zero()
                return

        else:
            self.publish_zero()
            return

        safe_cmd = self.apply_lidar_safety(selected_cmd, source, now)
        self.output_pub.publish(safe_cmd)

    def is_command_recent(self, stamp_time: float, now: float) -> bool:
        return stamp_time > 0.0 and (now - stamp_time) <= self.command_timeout_s

    def is_target_safe(self, now: float) -> bool:
        if self.last_target is None:
            self.log_warn_throttle(0.5, 'No target yet: stop')
            return False

        if now - self.last_target_time > self.target_timeout_s:
            self.log_warn_throttle(0.5, 'Target timeout in safety mux: stop')
            return False

        if self.last_target.lost:
            self.log_warn_throttle(0.5, 'Target lost in safety mux: stop')
            return False

        if not math.isfinite(float(self.last_target.distance_m)):
            self.log_warn_throttle(0.5, 'Target distance invalid in safety mux: stop')
            return False

        if not math.isfinite(float(self.last_target.angle_rad)):
            self.log_warn_throttle(0.5, 'Target angle invalid in safety mux: stop')
            return False

        return True

    # ==========================================================
    # LiDAR safety
    # ==========================================================
    def compute_front_min_distance(self, scan: LaserScan) -> float:
        front_min = math.inf
        angle = float(scan.angle_min)

        for r in scan.ranges:
            if math.isfinite(r):
                r = float(r)

                if scan.range_min <= r <= scan.range_max:
                    diff = abs(normalize_angle(angle - self.front_center_angle_rad))

                    if diff <= self.front_angle_rad:
                        front_min = min(front_min, r)

            angle += float(scan.angle_increment)

        return front_min

    def apply_lidar_safety(self, cmd: Twist, source: str, now: float) -> Twist:
        if self.require_scan_for_motion:
            if now - self.last_scan_time > self.scan_timeout_s:
                self.log_warn_throttle(0.5, 'Scan timeout: stop')
                return Twist()

        front_min = self.front_min_distance

        if math.isfinite(front_min):
            if front_min <= self.emergency_stop_distance_m:
                self.log_warn_throttle(
                    0.5,
                    f'EMERGENCY LiDAR stop: front_min={front_min:.2f} m, source={source}'
                )
                return Twist()

            if (
                front_min < self.slowdown_distance_m
                and cmd.linear.x > 0.0
            ):
                scale = (
                    (front_min - self.emergency_stop_distance_m)
                    / max(0.01, self.slowdown_distance_m - self.emergency_stop_distance_m)
                )
                scale = clamp(scale, 0.0, 1.0)

                cmd.linear.x *= scale

                self.log_info_throttle(
                    0.5,
                    f'LiDAR slowdown: front_min={front_min:.2f} m, scale={scale:.2f}'
                )

        return cmd

    # ==========================================================
    # Helpers
    # ==========================================================
    def copy_twist(self, msg: Optional[Twist]) -> Twist:
        out = Twist()

        if msg is None:
            return out

        out.linear.x = msg.linear.x
        out.linear.y = msg.linear.y
        out.linear.z = msg.linear.z

        out.angular.x = msg.angular.x
        out.angular.y = msg.angular.y
        out.angular.z = msg.angular.z

        return out

    def publish_zero(self):
        self.output_pub.publish(Twist())


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelSafetyMuxNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()