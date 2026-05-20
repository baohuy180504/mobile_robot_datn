#!/usr/bin/env python3

import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import PointCloud2
from std_srvs.srv import Empty


class LiveOctomapManager(Node):
    """
    Quản lý live Octomap an toàn:
    - Nhận /octomap_cloud
    - Publish sang /live_octomap_cloud
    - Định kỳ pause cloud -> reset live octomap -> resume cloud

    Mục tiêu:
    - Live Octomap có bộ nhớ ngắn giống costmap động
    - Không reset khi octomap_server đang liên tục nhận cloud
    """

    def __init__(self):
        super().__init__('live_octomap_manager')

        self.declare_parameter('input_cloud_topic', '/octomap_cloud')
        self.declare_parameter('output_cloud_topic', '/live_octomap_cloud')
        self.declare_parameter('reset_service', '/live_octomap/live_octomap_server/reset')

        self.declare_parameter('reset_period_s', 1.0)
        self.declare_parameter('post_reset_pause_s', 0.15)
        self.declare_parameter('enabled', True)

        self.input_cloud_topic = self.get_parameter('input_cloud_topic').value
        self.output_cloud_topic = self.get_parameter('output_cloud_topic').value
        self.reset_service = self.get_parameter('reset_service').value

        self.reset_period_s = float(self.get_parameter('reset_period_s').value)
        self.post_reset_pause_s = float(self.get_parameter('post_reset_pause_s').value)
        self.enabled = bool(self.get_parameter('enabled').value)

        self.paused = False
        self.reset_in_progress = False
        self.resume_time = 0.0
        self.last_reset_start = 0.0
        self.last_warn_time = 0.0
        self.pass_count = 0
        self.drop_count = 0
        self.reset_count = 0

        self.cloud_pub = self.create_publisher(
            PointCloud2,
            self.output_cloud_topic,
            qos_profile_sensor_data
        )

        self.cloud_sub = self.create_subscription(
            PointCloud2,
            self.input_cloud_topic,
            self.cloud_callback,
            qos_profile_sensor_data
        )

        self.reset_client = self.create_client(
            Empty,
            self.reset_service
        )

        self.timer = self.create_timer(0.05, self.timer_callback)

        self.get_logger().warn(
            f'Live Octomap Manager started | '
            f'{self.input_cloud_topic} -> {self.output_cloud_topic}, '
            f'reset_service={self.reset_service}, '
            f'reset_period={self.reset_period_s:.2f}s'
        )

    def cloud_callback(self, msg: PointCloud2):
        if self.paused or self.reset_in_progress:
            self.drop_count += 1
            return

        self.cloud_pub.publish(msg)
        self.pass_count += 1

    def timer_callback(self):
        now = time.time()

        if not self.enabled:
            return

        # Resume sau khi reset xong và đã đợi một khoảng ngắn
        if self.paused and not self.reset_in_progress and self.resume_time > 0.0:
            if now >= self.resume_time:
                self.paused = False
                self.resume_time = 0.0
                self.get_logger().info(
                    f'Resume live cloud | reset_count={self.reset_count}, '
                    f'pass={self.pass_count}, drop={self.drop_count}'
                )

        if self.reset_in_progress:
            return

        if now - self.last_reset_start < self.reset_period_s:
            return

        if not self.reset_client.service_is_ready():
            if now - self.last_warn_time > 2.0:
                self.get_logger().warn(
                    f'Reset service not ready: {self.reset_service}'
                )
                self.last_warn_time = now
            return

        self.start_reset(now)

    def start_reset(self, now):
        self.paused = True
        self.reset_in_progress = True
        self.last_reset_start = now

        future = self.reset_client.call_async(Empty.Request())
        future.add_done_callback(self.reset_done_callback)

    def reset_done_callback(self, future):
        try:
            future.result()
            self.reset_count += 1

            if self.reset_count % 10 == 0:
                self.get_logger().info(
                    f'Live Octomap reset count={self.reset_count}, '
                    f'pass={self.pass_count}, drop={self.drop_count}'
                )

        except Exception as exc:
            self.get_logger().error(f'Live Octomap reset failed: {exc}')

        self.reset_in_progress = False
        self.resume_time = time.time() + self.post_reset_pause_s


def main(args=None):
    rclpy.init(args=args)
    node = LiveOctomapManager()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
