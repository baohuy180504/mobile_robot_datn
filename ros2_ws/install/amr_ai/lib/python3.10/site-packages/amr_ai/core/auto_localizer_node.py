#!/usr/bin/env python3

import math
import time

import rclpy
from rclpy.node import Node

from std_srvs.srv import Empty
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped

from amr_interfaces.msg import AiMode
from amr_interfaces.srv import SetAiMode


class AutoLocalizerNode(Node):
    """
    Auto global localization cho AMR.

    Khi mode = LOCALIZING:
    - gọi /reinitialize_global_localization
    - publish /cmd_vel_localize để xe quay tại chỗ
    - theo dõi /amcl_pose covariance
    - nếu hội tụ thì dừng và báo LOCALIZE_DONE
    - nếu timeout thì dừng và báo LOCALIZE_FAILED

    Node này không publish trực tiếp /cmd_vel_safe.
    /cmd_vel_localize sẽ đi qua cmd_vel_safety_mux ở bước sau.
    """

    def __init__(self):
        super().__init__('auto_localizer_node')

        self.declare_parameter('global_localization_service', '/reinitialize_global_localization')
        self.declare_parameter('amcl_pose_topic', '/amcl_pose')
        self.declare_parameter('cmd_vel_localize_topic', '/cmd_vel_localize')
        self.declare_parameter('set_mode_service', '/amr_ai/set_mode')

        self.declare_parameter('spin_angular_z', 0.25)
        self.declare_parameter('min_spin_time_s', 8.0)
        self.declare_parameter('max_spin_time_s', 45.0)
        self.declare_parameter('control_rate_hz', 10.0)

        self.declare_parameter('cov_x_threshold', 0.25)
        self.declare_parameter('cov_y_threshold', 0.25)
        self.declare_parameter('cov_yaw_threshold', 0.35)
        self.declare_parameter('stable_required_count', 10)

        self.declare_parameter('stop_publish_count', 10)

        self.global_localization_service = self.get_parameter('global_localization_service').value
        self.amcl_pose_topic = self.get_parameter('amcl_pose_topic').value
        self.cmd_vel_localize_topic = self.get_parameter('cmd_vel_localize_topic').value
        self.set_mode_service = self.get_parameter('set_mode_service').value

        self.spin_angular_z = float(self.get_parameter('spin_angular_z').value)
        self.min_spin_time_s = float(self.get_parameter('min_spin_time_s').value)
        self.max_spin_time_s = float(self.get_parameter('max_spin_time_s').value)
        self.control_rate_hz = float(self.get_parameter('control_rate_hz').value)

        self.cov_x_threshold = float(self.get_parameter('cov_x_threshold').value)
        self.cov_y_threshold = float(self.get_parameter('cov_y_threshold').value)
        self.cov_yaw_threshold = float(self.get_parameter('cov_yaw_threshold').value)
        self.stable_required_count = int(self.get_parameter('stable_required_count').value)

        self.stop_publish_count = int(self.get_parameter('stop_publish_count').value)

        self.current_mode = AiMode.IDLE

        self.localizing_active = False
        self.global_localization_called = False
        self.localize_start_time = 0.0
        self.stable_count = 0

        self.last_amcl_pose = None
        self.last_amcl_time = 0.0

        self.cmd_pub = self.create_publisher(
            Twist,
            self.cmd_vel_localize_topic,
            10
        )

        self.mode_sub = self.create_subscription(
            AiMode,
            '/amr_ai/mode',
            self.mode_callback,
            10
        )

        self.amcl_sub = self.create_subscription(
            PoseWithCovarianceStamped,
            self.amcl_pose_topic,
            self.amcl_pose_callback,
            10
        )

        self.global_loc_client = self.create_client(
            Empty,
            self.global_localization_service
        )

        self.set_mode_client = self.create_client(
            SetAiMode,
            self.set_mode_service
        )

        timer_period = 1.0 / max(1.0, self.control_rate_hz)
        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.get_logger().warn('Auto Localizer Node started')
        self.get_logger().info(f'global_localization_service={self.global_localization_service}')
        self.get_logger().info(f'amcl_pose_topic={self.amcl_pose_topic}')
        self.get_logger().info(f'cmd_vel_localize_topic={self.cmd_vel_localize_topic}')
        self.get_logger().info(f'spin_angular_z={self.spin_angular_z}')

    def mode_callback(self, msg: AiMode):
        old_mode = self.current_mode
        self.current_mode = int(msg.mode)

        if old_mode != AiMode.LOCALIZING and self.current_mode == AiMode.LOCALIZING:
            self.start_localization()

        if old_mode == AiMode.LOCALIZING and self.current_mode != AiMode.LOCALIZING:
            self.stop_motion()
            self.localizing_active = False
            self.global_localization_called = False
            self.stable_count = 0

    def amcl_pose_callback(self, msg: PoseWithCovarianceStamped):
        self.last_amcl_pose = msg
        self.last_amcl_time = time.time()

    def start_localization(self):
        self.get_logger().warn('LOCALIZING mode received: start auto localization')

        self.localizing_active = True
        self.global_localization_called = False
        self.localize_start_time = time.time()
        self.stable_count = 0

        self.call_global_localization()

    def call_global_localization(self):
        if not self.global_loc_client.wait_for_service(timeout_sec=2.0):
            self.get_logger().error(
                f'Global localization service not ready: {self.global_localization_service}'
            )
            self.finish_localization(success=False)
            return

        req = Empty.Request()
        future = self.global_loc_client.call_async(req)
        future.add_done_callback(self.global_localization_done)

    def global_localization_done(self, future):
        try:
            future.result()
            self.global_localization_called = True
            self.get_logger().warn('Global localization service called successfully')
        except Exception as exc:
            self.get_logger().error(f'Global localization service failed: {exc}')
            self.finish_localization(success=False)

    def timer_callback(self):
        if self.current_mode != AiMode.LOCALIZING:
            return

        if not self.localizing_active:
            return

        now = time.time()
        elapsed = now - self.localize_start_time

        if elapsed > self.max_spin_time_s:
            self.get_logger().error('Auto localization timeout')
            self.finish_localization(success=False)
            return

        # Chỉ bắt đầu đánh giá hội tụ sau thời gian xoay tối thiểu
        if elapsed >= self.min_spin_time_s:
            if self.is_amcl_converged():
                self.stable_count += 1
            else:
                self.stable_count = 0

            if self.stable_count >= self.stable_required_count:
                self.get_logger().warn('AMCL covariance converged')
                self.finish_localization(success=True)
                return

        # Trong lúc localize thì publish lệnh quay
        cmd = Twist()
        cmd.linear.x = 0.0
        cmd.angular.z = self.spin_angular_z
        self.cmd_pub.publish(cmd)

        if int(elapsed * 10) % 20 == 0:
            self.get_logger().info(
                f'LOCALIZING elapsed={elapsed:.1f}s, stable_count={self.stable_count}'
            )

    def is_amcl_converged(self) -> bool:
        if self.last_amcl_pose is None:
            return False

        if time.time() - self.last_amcl_time > 1.0:
            return False

        cov = self.last_amcl_pose.pose.covariance

        cov_x = abs(float(cov[0]))
        cov_y = abs(float(cov[7]))
        cov_yaw = abs(float(cov[35]))

        ok = (
            cov_x <= self.cov_x_threshold and
            cov_y <= self.cov_y_threshold and
            cov_yaw <= self.cov_yaw_threshold
        )

        self.get_logger().info(
            f'AMCL cov: x={cov_x:.3f}, y={cov_y:.3f}, yaw={cov_yaw:.3f}, ok={ok}'
        )

        return ok

    def finish_localization(self, success: bool):
        self.stop_motion()
        self.localizing_active = False

        if success:
            self.call_set_mode('LOCALIZE_DONE')
        else:
            self.call_set_mode('LOCALIZE_FAILED')

    def stop_motion(self):
        msg = Twist()

        for _ in range(max(1, self.stop_publish_count)):
            self.cmd_pub.publish(msg)

    def call_set_mode(self, command: str):
        if not self.set_mode_client.wait_for_service(timeout_sec=2.0):
            self.get_logger().error(f'Set mode service not ready: {self.set_mode_service}')
            return

        req = SetAiMode.Request()
        req.mode = 0
        req.command = command

        future = self.set_mode_client.call_async(req)
        future.add_done_callback(lambda fut: self.set_mode_done(fut, command))

    def set_mode_done(self, future, command: str):
        try:
            res = future.result()
            self.get_logger().warn(
                f'set_mode {command}: success={res.success}, '
                f'message={res.message}, current_mode={res.current_mode}'
            )
        except Exception as exc:
            self.get_logger().error(f'set_mode {command} failed: {exc}')


def main(args=None):
    rclpy.init(args=args)
    node = AutoLocalizerNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()