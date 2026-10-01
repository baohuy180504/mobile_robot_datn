#!/usr/bin/env python3

import os
import time

import cv2
import torch

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image
from geometry_msgs.msg import PoseStamped
from cv_bridge import CvBridge
# TensorRT trực tiếp thay Ultralytics (giảm chi phí Python/framework ngoài phần GPU tính;
# xem amr_ai/core/trt_yolo.py). TrtYOLO giả lập đúng API .track()/.predict() của YOLO nên
# phần code bên dưới không cần đổi gì khác.
from amr_ai.core.trt_yolo import TrtYOLO as YOLO
from ament_index_python.packages import get_package_share_directory

from amr_interfaces.msg import AiAlert

from amr_ai.core import config as cfg
from amr_ai.detectors.fall_detector import FallDetector


class AiDetectorNode(Node):
    """
    AI detector chỉ còn nhận diện TÉ NGÃ, chạy song song ở MỌI chế độ
    (IDLE, NAV_TO_ZONE, RETURN_TO_ZONE, FOLLOW_*, ...).

    Chức năng:
    - Subscribe RGB + depth image từ camera ROS2.
    - Chạy YOLO person (có tracking) tạo detections cho FallDetector.
    - Chạy FallDetector (YOLO pose + depth) để phát hiện người té.
    - Publish /amr_ai/alert (alert_type='FALL', active=True khi có người té,
      'NORMAL' định kỳ khi không có).
    - Publish /amr_ai/debug/alert/image (ảnh có khung + chữ cảnh báo) để
      esp32_alert_bridge gửi ảnh về thiết bị và để xem trên RViz/web.

    Ai xử lý alert FALL:
    - ai_mode_manager: đang NAV_TO_ZONE/RETURN_TO_ZONE -> hủy goal, dừng xe
      (ALERT_STOPPED), chỉ chạy lại khi có lệnh mới.
    - Đang FOLLOW_*: xe KHÔNG bị dừng, chỉ hiển thị/gửi cảnh báo.
    - esp32_alert_bridge: gửi cảnh báo + ảnh về ESP32.

    Node này KHÔNG publish /cmd_vel và KHÔNG can thiệp điều khiển xe.
    Đã bỏ hoàn toàn nhận diện lửa/khói và bảo hộ: không import, không load
    model tương ứng (fire_smoke_detector.py / ppe_detector.py không còn được gọi).
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

        self.declare_parameter('detect_conf', 0.4)
        self.declare_parameter('process_every_n_frames', 2)

        # False -> không load model nào, node chỉ publish NORMAL.
        self.declare_parameter('enable_fall_alert', True)

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
        self.process_every_n_frames = max(
            1, int(self.get_parameter('process_every_n_frames').value)
        )

        self.enable_fall_alert = bool(self.get_parameter('enable_fall_alert').value)

        self.alert_topic = self.get_parameter('alert_topic').value
        self.publish_normal_status = bool(self.get_parameter('publish_normal_status').value)
        self.normal_status_period_s = float(self.get_parameter('normal_status_period_s').value)

        self.publish_debug_image_flag = bool(self.get_parameter('publish_debug_image').value)
        self.debug_image_topic = self.get_parameter('debug_image_topic').value
        self.debug_image_publish_hz = float(self.get_parameter('debug_image_publish_hz').value)
        self.debug_image_scale = float(self.get_parameter('debug_image_scale').value)

        self.bridge = CvBridge()
        self.share_dir = get_package_share_directory('amr_ai')

        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.infer_device = 0 if torch.cuda.is_available() else 'cpu'
        self.use_half = torch.cuda.is_available()

        # ======================================================
        # Models (chỉ load khi bật fall alert)
        # ======================================================
        self.person_model = None
        self.fall_detector = None

        if self.enable_fall_alert:
            person_model_path = self.resolve_model_path(
                self.get_parameter('person_model_path').value
            )
            pose_model_path = self.resolve_model_path(
                self.get_parameter('pose_model_path').value
            )

            self.get_logger().info('Loading person YOLO model for fall detector...')
            self.get_logger().info(f'Person model path: {person_model_path}')
            self.person_model = YOLO(person_model_path)

            self.get_logger().info('Loading fall pose detector...')
            self.get_logger().info(f'Pose model path: {pose_model_path}')
            self.fall_detector = FallDetector(
                pose_model_path=pose_model_path,
                infer_device=self.infer_device,
                use_half=self.use_half
            )
        else:
            self.get_logger().warn('Fall alert disabled (enable_fall_alert=false): no model loaded')

        # ======================================================
        # State
        # ======================================================
        self.frame_count = 0
        self.last_depth_msg = None

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

        self.get_logger().warn('AI Detector Node started (FALL only)')
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

        now = time.time()
        stamp = msg.header.stamp

        # Tắt fall alert: chỉ giữ heartbeat NORMAL, không đọc/convert ảnh.
        if not self.enable_fall_alert or self.fall_detector is None:
            self.publish_normal_status_if_needed(stamp, now)
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

        detections = self.run_person_detection(frame)
        detections = self.run_fall_detection(frame, depth, detections, now)

        fall_dets = [det for det in detections if det.get('falling', False)]
        fall_active = len(fall_dets) > 0

        if fall_active:
            fall_conf = max(float(det.get('conf', 0.0)) for det in fall_dets)
            modes = sorted({
                str(det.get('fall_mode', 'FALL')) for det in fall_dets
                if det.get('fall_mode', None) is not None
            })
            fall_message = 'FALL detected'
            if modes:
                fall_message += ': ' + ', '.join(modes)

            self.publish_alert(stamp, 'FALL', fall_conf, fall_message, True)
        else:
            self.publish_normal_status_if_needed(stamp, now)

        # Chỉ dựng ảnh debug khi tới lượt publish (trước đây vẽ + sao chép ảnh mỗi khung rồi mới bỏ đi).
        if self.debug_image_due(now):
            annotated = self.draw_debug_image(frame, detections, fall_active)
            self.publish_debug_image(annotated, stamp, msg.header.frame_id)

    # ==========================================================
    # Detection
    # ==========================================================
    def run_person_detection(self, frame):
        detections = []

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
    def draw_debug_image(self, frame, detections, fall_active):
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

        if fall_active:
            cv2.putText(
                annotated,
                'CANH BAO: CO NGUOI TE NGA',
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.85,
                (0, 0, 255),
                3
            )

        return annotated

    def debug_image_due(self, now):
        if not self.publish_debug_image_flag:
            return False
        if self.debug_image_publish_hz > 0.0:
            if now - self.last_debug_image_publish_time < 1.0 / self.debug_image_publish_hz:
                return False
        return True

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
