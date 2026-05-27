#!/usr/bin/env python3
import math
import sys
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String


class WebTeleopNode(Node):
    def __init__(self):
        super().__init__('amr_web_teleop_node')

        self.declare_parameter('cmd_vel_topic', '/cmd_vel_safe')
        self.declare_parameter('publish_rate_hz', 20.0)
        self.declare_parameter('key_timeout_s', 0.35)
        self.declare_parameter('linear_speed', 0.12)
        self.declare_parameter('angular_speed', 0.28)

        self.cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self.publish_rate_hz = float(self.get_parameter('publish_rate_hz').value)
        self.key_timeout_s = float(self.get_parameter('key_timeout_s').value)
        self.linear_speed = float(self.get_parameter('linear_speed').value)
        self.angular_speed = float(self.get_parameter('angular_speed').value)

        self.cmd_pub = self.create_publisher(Twist, self.cmd_vel_topic, 10)
        self.key_sub = self.create_subscription(String, '/amr_web_teleop/key', self.on_key, 10)
        self.speed_sub = self.create_subscription(Twist, '/amr_web_teleop/speed', self.on_speed, 10)

        self.active_key = 'k'
        self.last_key_time = 0.0

        period = 1.0 / max(self.publish_rate_hz, 1.0)
        self.timer = self.create_timer(period, self.on_timer)

        self.get_logger().warn('AMR Web Teleop Node started')
        self.get_logger().warn(f'Publish topic: {self.cmd_vel_topic}')
        self.get_logger().warn('Key topic    : /amr_web_teleop/key')
        self.get_logger().warn('Speed topic  : /amr_web_teleop/speed')
        self.get_logger().warn('Keys: u i o / j k l / m , .')

    def on_speed(self, msg: Twist):
        if math.isfinite(msg.linear.x) and msg.linear.x > 0.0:
            self.linear_speed = float(msg.linear.x)
        if math.isfinite(msg.angular.z) and msg.angular.z > 0.0:
            self.angular_speed = float(msg.angular.z)
        self.get_logger().info(
            f'speed updated: linear={self.linear_speed:.3f}, angular={self.angular_speed:.3f}',
            throttle_duration_sec=1.0,
        )

    def on_key(self, msg: String):
        key = (msg.data or '').strip()
        allowed = {'u', 'i', 'o', 'j', 'k', 'l', 'm', ',', '.', ' '}
        if key not in allowed:
            key = 'k'

        if key == ' ':
            key = 'k'

        self.active_key = key
        self.last_key_time = time.monotonic()

        if key == 'k':
            self.publish_zero()

    def twist_from_key(self, key: str) -> Twist:
        msg = Twist()
        v = self.linear_speed
        w = self.angular_speed

        # teleop_twist_keyboard default mapping
        if key == 'i':
            msg.linear.x = v
        elif key == ',':
            msg.linear.x = -v
        elif key == 'j':
            msg.angular.z = w
        elif key == 'l':
            msg.angular.z = -w
        elif key == 'u':
            msg.linear.x = v
            msg.angular.z = w
        elif key == 'o':
            msg.linear.x = v
            msg.angular.z = -w
        elif key == 'm':
            msg.linear.x = -v
            msg.angular.z = -w
        elif key == '.':
            msg.linear.x = -v
            msg.angular.z = w
        return msg

    def publish_zero(self):
        self.cmd_pub.publish(Twist())

    def on_timer(self):
        now = time.monotonic()
        if self.active_key == 'k' or (now - self.last_key_time) > self.key_timeout_s:
            self.publish_zero()
            return

        self.cmd_pub.publish(self.twist_from_key(self.active_key))


def main():
    rclpy.init()
    node = WebTeleopNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Send zero a few times on shutdown
        for _ in range(5):
            node.publish_zero()
            rclpy.spin_once(node, timeout_sec=0.02)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
