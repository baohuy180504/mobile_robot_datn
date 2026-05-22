#!/usr/bin/env python3

import math
import time

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseWithCovarianceStamped


def yaw_to_quaternion(yaw: float):
    qz = math.sin(yaw / 2.0)
    qw = math.cos(yaw / 2.0)
    return 0.0, 0.0, qz, qw


class AutoInitialPoseNode(Node):
    """
    Publish initial pose HOME cho AMCL.

    Mục tiêu:
    - Khi START hệ thống, nếu xe đang ở HOME thật sự,
      AMCL tự nhận pose map->odom mà không cần đặt 2D Pose Estimate trong RViz.
    - Node này không điều khiển xe, không publish /cmd_vel.
    """

    def __init__(self):
        super().__init__('auto_initial_pose_node')

        self.declare_parameter('enabled', True)

        self.declare_parameter('initial_pose_topic', '/initialpose')
        self.declare_parameter('frame_id', 'map')

        self.declare_parameter('initial_x', 0.0)
        self.declare_parameter('initial_y', 0.0)
        self.declare_parameter('initial_yaw', 0.0)

        self.declare_parameter('covariance_x', 0.05)
        self.declare_parameter('covariance_y', 0.05)
        self.declare_parameter('covariance_yaw', 0.05)

        self.declare_parameter('start_delay_s', 2.0)
        self.declare_parameter('publish_count', 10)
        self.declare_parameter('publish_period_s', 0.3)

        self.enabled = bool(self.get_parameter('enabled').value)

        self.initial_pose_topic = self.get_parameter('initial_pose_topic').value
        self.frame_id = self.get_parameter('frame_id').value

        self.initial_x = float(self.get_parameter('initial_x').value)
        self.initial_y = float(self.get_parameter('initial_y').value)
        self.initial_yaw = float(self.get_parameter('initial_yaw').value)

        self.covariance_x = float(self.get_parameter('covariance_x').value)
        self.covariance_y = float(self.get_parameter('covariance_y').value)
        self.covariance_yaw = float(self.get_parameter('covariance_yaw').value)

        self.start_delay_s = max(0.0, float(self.get_parameter('start_delay_s').value))
        self.publish_count = max(1, int(self.get_parameter('publish_count').value))
        self.publish_period_s = max(0.05, float(self.get_parameter('publish_period_s').value))

        self.pub = self.create_publisher(
            PoseWithCovarianceStamped,
            self.initial_pose_topic,
            10
        )

        self.sent_count = 0
        self.start_time = time.time()
        self.done = False

        self.timer = self.create_timer(self.publish_period_s, self.timer_callback)

        self.get_logger().warn('Auto Initial Pose Node started')
        self.get_logger().warn(
            f'HOME initial pose: x={self.initial_x:.3f}, '
            f'y={self.initial_y:.3f}, yaw={self.initial_yaw:.3f}'
        )
        self.get_logger().warn(f'Publish topic: {self.initial_pose_topic}')

    def timer_callback(self):
        if self.done:
            return

        if not self.enabled:
            self.get_logger().warn('Auto initial pose disabled')
            self.done = True
            return

        now = time.time()

        if now - self.start_time < self.start_delay_s:
            return

        msg = PoseWithCovarianceStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id

        msg.pose.pose.position.x = self.initial_x
        msg.pose.pose.position.y = self.initial_y
        msg.pose.pose.position.z = 0.0

        qx, qy, qz, qw = yaw_to_quaternion(self.initial_yaw)
        msg.pose.pose.orientation.x = qx
        msg.pose.pose.orientation.y = qy
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw

        cov = [0.0] * 36
        cov[0] = self.covariance_x
        cov[7] = self.covariance_y
        cov[35] = self.covariance_yaw
        msg.pose.covariance = cov

        self.pub.publish(msg)
        self.sent_count += 1

        self.get_logger().info(
            f'Published HOME initial pose {self.sent_count}/{self.publish_count}'
        )

        if self.sent_count >= self.publish_count:
            self.get_logger().warn('Auto initial pose publish done')
            self.done = True


def main(args=None):
    rclpy.init(args=args)
    node = AutoInitialPoseNode()

    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()