#!/usr/bin/env python3
import argparse
import time

import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy

from sensor_msgs.msg import Image, CompressedImage
from cv_bridge import CvBridge


class WebCameraLowLatency(Node):
    def __init__(self, args):
        super().__init__("web_camera_low_latency")

        self.input_topic = args.input
        self.output_topic = args.output
        self.width = int(args.width)
        self.height = int(args.height)
        self.fps = float(args.fps)
        self.jpeg_quality = int(args.quality)
        self.log_latency = bool(args.log_latency)

        self.bridge = CvBridge()

        self.latest_msg = None
        self.latest_key = None
        self.published_key = None

        self.last_stat_time = time.time()
        self.pub_count = 0

        qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
        )

        self.sub = self.create_subscription(
            Image,
            self.input_topic,
            self.image_cb,
            qos,
        )

        self.pub = self.create_publisher(
            CompressedImage,
            self.output_topic,
            qos,
        )

        period = 1.0 / max(self.fps, 1.0)
        self.timer = self.create_timer(period, self.timer_cb)

        self.get_logger().warn("=== AMR WEB CAMERA LOW LATENCY ===")
        self.get_logger().warn(f"Input        : {self.input_topic}")
        self.get_logger().warn(f"Output       : {self.output_topic}")
        self.get_logger().warn(f"Resolution   : {self.width}x{self.height}")
        self.get_logger().warn(f"FPS limit     : {self.fps}")
        self.get_logger().warn(f"JPEG quality : {self.jpeg_quality}")
        self.get_logger().warn("QoS          : BEST_EFFORT, depth=1")
        self.get_logger().warn("Policy       : publish NEW frame only, drop old frames")

    def image_cb(self, msg: Image):
        self.latest_msg = msg
        self.latest_key = (
            int(msg.header.stamp.sec),
            int(msg.header.stamp.nanosec),
        )

    def timer_cb(self):
        msg = self.latest_msg
        key = self.latest_key

        if msg is None or key is None:
            return

        # Quan trọng: nếu không có frame mới thì không publish lại frame cũ.
        if key == self.published_key:
            return

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().warn(f"cv_bridge convert failed: {exc}")
            return

        if self.width > 0 and self.height > 0:
            frame = cv2.resize(
                frame,
                (self.width, self.height),
                interpolation=cv2.INTER_AREA,
            )

        ok, encoded = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality],
        )

        if not ok:
            self.get_logger().warn("JPEG encode failed")
            return

        out = CompressedImage()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = msg.header.frame_id
        out.format = "jpeg"
        out.data = encoded.tobytes()

        self.pub.publish(out)
        self.published_key = key
        self.pub_count += 1

        now = time.time()

        if self.log_latency:
            src_t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            now_ros = self.get_clock().now().nanoseconds * 1e-9
            age = now_ros - src_t
            self.get_logger().info(
                f"published new frame, src_age={age:.3f}s, jpeg_size={len(out.data)/1024:.1f} KB"
            )

        if now - self.last_stat_time >= 5.0:
            dt = now - self.last_stat_time
            fps_real = self.pub_count / dt
            self.get_logger().info(
                f"Output approx {fps_real:.2f} FPS, last jpeg={len(out.data)/1024:.1f} KB"
            )
            self.pub_count = 0
            self.last_stat_time = now


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="/camera/color/image_raw")
    parser.add_argument("--output", default="/camera/color/image_web/compressed")
    parser.add_argument("--width", type=int, default=480)
    parser.add_argument("--height", type=int, default=270)
    parser.add_argument("--fps", type=float, default=3.0)
    parser.add_argument("--quality", type=int, default=45)
    parser.add_argument("--log-latency", action="store_true")
    args = parser.parse_args()

    rclpy.init()
    node = WebCameraLowLatency(args)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
