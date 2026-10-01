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
    - Xe luôn khởi động tại HOME (WP0 = 0,0,0), nên đây là cách định vị DUY NHẤT
      (đã bỏ chế độ LOCALIZING/auto global localization).
    - Khi START hệ thống, AMCL tự nhận pose map->odom mà không cần đặt
      2D Pose Estimate trong RViz.
    - Node này không điều khiển xe, không publish /cmd_vel.

    Độ tin cậy:
    - Chỉ publish khi đã có subscriber trên /initialpose (AMCL đã lên), thay vì
      publish mù ngay sau start_delay_s (Nav2 có thể chưa sẵn sàng).
    - Tiếp tục publish mỗi publish_period_s cho tới khi /amcl_pose xuất hiện
      SAU lần publish đầu (AMCL đã nhận pose), hoặc hết publish_count / max_wait_s.
    - Đặt wait_for_amcl_confirm=false để quay về hành vi cũ (publish_count lần
      rồi dừng, không chờ xác nhận).
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
        # Số lần publish TỐI ĐA (nếu chờ xác nhận) hoặc số lần publish cố định.
        self.declare_parameter('publish_count', 20)
        self.declare_parameter('publish_period_s', 1.0)

        # Chờ AMCL xác nhận (có /amcl_pose mới) rồi mới dừng publish.
        self.declare_parameter('wait_for_amcl_confirm', True)
        self.declare_parameter('amcl_pose_topic', '/amcl_pose')
        # Tổng thời gian tối đa (từ lúc node khởi động) trước khi bỏ cuộc.
        self.declare_parameter('max_wait_s', 120.0)
        # /amcl_pose chỉ được coi là xác nhận nếu nằm trong bán kính này quanh HOME.
        self.declare_parameter('confirm_radius_m', 0.5)

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

        self.wait_for_amcl_confirm = bool(self.get_parameter('wait_for_amcl_confirm').value)
        self.amcl_pose_topic = self.get_parameter('amcl_pose_topic').value
        self.max_wait_s = max(1.0, float(self.get_parameter('max_wait_s').value))
        self.confirm_radius_m = max(0.05, float(self.get_parameter('confirm_radius_m').value))

        self.pub = self.create_publisher(
            PoseWithCovarianceStamped,
            self.initial_pose_topic,
            10
        )

        self.sent_count = 0
        self.start_time = time.time()
        self.first_publish_time = None
        self.amcl_confirmed = False
        self.last_wait_log_time = 0.0
        self.done = False

        self.amcl_sub = None
        if self.wait_for_amcl_confirm:
            self.amcl_sub = self.create_subscription(
                PoseWithCovarianceStamped,
                self.amcl_pose_topic,
                self.amcl_pose_callback,
                10
            )

        self.timer = self.create_timer(self.publish_period_s, self.timer_callback)

        self.get_logger().warn('Auto Initial Pose Node started')
        self.get_logger().warn(
            f'HOME initial pose: x={self.initial_x:.3f}, '
            f'y={self.initial_y:.3f}, yaw={self.initial_yaw:.3f}'
        )
        self.get_logger().warn(f'Publish topic: {self.initial_pose_topic}')
        self.get_logger().warn(
            f'Wait for AMCL confirm: {self.wait_for_amcl_confirm} '
            f'(topic={self.amcl_pose_topic}, max_wait={self.max_wait_s:.0f}s)'
        )

    def amcl_pose_callback(self, msg: PoseWithCovarianceStamped):
        # Chỉ tính /amcl_pose xuất hiện SAU lần publish initial pose đầu tiên
        # và nằm gần HOME (tránh nhầm với pose cũ của AMCL).
        if self.first_publish_time is None:
            return

        p = msg.pose.pose.position
        if math.hypot(p.x - self.initial_x, p.y - self.initial_y) <= self.confirm_radius_m:
            self.amcl_confirmed = True

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

        if self.wait_for_amcl_confirm:
            if self.amcl_confirmed:
                self.get_logger().warn(
                    f'AMCL confirmed initial pose (after {self.sent_count} publish). Done.'
                )
                self.done = True
                return

            if now - self.start_time > self.max_wait_s:
                self.get_logger().error(
                    f'AMCL did not confirm initial pose within {self.max_wait_s:.0f}s. Give up.'
                )
                self.done = True
                return

        if self.sent_count >= self.publish_count:
            if self.wait_for_amcl_confirm and not self.amcl_confirmed:
                self.get_logger().error(
                    f'Published {self.sent_count} times but no /amcl_pose received. '
                    f'Check AMCL / LiDAR scan. Give up.'
                )
            else:
                self.get_logger().warn('Auto initial pose publish done')
            self.done = True
            return

        # Chưa có AMCL (chưa có subscriber trên /initialpose) -> chờ, không publish mù.
        if self.wait_for_amcl_confirm and self.pub.get_subscription_count() == 0:
            if now - self.last_wait_log_time > 5.0:
                self.last_wait_log_time = now
                self.get_logger().info('Waiting for AMCL (no subscriber on initial pose topic yet)...')
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

        if self.first_publish_time is None:
            self.first_publish_time = now

        self.pub.publish(msg)
        self.sent_count += 1

        self.get_logger().info(
            f'Published HOME initial pose {self.sent_count}/{self.publish_count}'
        )

        # Chế độ cũ (không chờ xác nhận): đủ số lần thì dừng.
        if not self.wait_for_amcl_confirm and self.sent_count >= self.publish_count:
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