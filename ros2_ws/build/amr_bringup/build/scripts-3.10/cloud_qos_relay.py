#!/usr/bin/python3
"""
cloud_qos_relay.py

Relay PointCloud2 cho OctoMap:
- Subscribe /camera/depth/points bằng SensorData QoS kiểu BEST_EFFORT.
- Publish /octomap_cloud bằng RELIABLE QoS để octomap_server nhận ổn định hơn.
- Giữ nguyên header.stamp và frame_id của camera để octomap_server tự transform qua TF.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    QoSHistoryPolicy,
    QoSReliabilityPolicy,
    QoSDurabilityPolicy,
)
from sensor_msgs.msg import PointCloud2


class CloudQosRelay(Node):
    def __init__(self):
        super().__init__('cloud_qos_relay')

        self.declare_parameter('input_topic', '/camera/depth/points')
        self.declare_parameter('output_topic', '/octomap_cloud')
        self.declare_parameter('max_publish_hz', 5.0)
        self.declare_parameter('force_frame_id', '')

        self.input_topic = self.get_parameter('input_topic').value
        self.output_topic = self.get_parameter('output_topic').value
        self.max_publish_hz = float(self.get_parameter('max_publish_hz').value)
        self.force_frame_id = self.get_parameter('force_frame_id').value

        self.declare_parameter('restamp', True)
        self.restamp = bool(self.get_parameter('restamp').value)

        self.last_pub_time = None

        sub_qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=5,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
        )

        pub_qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
        )

        self.pub = self.create_publisher(PointCloud2, self.output_topic, pub_qos)
        self.sub = self.create_subscription(PointCloud2, self.input_topic, self.cloud_callback, sub_qos)

        self.get_logger().info(
            f'Relay PointCloud2: {self.input_topic} [BEST_EFFORT] -> '
            f'{self.output_topic} [RELIABLE], max_publish_hz={self.max_publish_hz}'
        )

    def cloud_callback(self, msg: PointCloud2):
        now = self.get_clock().now()

        if self.max_publish_hz > 0.0 and self.last_pub_time is not None:
            min_period_ns = int(1e9 / self.max_publish_hz)
            if (now - self.last_pub_time).nanoseconds < min_period_ns:
                return

        if self.force_frame_id:
            msg.header.frame_id = self.force_frame_id

        if self.restamp:
            msg.header.stamp = self.get_clock().now().to_msg()
            
        self.pub.publish(msg)
        self.last_pub_time = now


def main(args=None):
    rclpy.init(args=args)
    node = CloudQosRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
