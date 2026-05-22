#!/usr/bin/env python3

import os
import time

import cv2
import numpy as np
import torch

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image
from geometry_msgs.msg import PoseStamped
from cv_bridge import CvBridge
from ultralytics import YOLO
from ament_index_python.packages import get_package_share_directory

from amr_interfaces.msg import AiAlert

from amr_ai.core import config as cfg
from amr_ai.core.utils import valid_box_size, center_distance_sq
from amr_ai.detectors.fall_detector import FallDetector
from amr_ai.detectors.fire_smoke_detector import FireSmokeDetector


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


class AiDetectorNode(Node):
    """
    AI detector chạy song song với hệ follow/navigation.

    Chức năng:
    - Subscribe RGB + depth image từ camera ROS2.
    - Chạy YOLO person để tạo detections đầu vào cho FallDetector.
    - Chạy FallDetector để phát hiện người té.
    - Chạy FireSmokeDetector để phát hiện lửa/khói.
    - Publish /amr_ai/alert.
    - Publish /amr_ai/debug/alert/image để xem trên RViz.

    Node này KHÔNG publish /cmd_vel và KHÔNG can thiệp điều khiển xe.
    """

    def __init__(self):
        super().__init__('ai_detector_node')

        # ======================================================
        # Parameters
        # ======================================================
        self.declare_parameter('color_topic', '/camera/color/image_raw')
        self.declare_parameter('depth_topic', '/camera/depth/image_raw')

        self.declare_parameter('person_model_path', 'models/yolo26n.engine')
        self.declare_parameter('pose_model_path', 'models/yolo26n-pose.engine')
        self.declare_parameter('fire_smoke_model_path', 'models/fire_smoke_s.engine')

        self.declare_parameter('detect_conf', 0.4)
        self.declare_parameter('process_every_n_frames', 2)

        self.declare_parameter('enable_fall_alert', True)
        self.declare_parameter('enable_fire_smoke_alert', True)

        self.declare_parameter('fire_smoke_run_interval', 5)
        self.declare_parameter('fire_alert_hold_sec', 2.0)
        self.declare_parameter('smoke_alert_hold_sec', 2.0)

        self.declare_parameter('fire_conf', 0.5)
        self.declare_parameter('smoke_conf', 0.8)
        self.declare_parameter('fire_smoke_imgsz', 640)

        self.declare_parameter('alert_topic', '/amr_ai/alert')
        self.declare_parameter('publish_normal_status', True)
        self.declare_parameter('normal_status_period_s', 1.0)

        self.declare_parameter('publish_debug_image', True)
        self.declare_parameter('debug_image_topic', '/amr_ai/debug/alert/image')
        self.declare_parameter('debug_image_publish_hz', 3.0)
        self.declare_parameter('debug_image_scale', 0.5)

        self.color_topic = self.get_parameter('color_topic').value
        self.depth_topic = self.get_parameter('depth_topic').value

        self.detect_conf = float(self.get_parameter('detect_conf').value)
        self.process_every_n_frames = max(1, int(self.get_parameter('process_every_n_frames').value))

        self.enable_fall_alert = bool(self.get_parameter('enable_fall_alert').value)
        self.enable_fire_smoke_alert = bool(self.get_parameter('enable_fire_smoke_alert').value)

        self.fire_smoke_run_interval = max(1, int(self.get_parameter('fire_smoke_run_interval').value))
        self.fire_alert_hold_sec = float(self.get_parameter('fire_alert_hold_sec').value)
        self.smoke_alert_hold_sec = float(self.get_parameter('smoke_alert_hold_sec').value)

        self.fire_conf = float(self.get_parameter('fire_conf').value)
        self.smoke_conf = float(self.get_parameter('smoke_conf').value)
        self.fire_smoke_imgsz = int(self.get_parameter('fire_smoke_imgsz').value)

        self.alert_topic = self.get_parameter('alert_topic').value
        self.publish_normal_status = bool(self.get_parameter('publish_normal_status').value)
        self.normal_status_period_s = float(self.get_parameter('normal_status_period_s').value)

        self.publish_debug_image_flag = bool(self.get_parameter('publish_debug_image').value)
        self.debug_image_topic = self.get_parameter('debug_image_topic').value
        self.debug_image_publish_hz = float(self.get_parameter('debug_image_publish_hz').value)
        self.debug_image_scale = float(self.get_parameter('debug_image_scale').value)

        self.bridge = CvBridge()
        self.share_dir = get_package_share_directory('amr_ai')

        self.person_model_path = self.resolve_model_path(self.get_parameter('person_model_path').value)
        self.pose_model_path = self.resolve_model_path(self.get_parameter('pose_model_path').value)
        self.fire_smoke_model_path = self.resolve_model_path(self.get_parameter('fire_smoke_model_path').value)

        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.infer_device = 0 if torch.cuda.is_available() else 'cpu'
        self.use_half = torch.cuda.is_available()

        # ======================================================
        # Models
        # ======================================================
        self.person_model = None
        self.fall_detector = None
        self.fire_smoke_detector = None

        if self.enable_fall_alert:
            self.get_logger().info('Loading person YOLO model for fall detector...')
            self.get_logger().info(f'Person model path: {self.person_model_path}')
            self.person_model = YOLO(self.person_model_path)

            self.get_logger().info('Loading fall pose detector...')
            self.get_logger().info(f'Pose model path: {self.pose_model_path}')
            self.fall_detector = FallDetector(
                pose_model_path=self.pose_model_path,
                infer_device=self.infer_device,
                use_half=self.use_half
            )

        if self.enable_fire_smoke_alert:
            self.get_logger().info('Loading fire/smoke detector...')
            self.get_logger().info(f'Fire/smoke model path: {self.fire_smoke_model_path}')
            self.fire_smoke_detector = FireSmokeDetector(
                model_path=self.fire_smoke_model_path,
                infer_device=self.infer_device,
                imgsz=self.fire_smoke_imgsz,
                fire_conf=self.fire_conf,
                smoke_conf=self.smoke_conf
            )

        # ======================================================
        # State
        # ======================================================
        self.frame_count = 0
        self.last_depth_msg = None

        self.last_fire_smoke_detections = []
        self.last_fire_time = 0.0
        self.last_smoke_time = 0.0
        self.last_fire_conf = 0.0
        self.last_smoke_conf = 0.0

        self.last_normal_publish_time = 0.0
        self.last_debug_image_publish_time = 0.0

        # ======================================================
        # Pub/Sub
        # ======================================================
        self.alert_pub = self.create_publisher(AiAlert, self.alert_topic, 10)
        self.debug_image_pub = self.create_publisher(Image, self.debug_image_topic, 1)

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

        self.get_logger().warn('AI Detector Node started')
        self.get_logger().info(f'Color topic: {self.color_topic}')
        self.get_logger().info(f'Depth topic: {self.depth_topic}')
        self.get_logger().info(f'Alert topic: {self.alert_topic}')
        self.get_logger().info(f'Debug image topic: {self.debug_image_topic}')
        self.get_logger().info(f'Device: {self.device}')

    def resolve_model_path(self, path_value: str) -> str:
        if os.path.isabs(path_value):
            return path_value
        return os.path.join(self.share_dir, path_value)

    # ==========================================================
    # ROS callbacks
    # ==========================================================
    def depth_callback(self, msg: Image):
        self.last_depth_msg = msg

    def color_callback(self, msg: Image):
        self.frame_count += 1

        if self.frame_count % self.process_every_n_frames != 0:
            return

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:
            self.get_logger().error(f'Failed to convert color image: {exc}')
            return

        depth = None
        if self.last_depth_msg is not None:
            try:
                depth = self.bridge.imgmsg_to_cv2(
                    self.last_depth_msg,
                    desired_encoding='passthrough'
                )
            except Exception as exc:
                self.get_logger().warn(f'Failed to convert depth image: {exc}')
                depth = None

        now = time.time()
        stamp = msg.header.stamp

        detections = []
        fall_active = False
        fall_conf = 0.0
        fall_message = ''

        if self.enable_fall_alert and self.person_model is not None and self.fall_detector is not None:
            detections = self.run_person_detection(frame)
            detections = self.run_fall_detection(frame, depth, detections, now)

            fall_dets = [det for det in detections if det.get('falling', False)]
            if fall_dets:
                fall_active = True
                fall_conf = max(float(det.get('conf', 0.0)) for det in fall_dets)
                modes = sorted({
                    str(det.get('fall_mode', 'FALL')) for det in fall_dets
                    if det.get('fall_mode', None) is not None
                })
                fall_message = 'FALL detected'
                if modes:
                    fall_message += ': ' + ', '.join(modes)

        fire_detections = []
        fire_active = False
        smoke_active = False
        fire_conf = 0.0
        smoke_conf = 0.0

        if self.enable_fire_smoke_alert and self.fire_smoke_detector is not None:
            fire_detections, fire_active, smoke_active, fire_conf, smoke_conf = (
                self.run_fire_smoke_detection(frame, now)
            )

        if fall_active:
            self.publish_alert(stamp, 'FALL', fall_conf, fall_message, True)

        if fire_active:
            self.publish_alert(stamp, 'FIRE', fire_conf, 'FIRE detected', True)

        if smoke_active:
            self.publish_alert(stamp, 'SMOKE', smoke_conf, 'SMOKE detected', True)

        if not fall_active and not fire_active and not smoke_active:
            self.publish_normal_status_if_needed(stamp, now)

        annotated = self.draw_debug_image(
            frame,
            detections,
            fire_detections,
            fall_active,
            fire_active,
            smoke_active
        )
        self.publish_debug_image(annotated, stamp, msg.header.frame_id)

    # ==========================================================
    # Detection
    # ==========================================================
    def run_person_detection(self):
        pass

    def run_person_detection(self, frame):
        detections = []
        h, w = frame.shape[:2]
        center_x = w // 2
        center_y = h // 2

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

            results = self.person_model.track(**track_kwargs)

        except Exception as exc:
            self.get_logger().warn(f'Person track failed, fallback to predict: {exc}')
            results = self.person_model.predict(
                frame,
                classes=[0],
                conf=self.detect_conf,
                verbose=False
            )

        boxes = results[0].boxes if results and len(results) > 0 else None

        if boxes is None or boxes.xyxy is None:
            return detections

        xyxy = boxes.xyxy.cpu().numpy()
        ids = (
            boxes.id.int().cpu().tolist()
            if boxes.id is not None
            else list(range(1, len(xyxy) + 1))
        )
        confs = boxes.conf.cpu().numpy() if boxes.conf is not None else [0.0] * len(xyxy)

        _, _ = get_nearest_track(xyxy, ids, center_x, center_y)

        for box, tid, conf in zip(xyxy, ids, confs):
            detections.append({
                'id': int(tid),
                'box': box,
                'conf': float(conf),
                'emb_sim': None,
                'shirt_sim': None,
                'motion_sim': None,
                'score': None,
                'falling': False,
                'fall_mode': None,
            })

        return detections

    def run_fall_detection(self, frame, depth, detections, now):
        if not detections:
            return detections

        h, w = frame.shape[:2]
        center_x = w // 2
        center_y = h // 2

        try:
            return self.fall_detector.update(
                frame,
                depth,
                detections,
                center_x,
                center_y,
                h,
                self.frame_count,
                now
            )
        except Exception as exc:
            self.get_logger().warn(f'Fall detector update failed: {exc}')
            return detections

    def run_fire_smoke_detection(self, frame, now):
        run_now = (self.frame_count % self.fire_smoke_run_interval) == 0

        if run_now:
            try:
                detections, fire_now, smoke_now = self.fire_smoke_detector.detect(frame)
                self.last_fire_smoke_detections = detections

                if fire_now:
                    self.last_fire_time = now
                    self.last_fire_conf = self.max_conf_for_class(detections, 'fire')

                if smoke_now:
                    self.last_smoke_time = now
                    self.last_smoke_conf = self.max_conf_for_class(detections, 'smoke')

            except Exception as exc:
                self.get_logger().warn(f'Fire/smoke detector failed: {exc}')
                self.last_fire_smoke_detections = []

        fire_active = (now - self.last_fire_time) <= self.fire_alert_hold_sec
        smoke_active = (now - self.last_smoke_time) <= self.smoke_alert_hold_sec

        return (
            self.last_fire_smoke_detections,
            fire_active,
            smoke_active,
            self.last_fire_conf if fire_active else 0.0,
            self.last_smoke_conf if smoke_active else 0.0
        )

    @staticmethod
    def max_conf_for_class(detections, class_name: str) -> float:
        confs = [
            float(det.get('conf', 0.0))
            for det in detections
            if str(det.get('class_name', '')).lower() == class_name
        ]

        if not confs:
            return 0.0

        return max(confs)

    # ==========================================================
    # Alert publishing
    # ==========================================================
    def publish_alert(self, stamp, alert_type: str, confidence: float, message: str, active: bool):
        msg = AiAlert()
        msg.stamp = stamp
        msg.alert_type = alert_type
        msg.confidence = float(confidence)
        msg.message = message
        msg.active = bool(active)

        msg.robot_pose = PoseStamped()
        msg.robot_pose.header.stamp = stamp
        msg.robot_pose.header.frame_id = 'map'

        msg.image_path = ''

        self.alert_pub.publish(msg)

    def publish_normal_status_if_needed(self, stamp, now):
        if not self.publish_normal_status:
            return

        if now - self.last_normal_publish_time < self.normal_status_period_s:
            return

        self.last_normal_publish_time = now

        self.publish_alert(
            stamp=stamp,
            alert_type='NORMAL',
            confidence=0.0,
            message='No AI alert',
            active=False
        )

    # ==========================================================
    # Debug image
    # ==========================================================
    def draw_debug_image(self, frame, detections, fire_detections, fall_active, fire_active, smoke_active):
        annotated = frame.copy()

        for det in detections:
            box = det.get('box', None)
            if box is None:
                continue

            x1, y1, x2, y2 = map(int, box)
            is_falling = bool(det.get('falling', False))

            if is_falling:
                color = (0, 0, 255)
                label = f"FALL {det.get('fall_mode', '')}"
            else:
                color = (0, 255, 255)
                label = f"Person {int(det.get('id', -1))} {float(det.get('conf', 0.0)):.2f}"

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                annotated,
                label,
                (x1, max(25, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                color,
                2
            )

        for det in fire_detections:
            x1, y1, x2, y2 = map(int, det['box'])
            class_name = str(det.get('class_name', 'unknown')).lower()
            conf = float(det.get('conf', 0.0))

            if class_name == 'fire':
                color = (0, 0, 255)
                label = f'FIRE {conf:.2f}'
            else:
                color = (160, 160, 160)
                label = f'SMOKE {conf:.2f}'

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                annotated,
                label,
                (x1, max(25, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                color,
                2
            )

        y = 35
        if fall_active:
            cv2.putText(
                annotated,
                'CANH BAO: CO NGUOI TE NGA',
                (20, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.85,
                (0, 0, 255),
                3
            )
            y += 35

        if fire_active and smoke_active:
            text = 'CANH BAO: CO LUA VA KHOI'
            color = (0, 0, 255)
        elif fire_active:
            text = 'CANH BAO: CO LUA'
            color = (0, 0, 255)
        elif smoke_active:
            text = 'CANH BAO: CO KHOI'
            color = (0, 140, 255)
        else:
            text = None
            color = (255, 255, 255)

        if text is not None:
            cv2.putText(
                annotated,
                text,
                (20, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.85,
                color,
                3
            )

        return annotated

    def publish_debug_image(self, annotated, stamp, frame_id):
        if not self.publish_debug_image_flag:
            return

        now = time.time()

        if self.debug_image_publish_hz > 0.0:
            min_period = 1.0 / self.debug_image_publish_hz
            if now - self.last_debug_image_publish_time < min_period:
                return

        self.last_debug_image_publish_time = now

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
            msg.header.frame_id = frame_id
            self.debug_image_pub.publish(msg)

        except Exception as exc:
            self.get_logger().warn(f'Failed to publish debug image: {exc}')


def main(args=None):
    rclpy.init(args=args)
    node = AiDetectorNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
