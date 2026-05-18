#!/usr/bin/env python3
"""
scan_merger.py — package: amr_slam

Gộp:
  /scan_filtered  LiDAR thật
  /scan_camera    LaserScan ảo từ depth camera
thành:
  /scan_merged

Điểm sửa quan trọng:
  - Xử lý wrap góc: nguồn LiDAR có thể publish 90° -> 270° nhưng output dùng -180° -> 180°.
  - Có merge_mode:
      fill_gaps_only: LiDAR là chính, camera chỉ điền beam LiDAR không có dữ liệu.
      nearest:        lấy range gần nhất từ 2 nguồn.
"""

import math
from typing import Optional

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan


class ScanMerger(Node):
    def __init__(self):
        super().__init__('scan_merger')

        self.declare_parameter('lidar_topic', '/scan_filtered')
        self.declare_parameter('camera_topic', '/scan_camera')
        self.declare_parameter('output_topic', '/scan_merged')
        self.declare_parameter('output_frame', 'laser_frame')
        self.declare_parameter('angle_min', -math.pi)
        self.declare_parameter('angle_max', math.pi)
        self.declare_parameter('angle_increment', 0.00436)
        self.declare_parameter('range_min', 0.10)
        self.declare_parameter('range_max', 11.0)
        self.declare_parameter('camera_timeout', 1.0)
        self.declare_parameter('merge_mode', 'fill_gaps_only')

        self.lidar_topic = self.get_parameter('lidar_topic').value
        self.camera_topic = self.get_parameter('camera_topic').value
        self.output_topic = self.get_parameter('output_topic').value
        self.output_frame = self.get_parameter('output_frame').value
        self.angle_min = float(self.get_parameter('angle_min').value)
        self.angle_max = float(self.get_parameter('angle_max').value)
        self.angle_inc = float(self.get_parameter('angle_increment').value)
        self.range_min = float(self.get_parameter('range_min').value)
        self.range_max = float(self.get_parameter('range_max').value)
        self.camera_timeout = float(self.get_parameter('camera_timeout').value)
        self.merge_mode = str(self.get_parameter('merge_mode').value)

        if self.merge_mode not in ('fill_gaps_only', 'nearest'):
            self.get_logger().warn(
                f"merge_mode='{self.merge_mode}' không hợp lệ, dùng fill_gaps_only"
            )
            self.merge_mode = 'fill_gaps_only'

        self._out_angles = np.arange(
            self.angle_min,
            self.angle_max + self.angle_inc * 0.5,
            self.angle_inc,
            dtype=np.float32,
        )
        self._num_beams = len(self._out_angles)

        self._lidar_scan: Optional[LaserScan] = None
        self._camera_scan: Optional[LaserScan] = None
        self._last_camera_rx_time = None

        sensor_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )

        self.create_subscription(LaserScan, self.lidar_topic, self._lidar_cb, sensor_qos)
        self.create_subscription(LaserScan, self.camera_topic, self._camera_cb, sensor_qos)
        self._pub = self.create_publisher(LaserScan, self.output_topic, sensor_qos)

        self.get_logger().info(
            f"ScanMerger: {self.lidar_topic} + {self.camera_topic} -> "
            f"{self.output_topic}, mode={self.merge_mode}"
        )

    @staticmethod
    def _norm_angle(angle: float) -> float:
        return math.atan2(math.sin(angle), math.cos(angle))

    def _angle_to_index(self, angle: float, scan: LaserScan) -> Optional[int]:
        """Trả về index trong scan nguồn, có xét wrap ±2π."""
        candidates = (angle, angle + 2.0 * math.pi, angle - 2.0 * math.pi)
        n = len(scan.ranges)

        for a in candidates:
            if scan.angle_min - 1e-6 <= a <= scan.angle_max + 1e-6:
                idx = int(round((a - scan.angle_min) / scan.angle_increment))
                if 0 <= idx < n:
                    return idx
        return None

    def _valid_range(self, r: float, scan: LaserScan) -> bool:
        if math.isnan(r) or math.isinf(r):
            return False
        if r < max(self.range_min, scan.range_min):
            return False
        if r > min(self.range_max, scan.range_max):
            return False
        return True

    def _scan_to_array(self, scan: LaserScan) -> np.ndarray:
        out = np.full(self._num_beams, np.inf, dtype=np.float32)
        ranges = scan.ranges

        for i, angle in enumerate(self._out_angles):
            idx = self._angle_to_index(float(angle), scan)
            if idx is None:
                continue

            r = float(ranges[idx])
            if self._valid_range(r, scan):
                out[i] = r

        return out

    def _lidar_cb(self, msg: LaserScan):
        self._lidar_scan = msg
        self._publish(msg.header.stamp)

    def _camera_cb(self, msg: LaserScan):
        self._camera_scan = msg
        self._last_camera_rx_time = self.get_clock().now()

    def _camera_is_valid(self) -> bool:
        if self._camera_scan is None or self._last_camera_rx_time is None:
            return False
        age = (self.get_clock().now() - self._last_camera_rx_time).nanoseconds * 1e-9
        return age <= self.camera_timeout

    def _publish(self, stamp):
        if self._lidar_scan is None:
            return

        lidar = self._scan_to_array(self._lidar_scan)

        if self._camera_is_valid():
            camera = self._scan_to_array(self._camera_scan)
            lidar_valid = np.isfinite(lidar)
            camera_valid = np.isfinite(camera)

            if self.merge_mode == 'nearest':
                merged = np.minimum(lidar, camera)
            else:
                # LiDAR là nguồn chính. Camera chỉ bù vùng LiDAR không có beam hợp lệ.
                merged = lidar.copy()
                fill_mask = (~lidar_valid) & camera_valid
                merged[fill_mask] = camera[fill_mask]
        else:
            merged = lidar
            if self._camera_scan is not None:
                self.get_logger().warn(
                    'Camera scan timeout, /scan_merged dùng LiDAR only',
                    throttle_duration_sec=5.0,
                )

        merged = np.where(
            (merged >= self.range_min) & (merged <= self.range_max),
            merged,
            np.inf,
        ).astype(np.float32)

        msg = LaserScan()
        msg.header.stamp = stamp
        msg.header.frame_id = self.output_frame
        msg.angle_min = float(self._out_angles[0])
        msg.angle_max = float(self._out_angles[-1])
        msg.angle_increment = float(self.angle_inc)
        msg.time_increment = 0.0
        msg.scan_time = self._lidar_scan.scan_time
        msg.range_min = self.range_min
        msg.range_max = self.range_max
        msg.ranges = merged.tolist()
        msg.intensities = []

        self._pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ScanMerger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
