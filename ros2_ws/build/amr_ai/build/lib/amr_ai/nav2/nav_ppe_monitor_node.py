#!/usr/bin/env python3
"""
nav_ppe_monitor_node.py

Giám sát PPE (nón bảo hộ + áo phản quang) cho tối đa 3 công nhân
trong khung hình khi robot đang ở chế độ NAV_TO_ZONE / RETURN_TO_ZONE.

Tự động không hoạt động ở các mode khác (IDLE, FOLLOW_*, ALERT_STOPPED...).
Không can thiệp điều khiển xe — chỉ publish /amr_ai/alert để
esp32_alert_bridge forward sang màn hình ESP32.
"""

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
from ultralytics import YOLO
from ament_index_python.packages import get_package_share_directory

from amr_interfaces.msg import AiAlert, AiMode
from amr_ai.detectors.ppe_detector import PPEDetector


class NavPPEMonitorNode(Node):
    """
    Detect PPE cho tối đa 3 người trong NAV2 mode.

    Luồng xử lý mỗi ppe_run_interval frame:
      1. YOLO person detect → lấy tối đa max_persons box lớn nhất
      2. PPEDetector.detect(frame) → danh sách tất cả PPE item trong ảnh
      3. PPEDetector.check_person_ppe(box, ppe_items) cho từng người
      4. Nếu bất kỳ người nào thiếu PPE → tăng violation_count
         Đủ confirm_frames lần liên tiếp → alarm_active = True → publish alert
      5. Khi không còn vi phạm → tăng ok_count
         Đủ clear_frames lần → alarm_active = False
    """

    NAV_MODES = frozenset({AiMode.NAV_TO_ZONE, AiMode.RETURN_TO_ZONE})

    def __init__(self):
        super().__init__('nav_ppe_monitor_node')

        # ==========================================================
        # Parameters
        # ==========================================================
        self.declare_parameter('color_topic',  '/camera/color/image_raw')
        self.declare_parameter('mode_topic',   '/amr_ai/mode')
        self.declare_parameter('alert_topic',  '/amr_ai/alert')

        self.declare_parameter('person_model_path', 'models/yolo26n.engine')
        self.declare_parameter('ppe_model_path',    'models/ppe_s.engine')

        self.declare_parameter('detect_conf',   0.4)
        self.declare_parameter('max_persons',   3)       # tối đa 3 người cùng lúc

        # PPE inference chạy mỗi N frame (ảnh đầu vào, không phải frame đã bỏ qua)
        self.declare_parameter('ppe_run_interval',  10)

        # PPE model params — phải khớp với model đang dùng
        self.declare_parameter('ppe_imgsz',         512)
        self.declare_parameter('ppe_conf',          0.15)
        self.declare_parameter('ppe_iou',           0.50)
        self.declare_parameter('ppe_helmet_ok_conf',0.15)
        self.declare_parameter('ppe_vest_ok_conf',  0.35)

        # Cần confirm_frames lần vi phạm liên tiếp mới bật alarm
        # (tránh báo nhầm khi người quay lưng thoáng qua)
        self.declare_parameter('confirm_frames', 3)
        # Cần clear_frames lần OK liên tiếp mới tắt alarm
        self.declare_parameter('clear_frames',   5)

        # Debug image
        self.declare_parameter('publish_debug_image',    True)
        self.declare_parameter('debug_image_topic',
                               '/amr_ai/debug/nav_ppe/image')
        self.declare_parameter('debug_image_publish_hz', 3.0)
        self.declare_parameter('debug_image_scale',      0.5)

        # ----------------------------------------------------------
        # Read params
        # ----------------------------------------------------------
        self.color_topic  = self.get_parameter('color_topic').value
        self.mode_topic   = self.get_parameter('mode_topic').value
        self.alert_topic  = self.get_parameter('alert_topic').value

        self.detect_conf       = float(self.get_parameter('detect_conf').value)
        self.max_persons       = int(self.get_parameter('max_persons').value)
        self.ppe_run_interval  = max(1, int(self.get_parameter('ppe_run_interval').value))

        self.confirm_frames = int(self.get_parameter('confirm_frames').value)
        self.clear_frames   = int(self.get_parameter('clear_frames').value)

        self.publish_debug_image_flag = bool(
            self.get_parameter('publish_debug_image').value
        )
        self.debug_image_topic      = self.get_parameter('debug_image_topic').value
        self.debug_image_publish_hz = float(
            self.get_parameter('debug_image_publish_hz').value
        )
        self.debug_image_scale = float(self.get_parameter('debug_image_scale').value)

        # ==========================================================
        # Models
        # ==========================================================
        share_dir         = get_package_share_directory('amr_ai')
        infer_device      = 0 if torch.cuda.is_available() else 'cpu'

        person_path = self._resolve_model(
            share_dir, self.get_parameter('person_model_path').value
        )
        ppe_path = self._resolve_model(
            share_dir, self.get_parameter('ppe_model_path').value
        )

        self.get_logger().info(f'Loading person YOLO: {person_path}')
        self.person_model = YOLO(person_path)

        self.get_logger().info(f'Loading PPE model: {ppe_path}')
        self.ppe_detector = PPEDetector(
            model_path=ppe_path,
            infer_device=infer_device,
            imgsz=int(self.get_parameter('ppe_imgsz').value),
            conf=float(self.get_parameter('ppe_conf').value),
            iou=float(self.get_parameter('ppe_iou').value),
            helmet_ok_conf=float(self.get_parameter('ppe_helmet_ok_conf').value),
            vest_ok_conf=float(self.get_parameter('ppe_vest_ok_conf').value),
        )

        # ==========================================================
        # State
        # ==========================================================
        self.current_mode  = AiMode.IDLE
        self.frame_count   = 0  # frame counter (đếm mọi frame nhận được)

        # Confirmation counters
        self.violation_count = 0   # số lần vi phạm liên tiếp
        self.ok_count        = 0   # số lần OK liên tiếp
        self.alarm_active    = False

        # Cache kết quả PPE run gần nhất (dùng giữa các interval)
        self.last_person_boxes  = []
        self.last_person_status = []  # list[dict] từ check_person_ppe

        self.last_debug_pub_time = 0.0
        self.bridge = CvBridge()

        # ==========================================================
        # Pub / Sub
        # ==========================================================
        self.alert_pub = self.create_publisher(AiAlert, self.alert_topic, 10)
        self.debug_pub = self.create_publisher(Image, self.debug_image_topic, 1)

        self.mode_sub = self.create_subscription(
            AiMode, self.mode_topic, self._mode_cb, 10
        )
        self.color_sub = self.create_subscription(
            Image, self.color_topic, self._color_cb, qos_profile_sensor_data
        )

        self.get_logger().warn(
            'NavPPEMonitorNode started — '
            'active only in NAV_TO_ZONE / RETURN_TO_ZONE'
        )
        self.get_logger().info(
            f'max_persons={self.max_persons}  '
            f'ppe_run_interval={self.ppe_run_interval}  '
            f'confirm={self.confirm_frames}  '
            f'clear={self.clear_frames}'
        )

    # ==========================================================
    # Helpers
    # ==========================================================
    @staticmethod
    def _resolve_model(share_dir: str, path_value: str) -> str:
        if os.path.isabs(path_value):
            return path_value
        return os.path.join(share_dir, path_value)

    def _reset_state(self):
        self.violation_count    = 0
        self.ok_count           = 0
        self.alarm_active       = False
        self.last_person_boxes  = []
        self.last_person_status = []
        self.frame_count        = 0
        self.get_logger().info('NavPPEMonitor: state reset (mode changed)')

    # ==========================================================
    # ROS callbacks
    # ==========================================================
    def _mode_cb(self, msg: AiMode):
        new_mode = int(msg.mode)
        if new_mode == self.current_mode:
            return

        was_active = self.current_mode in self.NAV_MODES
        is_active  = new_mode in self.NAV_MODES

        self.current_mode = new_mode

        # Reset khi thoát khỏi NAV mode để không có state cũ lúc vào lại
        if was_active and not is_active:
            self._reset_state()

    def _color_cb(self, msg: Image):
        # Không active ngoài NAV modes
        if self.current_mode not in self.NAV_MODES:
            return

        self.frame_count += 1

        # Chỉ chạy mỗi ppe_run_interval frame
        if self.frame_count % self.ppe_run_interval != 0:
            # Vẫn publish debug image với kết quả cache nếu cần
            if self.publish_debug_image_flag:
                self._maybe_publish_debug(None, msg.header.stamp,
                                          msg.header.frame_id)
            return

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:
            self.get_logger().error(f'imgmsg_to_cv2 failed: {exc}')
            return

        self._process_frame(frame, msg.header.stamp, msg.header.frame_id)

    # ==========================================================
    # Core processing
    # ==========================================================
    def _process_frame(self, frame, stamp, frame_id):
        # 1. Detect persons — lấy tối đa max_persons box lớn nhất
        person_boxes = self._detect_persons(frame)

        # 2. Chạy PPE detector trên toàn ảnh một lần
        try:
            ppe_items = self.ppe_detector.detect(frame)
        except Exception as exc:
            self.get_logger().warn(f'PPE detect failed: {exc}')
            ppe_items = []

        # 3. Kiểm tra từng người
        person_status = []
        for box in person_boxes:
            try:
                status = self.ppe_detector.check_person_ppe(box, ppe_items)
            except Exception as exc:
                self.get_logger().warn(f'check_person_ppe failed: {exc}')
                status = {'violation': False, 'missing_helmet': False,
                          'missing_vest': False}
            person_status.append(status)

        # Cache lại để debug image dùng giữa các interval
        self.last_person_boxes  = person_boxes
        self.last_person_status = person_status

        # 4. Cập nhật confirmation counters
        any_violation = any(s.get('violation', False) for s in person_status)

        if any_violation:
            self.violation_count += 1
            self.ok_count         = 0
        else:
            self.ok_count        += 1
            self.violation_count  = 0

        # 5. Quản lý alarm state
        if not self.alarm_active and self.violation_count >= self.confirm_frames:
            self.alarm_active = True
            n_viol = sum(1 for s in person_status if s.get('violation', False))
            self.get_logger().warn(
                f'PPE ALARM ON: {n_viol}/{len(person_status)} worker(s) '
                f'missing PPE (confirm_frames={self.confirm_frames})'
            )

        if self.alarm_active and self.ok_count >= self.clear_frames:
            self.alarm_active    = False
            self.violation_count = 0
            self.get_logger().info('PPE alarm cleared: all workers PPE OK')

        # 6. Publish alert
        if self.alarm_active:
            alert_type = self._determine_alert_type(person_status)
            self._publish_alert(stamp, alert_type, person_status)

        # 7. Debug image
        self._maybe_publish_debug(frame, stamp, frame_id)

    # ==========================================================
    # Person detection
    # ==========================================================
    def _detect_persons(self, frame):
        """
        Detect người trong ảnh, trả về tối đa max_persons box.
        Ưu tiên người có box diện tích lớn nhất (gần camera nhất).
        """
        try:
            results = self.person_model.predict(
                frame,
                classes=[0],          # class 0 = person
                conf=self.detect_conf,
                verbose=False
            )
        except Exception as exc:
            self.get_logger().warn(f'Person detect failed: {exc}')
            return []

        boxes_obj = results[0].boxes if results and len(results) > 0 else None
        if boxes_obj is None or boxes_obj.xyxy is None:
            return []

        xyxy = boxes_obj.xyxy.cpu().numpy()
        if len(xyxy) == 0:
            return []

        # Sort theo diện tích box giảm dần (người gần camera trước)
        areas = [(x2 - x1) * (y2 - y1) for x1, y1, x2, y2 in xyxy]
        order = sorted(range(len(areas)), key=lambda i: areas[i], reverse=True)

        return [xyxy[i] for i in order[:self.max_persons]]

    # ==========================================================
    # Alert helpers
    # ==========================================================
    def _determine_alert_type(self, person_status):
        """
        Xác định alert_type dựa trên tổng hợp vi phạm của mọi người.
        Ưu tiên: MISSING_PPE > MISSING_HELMET > MISSING_VEST.
        """
        any_no_helmet = any(s.get('missing_helmet', False) for s in person_status)
        any_no_vest   = any(s.get('missing_vest',   False) for s in person_status)

        if any_no_helmet and any_no_vest:
            return 'MISSING_PPE'
        if any_no_helmet:
            return 'MISSING_HELMET'
        if any_no_vest:
            return 'MISSING_VEST'
        return 'MISSING_PPE'

    def _publish_alert(self, stamp, alert_type: str, person_status):
        violations = [s for s in person_status if s.get('violation', False)]
        conf = max(
            (
                max(float(s.get('no_helmet_score', 0.0)),
                    float(s.get('no_vest_score',   0.0)))
                for s in violations
            ),
            default=0.5
        )

        msg = AiAlert()
        msg.stamp      = stamp
        msg.alert_type = alert_type
        msg.confidence = float(conf)
        msg.message    = (
            f'PPE violation during NAV2: '
            f'{len(violations)}/{len(person_status)} worker(s) missing PPE'
        )
        msg.active     = True

        msg.robot_pose = PoseStamped()
        msg.robot_pose.header.stamp    = stamp
        msg.robot_pose.header.frame_id = 'map'

        msg.image_path = ''

        self.alert_pub.publish(msg)

        self.get_logger().info(
            f'Alert published: {alert_type}  '
            f'violators={len(violations)}/{len(person_status)}'
        )

    # ==========================================================
    # Debug image
    # ==========================================================
    def _maybe_publish_debug(self, frame, stamp, frame_id):
        if not self.publish_debug_image_flag:
            return

        now = time.time()
        if (self.debug_image_publish_hz > 0.0
                and now - self.last_debug_pub_time < 1.0 / self.debug_image_publish_hz):
            return

        # Nếu không có frame mới (gọi từ non-PPE frames) dùng cache
        if frame is None:
            if not self.last_person_boxes:
                return
            # Không publish ảnh debug nếu không có frame mới — bỏ qua
            return

        self.last_debug_pub_time = now
        annotated = frame.copy()

        for i, box in enumerate(self.last_person_boxes):
            x1, y1, x2, y2 = map(int, box)
            status = (
                self.last_person_status[i]
                if i < len(self.last_person_status)
                else None
            )

            if status is None:
                color = (128, 128, 128)
                label = f'P{i+1} CHECK...'
            elif status.get('violation', False):
                color = (0, 0, 255)
                missing = []
                if status.get('missing_helmet'):
                    missing.append('NON')
                if status.get('missing_vest'):
                    missing.append('AO')
                label = f'P{i+1} THIEU ' + '+'.join(missing)
            else:
                color = (0, 255, 0)
                label = f'P{i+1} PPE OK'

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                annotated, label,
                (x1, max(22, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2
            )

        # Header cảnh báo
        if self.alarm_active:
            cv2.putText(
                annotated,
                'CANH BAO: THIEU BAO HO LAO DONG',
                (20, 36),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3
            )

        # Footer: mode + node label
        h = annotated.shape[0]
        cv2.putText(
            annotated,
            f'NAV PPE MONITOR  mode={self.current_mode}  '
            f'max={self.max_persons}  alarm={self.alarm_active}',
            (8, h - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 220, 0), 1
        )

        if self.debug_image_scale != 1.0:
            annotated = cv2.resize(
                annotated, None,
                fx=self.debug_image_scale,
                fy=self.debug_image_scale,
                interpolation=cv2.INTER_AREA
            )

        try:
            img_msg = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
            img_msg.header.stamp    = stamp
            img_msg.header.frame_id = frame_id
            self.debug_pub.publish(img_msg)
        except Exception as exc:
            self.get_logger().warn(f'Debug image publish failed: {exc}')


# ==========================================================
def main(args=None):
    rclpy.init(args=args)
    node = NavPPEMonitorNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()