#!/usr/bin/env python3

import cv2
import os
import inspect
import time
import math
import numpy as np
import torch

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
from ultralytics import YOLO
from ament_index_python.packages import get_package_share_directory

from amr_interfaces.msg import AiMode, PersonTarget
from amr_interfaces.srv import SetAiMode

from amr_ai.core import config as cfg
from amr_ai.core.utils import (
    valid_box_size,
    center_distance_sq,
    estimate_depth_distance,
)
from amr_ai.tracking.reid import ReIDManager


def get_nearest_track(boxes_xyxy, ids, center_x, center_y):
    nearest_track = None
    nearest_box = None
    nearest_dist = 10**18

    for box, tid in zip(boxes_xyxy, ids):
        if not valid_box_size(box):
            continue

        dist2 = center_distance_sq(box, center_x, center_y)

        if dist2 < nearest_dist:
            nearest_dist = dist2
            nearest_track = tid
            nearest_box = box

    return nearest_track, nearest_box


class PersonTrackerNode(Node):
    """
    ROS2 node bám target người ở mức perception.

    Vai trò:
    - Subscribe ảnh RGB + depth + camera_info.
    - Khi /amr_ai/mode = FOLLOW_DETECTING:
        + reset ReID
        + đếm chuẩn bị detect/enroll
        + enroll người gần tâm ảnh
        + khóa target
        + yêu cầu mode_manager chuyển sang FOLLOW_ACTIVE.
    - Khi /amr_ai/mode = FOLLOW_ACTIVE:
        + tiếp tục ReID target
        + publish /amr_ai/person_target.
    - Publish ảnh debug:
        + /amr_ai/debug/person_tracker/image
        + khung xám: người detect được
        + khung xanh: target đang bám.
    """

    def __init__(self):
        super().__init__('person_tracker_node')

        # ======================================================
        # Parameters
        # ======================================================
        self.declare_parameter('color_topic', '/camera/color/image_raw')
        self.declare_parameter('depth_topic', '/camera/depth/image_raw')
        self.declare_parameter('camera_info_topic', '/camera/color/camera_info')

        self.declare_parameter('person_model_path', 'models/yolo26n.engine')
        self.declare_parameter('camera_frame', 'camera_color_optical_frame')

        self.declare_parameter('detect_conf', 0.4)
        self.declare_parameter('detect_lock_time_s', 4.0)
        self.declare_parameter('enroll_frames', int(cfg.ENROLL_FRAMES))
        self.declare_parameter('target_lost_timeout_s', 3.0)

        self.declare_parameter('process_every_n_frames', 1)

        # Debug image
        self.declare_parameter('enable_debug_image', True)
        self.declare_parameter('debug_image_topic', '/amr_ai/debug/person_tracker/image')
        self.declare_parameter('debug_image_publish_hz', 3.0)
        self.declare_parameter('debug_image_scale', 0.5)

        self.color_topic = self.get_parameter('color_topic').value
        self.depth_topic = self.get_parameter('depth_topic').value
        self.camera_info_topic = self.get_parameter('camera_info_topic').value
        self.camera_frame = self.get_parameter('camera_frame').value

        self.detect_conf = float(self.get_parameter('detect_conf').value)
        self.detect_lock_time_s = float(self.get_parameter('detect_lock_time_s').value)
        self.enroll_frames = int(self.get_parameter('enroll_frames').value)
        self.target_lost_timeout_s = float(self.get_parameter('target_lost_timeout_s').value)
        self.process_every_n_frames = max(
            1,
            int(self.get_parameter('process_every_n_frames').value)
        )

        self.enable_debug_image = bool(self.get_parameter('enable_debug_image').value)
        self.debug_image_topic = self.get_parameter('debug_image_topic').value
        self.debug_image_publish_hz = float(self.get_parameter('debug_image_publish_hz').value)
        self.debug_image_scale = float(self.get_parameter('debug_image_scale').value)
        self.last_debug_image_publish_time = 0.0

        self.bridge = CvBridge()

        # ======================================================
        # Model
        # ======================================================
        self.share_dir = get_package_share_directory('amr_ai')
        self.person_model_path = self.resolve_model_path(
            self.get_parameter('person_model_path').value
        )

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.infer_device = 0 if torch.cuda.is_available() else "cpu"

        self.get_logger().info('Loading person YOLO model...')
        self.get_logger().info(f'Person model path: {self.person_model_path}')
        self.detect_model = YOLO(self.person_model_path)

        self.get_logger().info('Loading ReID manager...')
        self.reid = ReIDManager(self.device)

        # ======================================================
        # State
        # ======================================================
        self.current_mode = AiMode.IDLE
        self.last_mode = AiMode.IDLE

        self.prepare_mode = False
        self.enroll_mode = False
        self.prepare_start_time = 0.0
        self.target_locked_reported = False

        self.last_depth_msg = None
        self.last_camera_info = None

        self.frame_count = 0
        self.last_target_publish_time = 0.0
        self.last_selected_target_time = 0.0

        # ======================================================
        # Publishers
        # ======================================================
        self.person_target_pub = self.create_publisher(
            PersonTarget,
            '/amr_ai/person_target',
            10
        )

        # Queue nhỏ để giảm độ trễ hiển thị debug image.
        self.debug_image_pub = self.create_publisher(
            Image,
            self.debug_image_topic,
            1
        )

        # ======================================================
        # Subscribers
        # ======================================================
        self.mode_sub = self.create_subscription(
            AiMode,
            '/amr_ai/mode',
            self.mode_callback,
            10
        )

        self.color_sub = self.create_subscription(
            Image,
            self.color_topic,
            self.color_callback,
            qos_profile_sensor_data
        )

        self.depth_sub = self.create_subscription(
            Image,
            self.depth_topic,
            self.depth_callback,
            qos_profile_sensor_data
        )

        self.info_sub = self.create_subscription(
            CameraInfo,
            self.camera_info_topic,
            self.camera_info_callback,
            10
        )

        # ======================================================
        # Service clients
        # ======================================================
        self.set_mode_client = self.create_client(
            SetAiMode,
            '/amr_ai/set_mode'
        )

        self.get_logger().info('Person Tracker Node started')
        self.get_logger().info(f'Color topic      : {self.color_topic}')
        self.get_logger().info(f'Depth topic      : {self.depth_topic}')
        self.get_logger().info(f'Camera info topic: {self.camera_info_topic}')
        self.get_logger().info(f'Camera frame     : {self.camera_frame}')
        self.get_logger().info(f'Device           : {self.device}')
        self.get_logger().info(f'Debug image topic: {self.debug_image_topic}')
        self.get_logger().info(f'Debug image hz   : {self.debug_image_publish_hz}')
        self.get_logger().info(f'Debug image scale: {self.debug_image_scale}')

    def resolve_model_path(self, path_value):
        if os.path.isabs(path_value):
            return path_value
        return os.path.join(self.share_dir, path_value)

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

    # ==========================================================
    # ROS callbacks
    # ==========================================================
    def mode_callback(self, msg: AiMode):
        self.last_mode = self.current_mode
        self.current_mode = int(msg.mode)

        if (
            self.current_mode == AiMode.FOLLOW_DETECTING
            and self.last_mode != AiMode.FOLLOW_DETECTING
        ):
            self.start_follow_detecting()

        if self.current_mode in [
            AiMode.IDLE,
            AiMode.NAV_TO_ZONE,
            AiMode.RETURN_TO_ZONE,
            AiMode.EMERGENCY_STOP,
        ]:
            if self.last_mode != self.current_mode:
                self.reset_tracking_state()

    def depth_callback(self, msg: Image):
        self.last_depth_msg = msg

    def camera_info_callback(self, msg: CameraInfo):
        self.last_camera_info = msg

    def color_callback(self, msg: Image):
        self.frame_count += 1

        if self.frame_count % self.process_every_n_frames != 0:
            return

        if self.current_mode not in [AiMode.FOLLOW_DETECTING, AiMode.FOLLOW_ACTIVE]:
            return

        if self.last_depth_msg is None:
            self.log_warn_throttle(2.0, 'No depth image received yet')
            return

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
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

        now = time.time()
        self.process_frame(frame, depth, msg.header.stamp, now)

    # ==========================================================
    # State
    # ==========================================================
    def start_follow_detecting(self):
        self.get_logger().warn('FOLLOW_DETECTING received: reset ReID and start prepare/enroll')

        self.reid.reset()

        self.prepare_mode = True
        self.enroll_mode = False
        self.prepare_start_time = time.time()
        self.target_locked_reported = False
        self.last_selected_target_time = 0.0

    def reset_tracking_state(self):
        self.prepare_mode = False
        self.enroll_mode = False
        self.target_locked_reported = False

    # ==========================================================
    # Main processing
    # ==========================================================
    def process_frame(self, frame, depth, stamp, now):
        h, w = frame.shape[:2]
        center_x = w // 2
        center_y = h // 2

        if self.prepare_mode:
            elapsed = now - self.prepare_start_time
            remaining = max(0.0, self.detect_lock_time_s - elapsed)

            self.log_info_throttle(
                1.0,
                f'Preparing target enrollment... remaining={remaining:.1f}s'
            )

            if elapsed >= self.detect_lock_time_s:
                self.prepare_mode = False
                self.enroll_mode = True
                self.reid.enroll_embeddings = []
                self.reid.enroll_upper_embeddings = []
                self.reid.enroll_shirts = []
                self.get_logger().warn('Start enrolling target near image center')

        detections, nearest_track, nearest_box = self.run_detection(
            frame,
            center_x,
            center_y
        )

        if self.enroll_mode:
            self.handle_enroll(frame, nearest_track, nearest_box, now)

        selected_target = self.reid.select_target(
            frame,
            detections,
            center_x,
            center_y,
            now,
            self.frame_count
        )

        selected_distance_mm = None

        if selected_target is not None:
            raw_distance_mm, _ = estimate_depth_distance(
                depth,
                selected_target["box"]
            )
            selected_distance_mm = self.reid.smooth_depth_distance(raw_distance_mm)
            self.last_selected_target_time = now

            if (
                self.current_mode == AiMode.FOLLOW_DETECTING
                and not self.target_locked_reported
            ):
                self.request_follow_active()

            self.publish_target(
                stamp=stamp,
                selected_target=selected_target,
                distance_mm=selected_distance_mm,
                lost=False
            )

        elif self.reid.target_profile is not None:
            lost_duration = (
                now - self.last_selected_target_time
                if self.last_selected_target_time > 0.0
                else 0.0
            )

            self.publish_lost_target(stamp)

            self.log_warn_throttle(
                1.0,
                f'Target lost. lost_duration={lost_duration:.1f}s'
            )

        self.publish_debug_image(frame, detections, selected_target, stamp)

    def run_detection(self, frame, center_x, center_y):
        detections = []
        nearest_track = None
        nearest_box = None

        try:
            track_kwargs = {
                'source': frame,
                'persist': True,
                'classes': [0],
                'conf': self.detect_conf,
                'verbose': False,
            }

            tracker_cfg = getattr(cfg, 'TRACKER_CFG', None)
            if tracker_cfg:
                track_kwargs['tracker'] = tracker_cfg

            detect_results = self.detect_model.track(**track_kwargs)

        except Exception as exc:
            self.log_warn_throttle(
                2.0,
                f'YOLO track failed, fallback to predict: {exc}'
            )
            detect_results = self.detect_model.predict(
                frame,
                classes=[0],
                conf=self.detect_conf,
                verbose=False
            )

        boxes = detect_results[0].boxes if detect_results and len(detect_results) > 0 else None

        if boxes is None or boxes.xyxy is None:
            return detections, nearest_track, nearest_box

        xyxy = boxes.xyxy.cpu().numpy()
        ids = (
            boxes.id.int().cpu().tolist()
            if boxes.id is not None
            else list(range(1, len(xyxy) + 1))
        )
        confs = boxes.conf.cpu().numpy() if boxes.conf is not None else [0.0] * len(xyxy)

        nearest_track, nearest_box = get_nearest_track(
            xyxy,
            ids,
            center_x,
            center_y
        )

        for box, tid, conf in zip(xyxy, ids, confs):
            detections.append({
                "id": int(tid),
                "box": box,
                "conf": float(conf),
                "emb_sim": None,
                "shirt_sim": None,
                "motion_sim": None,
                "score": None,
                "falling": False,
                "fall_mode": None,
            })

        return detections, nearest_track, nearest_box

    def handle_enroll(self, frame, nearest_track, nearest_box, now):
        if nearest_box is None:
            self.log_warn_throttle(1.0, 'Enrolling: no valid person near image center')
            return

        try:
            self.reid.add_enroll_sample(frame, nearest_box)
        except Exception as exc:
            self.log_warn_throttle(1.0, f'add_enroll_sample failed: {exc}')
            return

        enroll_count = len(self.reid.enroll_embeddings)

        self.log_info_throttle(
            0.5,
            f'Enrolling target: {enroll_count}/{self.enroll_frames}'
        )

        if enroll_count >= self.enroll_frames:
            self.reid.finish_enroll(nearest_track, nearest_box, now)
            self.enroll_mode = False
            self.last_selected_target_time = now

            self.get_logger().warn(
                f'Target locked: track_id={nearest_track}, samples={enroll_count}'
            )

    # ==========================================================
    # Debug image
    # ==========================================================
    def publish_debug_image(self, frame, detections, selected_target, stamp):
        if not self.enable_debug_image:
            return

        now = time.time()

        if self.debug_image_publish_hz > 0.0:
            min_period = 1.0 / self.debug_image_publish_hz
            if now - self.last_debug_image_publish_time < min_period:
                return

        self.last_debug_image_publish_time = now

        annotated = frame.copy()

        # Vẽ tất cả người YOLO detect được.
        for det in detections:
            box = det.get("box", None)
            if box is None:
                continue

            x1, y1, x2, y2 = map(int, box)
            tid = int(det.get("id", -1))
            conf = float(det.get("conf", 0.0))

            color = (160, 160, 160)
            label = f"ID {tid} {conf:.2f}"

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                annotated,
                label,
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )

        # Vẽ target đang bám.
        if selected_target is not None:
            box = selected_target.get("box", None)

            if box is not None:
                x1, y1, x2, y2 = map(int, box)
                tid = int(selected_target.get("id", -1))
                conf = float(selected_target.get("conf", 0.0))

                color = (0, 255, 0)
                label = f"FOLLOW TARGET ID {tid} {conf:.2f}"

                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
                cv2.putText(
                    annotated,
                    label,
                    (x1, max(30, y1 - 12)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    color,
                    2
                )

                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                cv2.circle(annotated, (cx, cy), 5, color, -1)

        # Vẽ tâm ảnh camera.
        h, w = annotated.shape[:2]
        cv2.line(annotated, (w // 2, 0), (w // 2, h), (255, 0, 0), 1)
        cv2.line(annotated, (0, h // 2), (w, h // 2), (255, 0, 0), 1)

        if self.debug_image_scale > 0.0 and self.debug_image_scale != 1.0:
            annotated = cv2.resize(
                annotated,
                None,
                fx=self.debug_image_scale,
                fy=self.debug_image_scale,
                interpolation=cv2.INTER_AREA
            )

        try:
            msg = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
            msg.header.stamp = stamp
            msg.header.frame_id = self.camera_frame
            self.debug_image_pub.publish(msg)

        except Exception as exc:
            self.get_logger().warn(f'Failed to publish debug image: {exc}')

    # ==========================================================
    # Publish target
    # ==========================================================
    def publish_target(self, stamp, selected_target, distance_mm, lost=False):
        msg = PersonTarget()
        msg.header.stamp = stamp
        msg.header.frame_id = self.camera_frame

        box = selected_target["box"]
        x1, y1, x2, y2 = map(int, box)

        msg.target_id = int(selected_target["id"])
        msg.locked = True
        msg.lost = bool(lost)
        msg.confidence = float(selected_target.get("conf", 0.0))

        msg.bbox_x = x1
        msg.bbox_y = y1
        msg.bbox_w = max(0, x2 - x1)
        msg.bbox_h = max(0, y2 - y1)

        distance_m = self.depth_mm_to_m(distance_mm)
        msg.distance_m = float(distance_m) if distance_m is not None else math.nan

        u = int((x1 + x2) / 2)
        v = int((y1 + y2) / 2)

        if distance_m is not None and self.last_camera_info is not None:
            x_cam, y_cam, z_cam = self.project_pixel_to_camera(u, v, distance_m)

            msg.position_camera.header.stamp = stamp
            msg.position_camera.header.frame_id = self.camera_frame
            msg.position_camera.point.x = float(x_cam)
            msg.position_camera.point.y = float(y_cam)
            msg.position_camera.point.z = float(z_cam)

            # Góc lệch ngang trong optical frame: + là lệch sang phải ảnh.
            msg.angle_rad = float(math.atan2(x_cam, z_cam))

        else:
            msg.position_camera.header.stamp = stamp
            msg.position_camera.header.frame_id = self.camera_frame
            msg.position_camera.point.x = 0.0
            msg.position_camera.point.y = 0.0
            msg.position_camera.point.z = 0.0
            msg.angle_rad = math.nan

        # Chưa transform sang base/map ở node này.
        msg.position_base.header.stamp = stamp
        msg.position_base.header.frame_id = 'base_footprint'

        msg.position_map.header.stamp = stamp
        msg.position_map.header.frame_id = 'map'

        self.person_target_pub.publish(msg)

        self.log_info_throttle(
            0.5,
            f'Target ID={msg.target_id}, dist={msg.distance_m:.2f} m, '
            f'angle={msg.angle_rad:.2f} rad, '
            f'bbox=({msg.bbox_x},{msg.bbox_y},{msg.bbox_w},{msg.bbox_h})'
        )

    def publish_lost_target(self, stamp):
        msg = PersonTarget()
        msg.header.stamp = stamp
        msg.header.frame_id = self.camera_frame

        msg.target_id = (
            int(self.reid.current_track_id)
            if self.reid.current_track_id is not None
            else -1
        )
        msg.locked = self.reid.target_profile is not None
        msg.lost = True
        msg.confidence = 0.0

        msg.distance_m = math.nan
        msg.angle_rad = math.nan

        msg.position_camera.header.stamp = stamp
        msg.position_camera.header.frame_id = self.camera_frame
        msg.position_base.header.stamp = stamp
        msg.position_base.header.frame_id = 'base_footprint'
        msg.position_map.header.stamp = stamp
        msg.position_map.header.frame_id = 'map'

        self.person_target_pub.publish(msg)

    def depth_mm_to_m(self, distance_value):
        if distance_value is None:
            return None

        d = float(distance_value)

        if not math.isfinite(d) or d <= 0.0:
            return None

        # 16UC1 depth thường là mm. Nếu nhỏ hơn 20, có thể đã là mét.
        if d > 20.0:
            return d / 1000.0

        return d

    def project_pixel_to_camera(self, u, v, z):
        k = self.last_camera_info.k

        fx = float(k[0])
        fy = float(k[4])
        cx = float(k[2])
        cy = float(k[5])

        x = (float(u) - cx) * z / fx
        y = (float(v) - cy) * z / fy

        return x, y, z

    # ==========================================================
    # Mode manager transition
    # ==========================================================
    def request_follow_active(self):
        if self.target_locked_reported:
            return

        if not self.set_mode_client.wait_for_service(timeout_sec=0.1):
            self.get_logger().warn('/amr_ai/set_mode not available, cannot switch to FOLLOW_ACTIVE')
            return

        req = SetAiMode.Request()
        req.mode = AiMode.FOLLOW_ACTIVE
        req.command = 'TARGET_LOCKED'

        future = self.set_mode_client.call_async(req)
        future.add_done_callback(self.follow_active_response_callback)

        self.target_locked_reported = True

    def follow_active_response_callback(self, future):
        try:
            response = future.result()
        except Exception as exc:
            self.get_logger().error(f'Failed to request FOLLOW_ACTIVE: {exc}')
            return

        if response.success:
            self.get_logger().warn(f'Mode manager switched to FOLLOW_ACTIVE: {response.message}')
        else:
            self.get_logger().warn(f'Mode manager rejected FOLLOW_ACTIVE: {response.message}')


def main(args=None):
    rclpy.init(args=args)
    node = PersonTrackerNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()