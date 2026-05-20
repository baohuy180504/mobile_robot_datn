#!/usr/bin/env python3

import math
import inspect
import time
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from geometry_msgs.msg import PoseStamped, PointStamped, Twist
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatus

import tf2_ros
from tf2_geometry_msgs import do_transform_point

from amr_interfaces.msg import AiMode, PersonTarget


def yaw_to_quaternion(yaw: float):
    qz = math.sin(yaw / 2.0)
    qw = math.cos(yaw / 2.0)
    return 0.0, 0.0, qz, qw


def yaw_from_quaternion(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class FollowGoalNode(Node):
    """
    Convert PersonTarget thành Nav2 goal động.

    Chỉ hoạt động khi /amr_ai/mode = FOLLOW_ACTIVE.
    Không điều khiển /cmd_vel trực tiếp.
    """

    def __init__(self):
        super().__init__('follow_goal_node')

        self.declare_parameter('base_frame', 'base_footprint')
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('follow_distance_m', 2.0)
        self.declare_parameter('follow_distance_tolerance_m', 0.30)
        self.declare_parameter('goal_update_period_s', 0.8)
        self.declare_parameter('min_goal_update_distance_m', 0.30)
        self.declare_parameter('target_timeout_s', 1.0)
        self.declare_parameter('nav_action_name', 'navigate_to_pose')
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('stop_cmd_duration_s', 0.8)

        self.base_frame = self.get_parameter('base_frame').value
        self.map_frame = self.get_parameter('map_frame').value
        self.follow_distance_m = float(self.get_parameter('follow_distance_m').value)
        self.follow_tolerance_m = float(self.get_parameter('follow_distance_tolerance_m').value)
        self.goal_update_period_s = float(self.get_parameter('goal_update_period_s').value)
        self.min_goal_update_distance_m = float(self.get_parameter('min_goal_update_distance_m').value)
        self.target_timeout_s = float(self.get_parameter('target_timeout_s').value)
        self.nav_action_name = self.get_parameter('nav_action_name').value
        self.cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self.stop_cmd_duration_s = float(self.get_parameter('stop_cmd_duration_s').value)
        self.stop_cmd_until = 0.0

        self.current_mode = AiMode.IDLE
        self.last_target: Optional[PersonTarget] = None
        self.last_target_time = 0.0

        self.current_goal_handle = None
        self.last_goal_x = None
        self.last_goal_y = None
        self.last_goal_send_time = 0.0

        self.tf_buffer = tf2_ros.Buffer(cache_time=rclpy.duration.Duration(seconds=10.0))
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.nav_client = ActionClient(self, NavigateToPose, self.nav_action_name)

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

        self.timer = self.create_timer(
            self.goal_update_period_s,
            self.timer_callback
        )

        self.get_logger().info('Follow Goal Node started')
        self.get_logger().info(f'base_frame={self.base_frame}, map_frame={self.map_frame}')
        self.get_logger().info(f'follow_distance_m={self.follow_distance_m}')


    # ==========================================================
    # Throttled logging helpers for ROS2 Humble Python
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

        if level == "info":
            self.get_logger().info(message)
        elif level == "warn":
            self.get_logger().warn(message)
        else:
            self.get_logger().info(message)

    def log_info_throttle(self, period_sec: float, message: str):
        self._log_throttle("info", period_sec, message)

    def log_warn_throttle(self, period_sec: float, message: str):
        self._log_throttle("warn", period_sec, message)


    def mode_callback(self, msg: AiMode):
        old_mode = self.current_mode
        self.current_mode = int(msg.mode)

        if old_mode == AiMode.FOLLOW_ACTIVE and self.current_mode != AiMode.FOLLOW_ACTIVE:
            self.get_logger().warn('Exit FOLLOW_ACTIVE: cancel follow Nav2 goal')
            self.cancel_current_goal()

    def target_callback(self, msg: PersonTarget):
        self.last_target = msg
        self.last_target_time = time.time()

    def timer_callback(self):
        if self.current_mode != AiMode.FOLLOW_ACTIVE:
            return

        if self.last_target is None:
            self.log_warn_throttle(2.0, 'No person target received yet')
            return

        if time.time() - self.last_target_time > self.target_timeout_s:
            self.get_logger().warn('Person target timeout. Cancel follow goal.')
            self.cancel_current_goal()
            return

        if self.last_target.lost:
            self.log_warn_throttle(1.0, 'Person target lost. Cancel follow goal.')
            self.cancel_current_goal()
            return

        if not math.isfinite(self.last_target.distance_m):
            self.log_warn_throttle(1.0, 'Target distance invalid. Skip follow goal.')
            return

        try:
            target_base = self.transform_point(
                self.last_target.position_camera,
                self.base_frame
            )
            target_map = self.transform_point(
                self.last_target.position_camera,
                self.map_frame
            )
            robot_map = self.lookup_robot_pose_in_map()
        except Exception as exc:
            self.log_warn_throttle(1.0, f'TF transform failed: {exc}')
            return

        # Trong base_footprint: x forward, y left.
        tx_b = target_base.point.x
        ty_b = target_base.point.y
        distance_base = math.hypot(tx_b, ty_b)

        if distance_base <= 0.05:
            return

        # Nếu đã ở vùng 2m ± tolerance thì không gửi goal mới liên tục.
        if abs(distance_base - self.follow_distance_m) <= self.follow_tolerance_m:
            self.log_info_throttle(
                1.0,
                f'Hold position. target_distance={distance_base:.2f} m'
            )
            self.cancel_current_goal()
            return

        goal_pose = self.compute_follow_goal(target_map, robot_map)

        if goal_pose is None:
            return

        gx = goal_pose.pose.position.x
        gy = goal_pose.pose.position.y

        if not self.should_send_new_goal(gx, gy):
            return

        self.send_nav2_goal(goal_pose)

    def transform_point(self, point_msg: PointStamped, target_frame: str) -> PointStamped:
        # Dùng time=0 để lấy transform mới nhất, tránh lỗi timestamp lệch giữa camera và TF.
        transform = self.tf_buffer.lookup_transform(
            target_frame,
            point_msg.header.frame_id,
            rclpy.time.Time(),
            timeout=rclpy.duration.Duration(seconds=0.2)
        )
        return do_transform_point(point_msg, transform)

    def lookup_robot_pose_in_map(self) -> PoseStamped:
        transform = self.tf_buffer.lookup_transform(
            self.map_frame,
            self.base_frame,
            rclpy.time.Time(),
            timeout=rclpy.duration.Duration(seconds=0.2)
        )

        pose = PoseStamped()
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.header.frame_id = self.map_frame
        pose.pose.position.x = transform.transform.translation.x
        pose.pose.position.y = transform.transform.translation.y
        pose.pose.position.z = transform.transform.translation.z
        pose.pose.orientation = transform.transform.rotation
        return pose

    def compute_follow_goal(self, target_map: PointStamped, robot_map: PoseStamped) -> Optional[PoseStamped]:
        rx = robot_map.pose.position.x
        ry = robot_map.pose.position.y

        tx = target_map.point.x
        ty = target_map.point.y

        dx = tx - rx
        dy = ty - ry
        dist = math.hypot(dx, dy)

        if dist < 0.05:
            return None

        ux = dx / dist
        uy = dy / dist

        # Điểm goal nằm trên đường robot-target, cách target follow_distance_m.
        gx = tx - ux * self.follow_distance_m
        gy = ty - uy * self.follow_distance_m

        # Robot quay mặt về target.
        yaw = math.atan2(ty - gy, tx - gx)

        goal = PoseStamped()
        goal.header.stamp = self.get_clock().now().to_msg()
        goal.header.frame_id = self.map_frame
        goal.pose.position.x = float(gx)
        goal.pose.position.y = float(gy)
        goal.pose.position.z = 0.0

        qx, qy, qz, qw = yaw_to_quaternion(yaw)
        goal.pose.orientation.x = qx
        goal.pose.orientation.y = qy
        goal.pose.orientation.z = qz
        goal.pose.orientation.w = qw

        return goal

    def should_send_new_goal(self, gx: float, gy: float) -> bool:
        now = time.time()

        if now - self.last_goal_send_time < self.goal_update_period_s:
            return False

        if self.last_goal_x is None or self.last_goal_y is None:
            return True

        moved = math.hypot(gx - self.last_goal_x, gy - self.last_goal_y)

        return moved >= self.min_goal_update_distance_m

    def send_nav2_goal(self, pose: PoseStamped):
        if not self.nav_client.wait_for_server(timeout_sec=0.1):
            self.get_logger().warn('Nav2 navigate_to_pose action server not available')
            return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = pose

        self.last_goal_x = pose.pose.position.x
        self.last_goal_y = pose.pose.position.y
        self.last_goal_send_time = time.time()

        self.get_logger().info(
            f'Send follow goal: x={self.last_goal_x:.2f}, y={self.last_goal_y:.2f}'
        )

        send_future = self.nav_client.send_goal_async(goal_msg)
        send_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        try:
            goal_handle = future.result()
        except Exception as exc:
            self.get_logger().error(f'Follow goal send failed: {exc}')
            return

        if not goal_handle.accepted:
            self.get_logger().warn('Follow goal rejected by Nav2')
            return

        self.current_goal_handle = goal_handle

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    def result_callback(self, future):
        try:
            result = future.result()
            status = result.status
        except Exception as exc:
            self.get_logger().error(f'Follow goal result failed: {exc}')
            return

        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info('Follow goal reached')
        elif status == GoalStatus.STATUS_CANCELED:
            self.get_logger().warn('Follow goal canceled')
        elif status == GoalStatus.STATUS_ABORTED:
            self.get_logger().warn('Follow goal aborted')
        else:
            self.get_logger().warn(f'Follow goal finished with status={status}')

        self.current_goal_handle = None

    def cancel_current_goal(self):
        if self.current_goal_handle is None:
            return

        try:
            self.current_goal_handle.cancel_goal_async()
        except Exception as exc:
            self.get_logger().warn(f'Cancel follow goal failed: {exc}')

        self.current_goal_handle = None


def main(args=None):
    rclpy.init(args=args)
    node = FollowGoalNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
