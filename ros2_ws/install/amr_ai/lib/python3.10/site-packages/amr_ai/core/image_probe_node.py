#!/usr/bin/env python3

import math

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge


class ImageProbeNode(Node):
    """
    Node test camera ROS2 cho amr_ai.

    Mục tiêu:
    - Subscribe ảnh màu ROS2.
    - Subscribe ảnh depth ROS2.
    - Kiểm tra cv_bridge hoạt động.
    - In shape ảnh, encoding, và depth tại tâm ảnh.
    - Không mở OpenNI trực tiếp.
    - Không mở GUI.
    """

    def __init__(self):
        super().__init__('ai_image_probe')

        self.declare_parameter('color_topic', '/camera/color/image_raw')
        self.declare_parameter('depth_topic', '/camera/depth/image_raw')
        self.declare_parameter('camera_info_topic', '/camera/color/camera_info')
        self.declare_parameter('print_period_sec', 1.0)

        self.color_topic = self.get_parameter('color_topic').value
        self.depth_topic = self.get_parameter('depth_topic').value
        self.camera_info_topic = self.get_parameter('camera_info_topic').value
        self.print_period_sec = float(self.get_parameter('print_period_sec').value)

        self.bridge = CvBridge()

        self.last_color_msg = None
        self.last_depth_msg = None
        self.last_camera_info = None

        self.color_count = 0
        self.depth_count = 0

        self.color_sub = self.create_subscription(
            Image,
            self.color_topic,
            self.color_callback,
            10
        )

        self.depth_sub = self.create_subscription(
            Image,
            self.depth_topic,
            self.depth_callback,
            10
        )

        self.info_sub = self.create_subscription(
            CameraInfo,
            self.camera_info_topic,
            self.camera_info_callback,
            10
        )

        self.timer = self.create_timer(
            self.print_period_sec,
            self.timer_callback
        )

        self.get_logger().info('AI Image Probe started')
        self.get_logger().info(f'Color topic      : {self.color_topic}')
        self.get_logger().info(f'Depth topic      : {self.depth_topic}')
        self.get_logger().info(f'Camera info topic: {self.camera_info_topic}')

    def color_callback(self, msg: Image):
        self.last_color_msg = msg
        self.color_count += 1

    def depth_callback(self, msg: Image):
        self.last_depth_msg = msg
        self.depth_count += 1

    def camera_info_callback(self, msg: CameraInfo):
        self.last_camera_info = msg

    def timer_callback(self):
        if self.last_color_msg is None:
            self.get_logger().warn('No color image received yet')
            return

        if self.last_depth_msg is None:
            self.get_logger().warn('No depth image received yet')
            return

        try:
            color = self.bridge.imgmsg_to_cv2(
                self.last_color_msg,
                desired_encoding='bgr8'
            )
        except Exception as exc:
            self.get_logger().error(f'Failed to convert color image: {exc}')
            return

        try:
            depth = self.bridge.imgmsg_to_cv2(
                self.last_depth_msg,
                desired_encoding='passthrough'
            )
        except Exception as exc:
            self.get_logger().error(f'Failed to convert depth image: {exc}')
            return

        h, w = color.shape[:2]
        dh, dw = depth.shape[:2]

        cx = dw // 2
        cy = dh // 2

        center_depth = depth[cy, cx]

        try:
            center_depth_float = float(center_depth)
        except Exception:
            center_depth_float = math.nan

        info_text = (
            f'color={color.shape}, enc={self.last_color_msg.encoding}, '
            f'depth={depth.shape}, depth_enc={self.last_depth_msg.encoding}, '
            f'center_depth={center_depth_float}, '
            f'color_count={self.color_count}, depth_count={self.depth_count}'
        )

        if self.last_camera_info is not None:
            fx = self.last_camera_info.k[0]
            fy = self.last_camera_info.k[4]
            cx_info = self.last_camera_info.k[2]
            cy_info = self.last_camera_info.k[5]
            info_text += (
                f', camera_info: fx={fx:.2f}, fy={fy:.2f}, '
                f'cx={cx_info:.2f}, cy={cy_info:.2f}'
            )
        else:
            info_text += ', camera_info=None'

        self.get_logger().info(info_text)


def main(args=None):
    rclpy.init(args=args)
    node = ImageProbeNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
