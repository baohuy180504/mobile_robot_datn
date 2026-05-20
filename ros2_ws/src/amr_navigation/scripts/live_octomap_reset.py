#!/usr/bin/env python3

import time
import rclpy
from rclpy.node import Node
from std_srvs.srv import Empty


class LiveOctomapReset(Node):
    def __init__(self):
        super().__init__('live_octomap_reset')

        self.declare_parameter(
            'reset_service',
            '/live_octomap/live_octomap_server/reset'
        )
        self.declare_parameter('reset_period_s', 1.0)
        self.declare_parameter('enabled', True)

        self.reset_service = self.get_parameter('reset_service').value
        self.reset_period_s = float(self.get_parameter('reset_period_s').value)
        self.enabled = bool(self.get_parameter('enabled').value)

        self.client = self.create_client(Empty, self.reset_service)
        self.last_warn_time = 0.0
        self.reset_count = 0

        self.timer = self.create_timer(self.reset_period_s, self.on_timer)

        self.get_logger().warn(
            f'Live Octomap reset started: service={self.reset_service}, '
            f'period={self.reset_period_s:.2f}s, enabled={self.enabled}'
        )

    def on_timer(self):
        if not self.enabled:
            return

        if not self.client.service_is_ready():
            now = time.time()
            if now - self.last_warn_time > 2.0:
                self.get_logger().warn(
                    f'Reset service not ready: {self.reset_service}'
                )
                self.last_warn_time = now
            return

        future = self.client.call_async(Empty.Request())
        future.add_done_callback(self.on_reset_done)

    def on_reset_done(self, future):
        try:
            future.result()
            self.reset_count += 1

            if self.reset_count % 10 == 0:
                self.get_logger().info(
                    f'Live Octomap reset count: {self.reset_count}'
                )

        except Exception as exc:
            self.get_logger().error(f'Live Octomap reset failed: {exc}')


def main(args=None):
    rclpy.init(args=args)
    node = LiveOctomapReset()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
