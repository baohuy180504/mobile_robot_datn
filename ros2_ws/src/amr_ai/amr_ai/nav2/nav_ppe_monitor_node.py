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
import math

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


# ==========================================================
# COCO 17-keypoint indices — đúng convention dùng trong
# fall_detector.py (nose=0, shoulders=5/6, hips=11/12...)
# ==========================================================
KPT_NOSE          = 0
KPT_LEFT_EYE      = 1
KPT_RIGHT_EYE     = 2
KPT_LEFT_EAR      = 3
KPT_RIGHT_EAR     = 4
KPT_LEFT_SHOULDER = 5
KPT_RIGHT_SHOULDER = 6
KPT_LEFT_ELBOW    = 7
KPT_RIGHT_ELBOW   = 8
KPT_LEFT_WRIST    = 9
KPT_RIGHT_WRIST   = 10
KPT_LEFT_HIP      = 11
KPT_RIGHT_HIP     = 12

# Keypoint vùng đầu — dùng để xác định đầu có thực sự nhìn rõ không
HEAD_KPTS = (KPT_NOSE, KPT_LEFT_EYE, KPT_RIGHT_EYE, KPT_LEFT_EAR, KPT_RIGHT_EAR)

# Keypoint vai — chỉ đủ để biết VAI nhìn thấy, KHÔNG đủ để suy ra áo
# nhìn thấy (vai có thể lộ trong khi thân dưới vẫn bị che bởi bàn/ghế)
SHOULDER_KPTS = (KPT_LEFT_SHOULDER, KPT_RIGHT_SHOULDER)

# Keypoint cổ tay — dùng để xác định BÀN TAY có nhìn thấy không, làm
# điều kiện cho việc xét THIẾU GĂNG TAY (tương tự đầu→mũ, thân→áo).
# Găng tay đeo ở bàn tay, ngay sau cổ tay, nên cổ tay nhìn rõ là dấu
# hiệu vùng bàn tay (nơi găng nằm) cũng nhìn thấy được.
WRIST_KPTS = (KPT_LEFT_WRIST, KPT_RIGHT_WRIST)

# Keypoint hông — tín hiệu ĐÁNG TIN CẬY hơn để biết vùng thân (nơi áo
# nằm, giữa vai-hông) có thực sự nhìn thấy hay không. Hông lộ ra nghĩa
# là cả vùng giữa thân (áo) nhiều khả năng cũng lộ theo.
HIP_KPTS = (KPT_LEFT_HIP, KPT_RIGHT_HIP)

# Giữ lại để tương thích — không còn dùng trực tiếp cho phân loại nữa
TORSO_KPTS = (KPT_LEFT_SHOULDER, KPT_RIGHT_SHOULDER, KPT_LEFT_HIP, KPT_RIGHT_HIP)

# Keypoint dùng để xác nhận đây THỰC SỰ là 1 người (không phải tay/chân
# lẻ lọt vào khung). Gồm CẢ đầu lẫn thân: một khuôn mặt rõ (nose+eye/ear)
# cũng là bằng chứng đủ mạnh là người thật — tay/chân không có các điểm
# này nên không lo bị nhận nhầm. Việc gộp cả đầu giúp không loại oan
# trường hợp người bị che thân, chỉ còn lộ đầu (trước đây chỉ tính
# vai/hông nên các case này bị loại nhầm "mất detect người").
BODY_VALIDATION_KPTS = HEAD_KPTS + TORSO_KPTS


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

    NAV_MODES = frozenset({AiMode.IDLE, AiMode.NAV_TO_ZONE, AiMode.RETURN_TO_ZONE, AiMode.ALERT_STOPPED})

    def __init__(self):
        super().__init__('nav_ppe_monitor_node')

        # ==========================================================
        # Parameters
        # ==========================================================
        self.declare_parameter('color_topic',  '/camera/color/image_raw')
        self.declare_parameter('mode_topic',   '/amr_ai/mode')
        self.declare_parameter('alert_topic',  '/amr_ai/alert')

        # [LEGACY — không còn dùng để load model, giữ lại tương thích YAML cũ]
        self.declare_parameter('person_model_path', 'models/yolo26n.engine')
        self.declare_parameter('ppe_model_path',    'models/ppe_s.engine')

        # ----------------------------------------------------------
        # Pose model — THAY THẾ person_model (không chạy thêm inference
        # song song). Pose model output cả box LẪN 17 keypoint COCO
        # trong 1 lần predict, nên tổng số inference/frame KHÔNG đổi
        # (vẫn 2: pose + PPE), chỉ đổi loại model dùng cho bước 1.
        # ----------------------------------------------------------
        self.declare_parameter('pose_model_path', 'models/yolo26n-pose.engine')

        # Ngưỡng confidence để coi 1 keypoint là "nhìn thấy được"
        self.declare_parameter('kpt_conf_threshold', 0.30)

        # Số keypoint thân (2 vai + 2 hông + mũi) tối thiểu phải nhìn
        # thấy được để chấp nhận đây là người thật (loại tay/chân lẻ)
        self.declare_parameter('min_valid_body_kpts', 2)

        # Ngưỡng box detection confidence để TIN TRỰC TIẾP không cần
        # thêm điều kiện keypoint — box_conf cao nghĩa là model đã rất
        # chắc đây là 1 người dựa trên silhouette tổng thể, kể cả khi
        # góc nghiêng/che khuất khiến keypoint không rõ.
        self.declare_parameter('high_conf_box_threshold', 0.60)

        # Số keypoint vùng đầu (mũi + 2 mắt + 2 tai) có conf cao nhất
        # phải đạt ngưỡng này thì mới coi là "đầu nhìn rõ" — nếu không,
        # suppress missing_helmet (đầu cúi/quay đi, không đủ căn cứ).
        self.declare_parameter('head_kpt_conf_threshold', 0.30)

        # Ngưỡng conf MẠNH cho keypoint đầu — chỉ khi đầu thật sự rõ
        # ràng (hướng về camera) mới đủ căn cứ xét mũ. Cao hơn ngưỡng
        # thường để loại trường hợp cúi đầu chỉ còn ló 1 tai/mắt với
        # conf trung bình (gây báo thiếu nón oan khi cúi).
        self.declare_parameter('head_kpt_strong_conf', 0.50)

        # Số keypoint đầu MẠNH tối thiểu để coi đầu nhìn rõ. 2 điểm
        # (vd mũi+mắt, hoặc 2 mắt) đảm bảo mặt hướng camera, không phải
        # chỉ 1 điểm lẻ ló ra khi cúi.
        self.declare_parameter('min_head_kpts_visible', 2)

        # Ngưỡng conf cho keypoint HÔNG — cao hơn ngưỡng thường vì pose
        # model hay NỘI SUY vị trí hông với confidence khá cao kể cả khi
        # hông bị vật che (ôm thùng hàng trước bụng). Ngưỡng cao giúp
        # phân biệt hông THẬT SỰ nhìn thấy với hông chỉ được đoán.
        self.declare_parameter('hip_kpt_conf_threshold', 0.55)

        # [LEGACY — không còn dùng để phân loại, giữ tương thích YAML cũ.
        #  Đã thay bằng min_hip_kpts_for_full_body bên dưới, đáng tin
        #  cậy hơn vì vai lộ ra không đủ chứng minh vùng áo cũng lộ theo]
        self.declare_parameter('min_torso_kpts_for_full_body', 2)

        # Số keypoint HÔNG tối thiểu để coi là FULL_BODY (thân thực sự
        # nhìn thấy được, đủ căn cứ check áo). Chỉ cần 1 hông lộ ra là
        # đủ — đảm bảo vùng giữa thân (nơi áo nằm) khả năng cao cũng lộ.
        self.declare_parameter('min_hip_kpts_for_full_body', 1)

        # Ngưỡng conf cho keypoint CỔ TAY — proxy cho bàn tay (nơi đeo
        # găng). Cao hơn ngưỡng thường vì pose hay nội suy cổ tay khi
        # tay khuất (sau lưng/trong túi) → ngưỡng cao phân biệt tay
        # THẬT SỰ nhìn thấy với tay chỉ được đoán vị trí.
        self.declare_parameter('wrist_kpt_conf_threshold', 0.50)

        # Số cổ tay tối thiểu nhìn rõ để xét THIẾU GĂNG. 1 là đủ — nếu
        # 1 tay đã không đeo găng thì đã vi phạm, không cần thấy cả 2.
        self.declare_parameter('min_wrist_kpts_visible', 1)

        # Hệ số làm mượt (EMA) cho confidence keypoint vùng đầu, giảm
        # chập chờn báo/không báo khi cúi đầu do nhiễu confidence dao
        # động quanh ngưỡng giữa các frame. alpha càng nhỏ càng mượt
        # nhưng phản ứng chậm hơn; 1.0 = không làm mượt (dùng giá trị
        # frame hiện tại trực tiếp).
        self.declare_parameter('head_conf_smoothing_alpha', 0.4)

        # Nới rộng box (theo % chiều rộng/cao box) trước khi tìm
        # helmet/vest — bù trừ box pose model khít hơn box detection
        # thường, tránh bỏ sót mũ/áo nằm sát mép box.
        self.declare_parameter('ppe_match_margin_ratio', 0.15)

        # Tỉ lệ overlap tối thiểu (item ∩ person / item) để coi 1 PPE
        # item là "thuộc về" người này. Dùng overlap thay vì tâm-điểm
        # giúp không bỏ sót vest khi người nghiêng/cầm vật làm box vest
        # lệch ra mép. Thấp (0.3) = dễ match hơn, giảm báo thiếu áo oan.
        self.declare_parameter('ppe_match_min_overlap', 0.30)

        # Góc nghiêng thân tối thiểu (độ, so với phương ngang — như
        # fall_detector) để được phép báo THIẾU ÁO. 90°=thẳng đứng,
        # nhỏ dần=nghiêng/cúi. Dưới ngưỡng này (nghiêng nhiều) → vùng
        # áo bị co ngắn theo góc nhìn, PPE model khó detect → không đủ
        # tin để báo thiếu. Mặc định 55° (nghiêng vừa phải vẫn xét,
        # nghiêng/cúi nhiều thì bỏ qua).
        self.declare_parameter('min_torso_angle_for_vest_check', 55.0)

        # Box aspect (h/w) tối thiểu để coi người ĐỨNG THẲNG theo hình
        # học — nguồn tín hiệu thẳng đứng ĐỘC LẬP với keypoint hông
        # (cần cho case đứng thẳng mà hông conf thấp). Người đứng cao &
        # hẹp (aspect ~2-3); ngồi/cúi thấp & rộng (aspect <1.5).
        self.declare_parameter('upright_box_aspect_min', 1.80)

        # Mũi phải cao hơn vai ít nhất tỉ lệ này (so với khoảng vai) thì
        # mới coi đầu NGẨNG (không cúi gục). Nhỏ → chỉ loại gục hẳn.
        self.declare_parameter('head_above_shoulder_ratio', 0.15)

        # Tỉ lệ dọc/ngang tối thiểu (vai-hông) để coi thân ĐỨNG THẲNG —
        # robust với xoay ngang/xoay lưng (thay cho torso_angle atan2 vốn
        # bị lệch khi xoay hướng). ~1.0 = phần dọc ít nhất bằng phần
        # ngang. Giảm → dễ coi là đứng hơn (chấp nhận nghiêng nhiều hơn).
        self.declare_parameter('torso_vertical_ratio_min', 1.0)

        # Bề rộng cho phép (tỉ lệ khoảng vai) để coi cổ tay/khuỷu tay là
        # "gần trục giữa thân" khi phát hiện tay ôm vật che thân. Lớn hơn
        # → dễ kết luận che hơn (nhạy hơn).
        self.declare_parameter('hands_cover_x_ratio', 0.60)

        # Bật log chẩn đoán chi tiết (keypoint counts, torso angle) để
        # tinh chỉnh ngưỡng theo dữ liệu thật. Tắt khi chạy production.
        self.declare_parameter('diag_logging', False)

        self.declare_parameter('detect_conf',   0.4)
        self.declare_parameter('max_persons',   3)       # tối đa 3 người cùng lúc

        # PPE inference chạy mỗi N frame (ảnh đầu vào, không phải frame đã bỏ qua)
        self.declare_parameter('ppe_run_interval',  10)

        # PPE model params — phải khớp với model đang dùng
        self.declare_parameter('ppe_imgsz',         640)
        self.declare_parameter('ppe_conf',          0.15)
        self.declare_parameter('ppe_iou',           0.50)
        self.declare_parameter('ppe_helmet_ok_conf',0.15)
        self.declare_parameter('ppe_vest_ok_conf',  0.35)
        # Ngưỡng conf để coi tìm thấy GĂNG TAY (class 'gloves' trong
        # ppe_s.engine). Giữ trong node này, không đụng ppe_detector.py.
        self.declare_parameter('ppe_gloves_ok_conf', 0.30)

        # ----------------------------------------------------------
        # Bật/tắt detect từng loại PPE độc lập (tiện test). Tắt loại
        # nào → bỏ qua HOÀN TOÀN việc xét và báo thiếu loại đó (coi như
        # luôn "đạt", không bao giờ vi phạm vì loại đó).
        # ----------------------------------------------------------
        self.declare_parameter('enable_helmet_check', True)
        self.declare_parameter('enable_vest_check',   True)
        self.declare_parameter('enable_gloves_check', True)

        # Cần confirm_frames lần vi phạm liên tiếp mới bật alarm
        # (tránh báo nhầm khi người quay lưng thoáng qua)
        self.declare_parameter('confirm_frames', 3)
        # Cần clear_frames lần OK liên tiếp mới tắt alarm
        self.declare_parameter('clear_frames',   5)

        # ----------------------------------------------------------
        # Geometry filter — lọc box bộ phận cơ thể (tay/chân/thân không đầu)
        # ----------------------------------------------------------
        # Chiều cao box tối thiểu tính theo % frame height.
        # Lọc cánh tay/chân nằm ngang nhỏ.  Để nhỏ (~0.12) tránh bỏ sót
        # công nhân đứng xa.
        self.declare_parameter('min_person_height_ratio', 0.12)

        # Tỉ lệ height/width tối thiểu của person box.
        # Người đứng/ngồi luôn cao hơn rộng (h/w ≥ 0.70).
        # Cánh tay nằm ngang có h/w ≈ 0.3 → bị lọc.
        self.declare_parameter('min_person_aspect_ratio', 0.70)

        # Nếu y1 (mép trên box) < N% chiều cao frame thì đầu người
        # có khả năng đã ngoài khung → không báo missing_helmet.
        self.declare_parameter('head_clip_margin_ratio', 0.05)

        # Chỉ suppress "uncertain" detection (cả 2 score=0) khi box NHỎ
        # hơn N% chiều cao frame (khả năng cao là người xa/partial-view).
        # Với box LỚN (người gần, nhìn rõ) mà vẫn uncertain → giữ
        # missing=True, vì model đủ resolution để tự tin nếu thật có PPE.
        self.declare_parameter('uncertain_suppress_max_height_ratio', 0.35)

        # ----------------------------------------------------------
        # Head-only classification — xử lý trường hợp thân bị che,
        # chỉ lộ phần đầu (ví dụ: ngồi sau bàn/máy, thân bị vật cản).
        # ----------------------------------------------------------
        # Box có h/w >= ngưỡng này → coi là FULL BODY (đủ thân để check áo).
        # Box có h/w < ngưỡng này (nhưng vẫn pass min_person_aspect_ratio)
        # → coi là HEAD_ONLY: chỉ check mũ trên toàn bộ box, KHÔNG check áo
        # (vì thân không nằm trong box để đánh giá).
        # [LEGACY — không còn dùng để phân loại chính, giữ lại để tương
        #  thích YAML cũ. Phân loại chính nay dựa vào head_occupancy_ratio
        #  bên dưới, chính xác hơn vì neo vào detect thật của PPE model.]
        self.declare_parameter('full_body_aspect_min', 1.30)

        # Tỉ lệ (chiều cao item helmet/no_helmet detect được) / (chiều cao
        # person box). Nếu đầu chiếm >= ngưỡng này của box → HEAD_ONLY
        # (thân bị che hoặc không nằm trong box). Nếu nhỏ hơn → FULL_BODY
        # (đầu chỉ là phần trên cùng của một box cao hơn nhiều).
        self.declare_parameter('head_occupancy_ratio_threshold', 0.30)

        # Với box HEAD_ONLY, chỉ suppress uncertain helmet khi box nhỏ hơn
        # ngưỡng này (riêng, nhỏ hơn ngưỡng full-body vì box đầu vốn đã nhỏ
        # hơn box toàn thân tự nhiên).
        self.declare_parameter(
            'uncertain_suppress_max_height_ratio_head_only', 0.12
        )

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

        self.min_person_height_ratio = float(
            self.get_parameter('min_person_height_ratio').value
        )
        self.min_person_aspect_ratio = float(
            self.get_parameter('min_person_aspect_ratio').value
        )
        self.head_clip_margin_ratio = float(
            self.get_parameter('head_clip_margin_ratio').value
        )
        self.uncertain_suppress_max_height_ratio = float(
            self.get_parameter('uncertain_suppress_max_height_ratio').value
        )
        self.full_body_aspect_min = float(
            self.get_parameter('full_body_aspect_min').value
        )
        self.head_occupancy_ratio_threshold = float(
            self.get_parameter('head_occupancy_ratio_threshold').value
        )
        self.uncertain_suppress_max_height_ratio_head_only = float(
            self.get_parameter(
                'uncertain_suppress_max_height_ratio_head_only'
            ).value
        )

        self.kpt_conf_threshold = float(
            self.get_parameter('kpt_conf_threshold').value
        )
        self.min_valid_body_kpts = int(
            self.get_parameter('min_valid_body_kpts').value
        )
        self.high_conf_box_threshold = float(
            self.get_parameter('high_conf_box_threshold').value
        )
        self.head_kpt_conf_threshold = float(
            self.get_parameter('head_kpt_conf_threshold').value
        )
        self.head_kpt_strong_conf = float(
            self.get_parameter('head_kpt_strong_conf').value
        )
        self.min_head_kpts_visible = int(
            self.get_parameter('min_head_kpts_visible').value
        )
        self.hip_kpt_conf_threshold = float(
            self.get_parameter('hip_kpt_conf_threshold').value
        )
        self.min_torso_kpts_for_full_body = int(
            self.get_parameter('min_torso_kpts_for_full_body').value
        )
        self.min_hip_kpts_for_full_body = int(
            self.get_parameter('min_hip_kpts_for_full_body').value
        )
        self.wrist_kpt_conf_threshold = float(
            self.get_parameter('wrist_kpt_conf_threshold').value
        )
        self.min_wrist_kpts_visible = int(
            self.get_parameter('min_wrist_kpts_visible').value
        )
        self.head_conf_smoothing_alpha = float(
            self.get_parameter('head_conf_smoothing_alpha').value
        )
        self.ppe_match_margin_ratio = float(
            self.get_parameter('ppe_match_margin_ratio').value
        )
        self.ppe_match_min_overlap = float(
            self.get_parameter('ppe_match_min_overlap').value
        )
        self.min_torso_angle_for_vest_check = float(
            self.get_parameter('min_torso_angle_for_vest_check').value
        )
        self.upright_box_aspect_min = float(
            self.get_parameter('upright_box_aspect_min').value
        )
        self.head_above_shoulder_ratio = float(
            self.get_parameter('head_above_shoulder_ratio').value
        )
        self.torso_vertical_ratio_min = float(
            self.get_parameter('torso_vertical_ratio_min').value
        )
        self.hands_cover_x_ratio = float(
            self.get_parameter('hands_cover_x_ratio').value
        )
        self.diag_logging = bool(
            self.get_parameter('diag_logging').value
        )

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

        pose_path = self._resolve_model(
            share_dir, self.get_parameter('pose_model_path').value
        )
        ppe_path = self._resolve_model(
            share_dir, self.get_parameter('ppe_model_path').value
        )

        self.get_logger().info(f'Loading pose YOLO: {pose_path}')
        self.pose_model = YOLO(pose_path)
        self.infer_device = infer_device

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

        # Ngưỡng conf cho găng tay — lưu trong node này thay vì truyền
        # vào PPEDetector, để KHÔNG phải sửa ppe_detector.py (file dùng
        # chung với person_tracker_node.py). Việc tìm 'gloves' item dùng
        # _scan_box_for_items tự chứa trong node này.
        self.gloves_ok_conf = float(
            self.get_parameter('ppe_gloves_ok_conf').value
        )

        self.enable_helmet_check = bool(
            self.get_parameter('enable_helmet_check').value
        )
        self.enable_vest_check = bool(
            self.get_parameter('enable_vest_check').value
        )
        self.enable_gloves_check = bool(
            self.get_parameter('enable_gloves_check').value
        )
        self.get_logger().info(
            f'PPE checks enabled: helmet={self.enable_helmet_check}, '
            f'vest={self.enable_vest_check}, gloves={self.enable_gloves_check}'
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

        # EMA smoothing cho head keypoint confidence theo slot (vị trí
        # trong danh sách person_entries, sort theo diện tích box giảm
        # dần) — giảm chập chờn báo/không báo khi cúi đầu. Reset khi
        # thoát NAV mode (trong _reset_state).
        self.head_conf_ema = {}

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
        self.head_conf_ema      = {}
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
        # 1. Detect persons bằng pose model — mỗi entry có box + keypoints
        person_entries = self._detect_persons(frame)

        # 2. Chạy PPE detector trên toàn ảnh một lần.
        # Dùng method nội bộ (chung model instance với ppe_detector, KHÔNG
        # thêm inference/RAM) thay vì ppe_detector.detect() — vì
        # ppe_detector._class_to_type() chỉ map helmet/vest, BỎ QUA gloves.
        # Method nội bộ tự map cả 3 class (helmet/vest/gloves) mà không
        # phải sửa ppe_detector.py (file dùng chung với person_tracker).
        try:
            ppe_items = self._detect_ppe_items(frame)
        except Exception as exc:
            self.get_logger().warn(f'PPE detect failed: {exc}')
            ppe_items = []

        # 3. Kiểm tra từng người
        # Phân loại HEAD_ONLY/FULL_BODY và suy ra "đầu có nhìn rõ không"
        # bằng chính keypoint pose — không còn đoán qua tỉ lệ box hay
        # suy luận gián tiếp qua PPE model (nguồn gốc các lỗi trước đây).
        #
        #   Đủ keypoint vai/hông nhìn thấy (>= min_torso_kpts_for_full_body)
        #     → FULL_BODY: check CẢ mũ và áo, độc lập với nhau.
        #   Không đủ (thân bị che/ngoài frame)
        #     → HEAD_ONLY: chỉ check mũ (toàn bộ box), KHÔNG check áo.
        #
        #   Đầu có nhìn rõ hay không = max confidence của keypoint vùng
        #   đầu (mũi/2 mắt/2 tai) so với head_kpt_conf_threshold. Đây là
        #   tín hiệu HÌNH HỌC trực tiếp (pose model thấy đầu hay không),
        #   khác hẳn cách cũ (suy luận qua việc PPE model có detect được
        #   helmet hay không — sai vì 2 nguyên nhân "không detect" khác
        # Nếu không có dữ liệu keypoint (model fallback, engine lỗi...)
        # → fallback an toàn: chỉ check theo geometry, không báo những
        # gì không chắc chắn.
        frame_h, frame_w = frame.shape[:2]
        person_status = []
        for entry in person_entries:
            box = entry['box']
            kpts_conf = entry['kpts_conf']

            # ──────────────────────────────────────────────────────────
            # NGUYÊN TẮC CỐT LÕI: chỉ báo THIẾU khi CHẮC CHẮN nhìn rõ
            # vùng cơ thể tương ứng MÀ không có PPE. Không chắc → không
            # báo (theo đúng yêu cầu "không chắc thì không cảnh báo").
            #
            # head_clearly_visible: đầu nhìn rõ (đủ keypoint đầu conf cao)
            #   → mới được phép báo THIẾU MŨ. Cúi/khuất đầu → không báo.
            #
            # torso_clearly_visible: thân nhìn rõ (CẢ 2 vai + ít nhất 1
            #   hông conf cao) → mới được phép báo THIẾU ÁO. Thân bị che
            #   (bảng/bàn/cúi sấp) → không báo. Yêu cầu cả vai LẪN hông
            #   đảm bảo toàn bộ vùng áo (giữa vai-hông) thực sự lộ ra,
            #   không chỉ một phần.
            # ──────────────────────────────────────────────────────────
            # MŨ: dùng ngưỡng đầu RIÊNG, cao hơn — chỉ "đầu thật sự rõ"
            # mới xét mũ. Cúi đầu còn lộ tí tai/mắt confidence trung bình
            # sẽ KHÔNG đủ, tránh báo thiếu nón oan khi cúi (ảnh 1).
            head_strong_count = self._kpt_visible_count(
                kpts_conf, HEAD_KPTS, self.head_kpt_strong_conf
            )

            # Kiểm tra đầu có CÚI XUỐNG không (độc lập với confidence) —
            # khi cúi/ngồi xổm gục đầu (ảnh 1), mặt vẫn còn hướng camera
            # nên keypoint đầu vẫn conf cao, nhưng đầu nằm THẤP bất thường
            # so với vai. So sánh vị trí Y của mũi với vai: nếu mũi không
            # ở RÕ RÀNG phía trên vai (đầu ngẩng) thì coi như đang cúi →
            # không đủ tin để xét mũ.
            head_not_bowed = self._is_head_upright(
                entry.get('kpts_xy'), kpts_conf
            )

            # Cần ÍT NHẤT 2 keypoint đầu mạnh VÀ đầu không cúi gục.
            head_clearly_visible = (
                head_strong_count >= self.min_head_kpts_visible and
                head_not_bowed
            )

            # THÂN/ÁO: vai cho biết phần trên thân, hông cho biết phần
            # dưới thân. Khi XOAY NGANG (ảnh 4) chỉ 1 vai lộ là bình
            # thường → chấp nhận 1 vai. Nhưng phải có THÊM hông để chắc
            # vùng giữa (áo) lộ ra.
            shoulder_visible_count = self._kpt_visible_count(
                kpts_conf, SHOULDER_KPTS, self.kpt_conf_threshold
            )
            hip_visible_count = self._kpt_visible_count(
                kpts_conf, HIP_KPTS, self.hip_kpt_conf_threshold
            )

            # "Thân thẳng đứng" — phân biệt ĐỨNG (dù xoay ngang/xoay lưng
            # về phía camera) với CÚI/NẰM. Dùng quan hệ DỌC giữa vai và
            # hông (robust với mọi hướng xoay), không dùng góc atan2.
            torso_vertical = self._is_torso_vertical(
                entry.get('kpts_xy'), kpts_conf
            )
            # Giữ torso_angle chỉ để LOG chẩn đoán (không dùng gate nữa).
            torso_angle = self._torso_angle_deg(
                entry.get('kpts_xy'), kpts_conf
            )
            angle_upright = torso_vertical

            hip_visible = hip_visible_count >= self.min_hip_kpts_for_full_body

            hands_cover = False  # mặc định (dùng cho cả nhánh no-pose + diag)
            if kpts_conf is not None:
                # ──────────────────────────────────────────────────────
                # CHIA LUỒNG xét THIẾU ÁO theo việc HÔNG có nhìn rõ không
                # (theo đề xuất phân luồng của người dùng):
                #
                # LUỒNG A — HÔNG NHÌN RÕ (hip_visible=True):
                #   Bao gồm: đứng đối diện, đứng nghiêng lộ hông, XOAY
                #   LƯNG (lưng lộ cả vai lẫn hông). Khi hông đã rõ ràng
                #   thì vùng áo (giữa vai-hông) chắc chắn lộ ra → TIN
                #   TƯỞNG, xét áo trực tiếp bằng YOLO. KHÔNG kiểm tra tay
                #   nữa — vì tay nằm cạnh thân khi đứng nghiêng/xoay lưng
                #   là BÌNH THƯỜNG, không phải bê vật. (Đây chính là chỗ
                #   trước đây bị gắt: hands_cover chặn nhầm các tư thế này.)
                #   Chỉ cần: vai rõ + hông rõ + thân thẳng đứng.
                #
                # LUỒNG B — HÔNG BỊ CHE (hip_visible=False):
                #   Hông không thấy → CÓ THỂ do (b1) vật thể che vùng
                #   thân/hông (ôm/bê vật), hoặc (b2) tư thế/góc khuất.
                #   Lúc này mới dùng _hands_covering_torso để phân biệt:
                #   nếu tay (khuỷu/cẳng tay) nằm chắn trong dải thân →
                #   đang bê vật che áo → KHÔNG xét (tránh báo oan). Nếu
                #   tay KHÔNG chắn nhưng hông vẫn không rõ → vùng áo
                #   không đủ tin cậy để khẳng định → cũng KHÔNG xét (theo
                #   nguyên tắc "không chắc thì không báo").
                #   → Tức LUỒNG B chỉ xét áo khi: vai rõ + thân thẳng +
                #     tay không chắn + (nhưng hông không rõ nên vẫn thận
                #     trọng — thực tế nhánh này hiếm khi báo, chủ yếu để
                #     KHÔNG báo oan khi bê vật).
                if hip_visible:
                    # LUỒNG A — HÔNG NHÌN RÕ: đối diện / nghiêng lộ hông /
                    # xoay lưng (lưng lộ cả vai lẫn hông). Hông rõ nghĩa là
                    # vùng áo (giữa vai-hông) chắc chắn lộ ra → TIN TƯỞNG,
                    # xét áo trực tiếp. KHÔNG kiểm tra tay (tay cạnh thân
                    # khi nghiêng/xoay lưng là bình thường).
                    torso_clearly_visible = (
                        shoulder_visible_count >= 1 and
                        angle_upright
                    )
                else:
                    # LUỒNG B — HÔNG BỊ CHE: theo yêu cầu, hông bị che
                    # (bởi vật đang bê/ôm trước bụng) → KHÔNG xét áo trong
                    # MỌI trường hợp → box giữ MÀU XANH (không báo thiếu).
                    #
                    # Lý do bỏ nhánh "tay không chắn → vẫn xét" trước đây:
                    # khi bê thùng/carton, người cầm 2 BÊN thùng nên cổ
                    # tay/khuỷu tay nằm ở RÌA thùng (mép ngoài thân), KHÔNG
                    # nằm giữa trục thân → _hands_covering_torso không bắt
                    # được dù tăng hands_cover_x_ratio. Vì vậy không dựa
                    # vào vị trí tay nữa: chỉ cần HÔNG BỊ CHE là đủ để
                    # không xét áo (đúng thực tế — đứng nghiêng/xoay lưng
                    # thì hông VẪN LỘ vào luồng A, hông chỉ khuất khi có
                    # VẬT che).
                    torso_clearly_visible = False
                    # Tính hands_cover chỉ để hiển thị log (không ảnh
                    # hưởng quyết định).
                    hands_cover = self._hands_covering_torso(
                        entry.get('kpts_xy'), kpts_conf
                    )
            else:
                # Không có pose → không đủ căn cứ → không báo (an toàn)
                head_clearly_visible = False
                torso_clearly_visible = False

            # GĂNG TAY: phần xét theo điểm cổ tay đã được BỎ theo yêu cầu.
            # hands_clearly_visible luôn False → không tự động báo thiếu
            # găng dựa trên cổ tay nữa. (enable_gloves_check trong YAML
            # điều khiển việc có xét găng hay không; hiện đang tắt.)
            hands_clearly_visible = False

            # Log chẩn đoán — bật bằng diag_logging=true để xem con số
            # thực tế và tinh chỉnh ngưỡng theo dữ liệu thật thay vì đoán.
            if self.diag_logging:
                angle_str = (
                    f'{torso_angle:.0f}' if torso_angle is not None else 'None'
                )
                flow = 'A(hip-visible)' if hip_visible else 'B(hip-hidden)'
                self.get_logger().info(
                    f'[DIAG] head_strong={head_strong_count} '
                    f'(need {self.min_head_kpts_visible}) '
                    f'head_not_bowed={head_not_bowed} '
                    f'shoulder={shoulder_visible_count} '
                    f'hip={hip_visible_count} (need {self.min_hip_kpts_for_full_body}) '
                    f'hip_visible={hip_visible} flow={flow} '
                    f'torso_angle={angle_str} torso_vertical={angle_upright} '
                    f'hands_cover={hands_cover} '
                    f'=> head_vis={head_clearly_visible} '
                    f'torso_vis={torso_clearly_visible}'
                )

            # Nới rộng nhẹ box CHỈ để tìm helmet/vest/gloves — box pose
            # model khít theo khung xương, PPE nằm sát mép có thể rơi ra
            # ngoài. Box GỐC vẫn dùng cho debug/cache/head_clipped.
            ppe_box = self._expand_box_for_ppe_match(box, frame_w, frame_h)

            try:
                status = self._check_ppe_with_visibility(
                    ppe_box, box, ppe_items, frame_h,
                    head_clearly_visible, torso_clearly_visible,
                    hands_clearly_visible
                )
            except Exception as exc:
                self.get_logger().warn(f'PPE check failed: {exc}')
                status = {'violation': False, 'missing_helmet': False,
                          'missing_vest': False, 'missing_gloves': False}
            person_status.append(status)

        # Cache lại để debug image dùng giữa các interval
        # (debug rendering chỉ cần box, không cần keypoints)
        self.last_person_boxes  = [entry['box'] for entry in person_entries]
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

        # 6. Publish alert hoặc NORMAL để reset latch trong esp32_alert_bridge
        if self.alarm_active:
            alert_type = self._determine_alert_type(person_status)
            self._publish_alert(stamp, alert_type, person_status)
        else:
            self._publish_normal(stamp)

        # 7. Debug image
        self._maybe_publish_debug(frame, stamp, frame_id)

    # ==========================================================
    # Person detection
    # ==========================================================
    def _detect_persons(self, frame):
        """
        Detect người trong ảnh bằng POSE model, trả về tối đa max_persons
        entry, mỗi entry là dict {'box', 'kpts_xy', 'kpts_conf'}.

        Dùng pose model thay vì plain detection model — vẫn 1 lần
        inference duy nhất cho bước này (không tăng tải), nhưng có thêm
        17 keypoint COCO mỗi người để:
          - Lọc chính xác tay/chân lẻ lọt vào khung (đếm keypoint thân
            nhìn thấy được, đáng tin hơn đoán qua tỉ lệ box).
          - Xác định đầu có thực sự nhìn rõ hay không (dùng trực tiếp
            confidence của keypoint vùng đầu — không suy luận gián tiếp
            qua PPE model như trước, vốn là nguồn gốc các lỗi cũ).

        Vẫn giữ filter hình học cơ bản (height/aspect) làm lớp lọc rẻ
        tiền đầu tiên trước khi xét tới keypoint, để loại sớm nhiễu rõ
        ràng mà không cần tính toán thêm.
        """
        frame_h, frame_w = frame.shape[:2]
        min_h = frame_h * self.min_person_height_ratio

        try:
            results = self.pose_model.predict(
                frame,
                classes=[0],          # class 0 = person
                conf=self.detect_conf,
                device=self.infer_device,
                verbose=False
            )
        except Exception as exc:
            self.get_logger().warn(f'Pose detect failed: {exc}')
            return []

        if results is None or len(results) == 0:
            return []

        result = results[0]
        boxes_obj = result.boxes
        if boxes_obj is None or boxes_obj.xyxy is None:
            return []

        xyxy = boxes_obj.xyxy.cpu().numpy()
        if len(xyxy) == 0:
            return []

        # Keypoints — có thể None nếu model/engine không xuất pose head
        has_kpts = (
            result.keypoints is not None and
            result.keypoints.xy is not None
        )
        if has_kpts:
            kpts_xy_all = result.keypoints.xy.cpu().numpy()
            kpts_conf_all = (
                result.keypoints.conf.cpu().numpy()
                if result.keypoints.conf is not None
                else None
            )
        else:
            kpts_xy_all = None
            kpts_conf_all = None

        # Box detection confidence (riêng biệt với keypoint confidence) —
        # dùng làm tín hiệu "ưu tiên tin tưởng" khi cao, không cần thêm
        # điều kiện keypoint (bù trừ trường hợp người bị che/góc nghiêng
        # khiến TẤT CẢ keypoint confidence thấp dù box detect rất chắc).
        box_conf_all = (
            boxes_obj.conf.cpu().numpy() if boxes_obj.conf is not None else None
        )

        valid = []
        for i, box in enumerate(xyxy):
            x1, y1, x2, y2 = box
            box_w = max(1.0, x2 - x1)
            box_h = max(1.0, y2 - y1)

            # Filter hình học cơ bản (rẻ tiền, loại nhiễu rõ ràng trước)
            if box_h < min_h:
                continue
            if box_h / box_w < self.min_person_aspect_ratio:
                continue

            kpts_conf = (
                kpts_conf_all[i] if kpts_conf_all is not None
                and i < len(kpts_conf_all) else None
            )
            box_conf = (
                float(box_conf_all[i]) if box_conf_all is not None
                and i < len(box_conf_all) else 1.0
            )

            # Filter bằng pose: xác nhận đây THỰC SỰ là người, không
            # phải tay/chân lẻ. CHỈ áp dụng khi box_conf còn THẤP/biên
            # giới (chưa đủ tự tin từ chính box detector) — nếu box_conf
            # đã cao (model rất chắc đây là 1 người, dựa trên silhouette
            # tổng thể) thì TIN TRỰC TIẾP, không đòi thêm keypoint, vì
            # góc nghiêng/che khuất có thể khiến MỌI keypoint (kể cả đầu)
            # đều confidence thấp dù box detect rất đúng — đây chính là
            # nguyên nhân case "che thân lộ đầu" bị mất detect trước đó.
            if box_conf < self.high_conf_box_threshold and kpts_conf is not None:
                valid_kpt_count = sum(
                    1 for idx in BODY_VALIDATION_KPTS
                    if idx < len(kpts_conf)
                    and float(kpts_conf[idx]) >= self.kpt_conf_threshold
                )
                if valid_kpt_count < self.min_valid_body_kpts:
                    self.get_logger().debug(
                        f'Box rejected by pose: box_conf={box_conf:.2f} '
                        f'(< {self.high_conf_box_threshold}), only '
                        f'{valid_kpt_count} body keypoints visible — '
                        f'likely a limb, not a full person'
                    )
                    continue

            valid.append({
                'box': box,
                'kpts_xy': (
                    kpts_xy_all[i] if kpts_xy_all is not None
                    and i < len(kpts_xy_all) else None
                ),
                'kpts_conf': kpts_conf,
            })

        if not valid:
            return []

        # Sort theo diện tích box giảm dần (người gần camera trước)
        def _area(entry):
            x1, y1, x2, y2 = entry['box']
            return (x2 - x1) * (y2 - y1)

        valid.sort(key=_area, reverse=True)

        return valid[:self.max_persons]

    @staticmethod
    def _kpt_max_conf(kpts_conf, indices):
        """Confidence cao nhất trong nhóm keypoint chỉ định. 0.0 nếu
        không có dữ liệu keypoint (model fallback an toàn)."""
        if kpts_conf is None:
            return 0.0
        best = 0.0
        for idx in indices:
            if idx < len(kpts_conf):
                best = max(best, float(kpts_conf[idx]))
        return best

    @staticmethod
    def _kpt_visible_count(kpts_conf, indices, threshold):
        """Số keypoint trong nhóm có conf >= threshold. 0 nếu không có
        dữ liệu keypoint."""
        if kpts_conf is None:
            return 0
        return sum(
            1 for idx in indices
            if idx < len(kpts_conf) and float(kpts_conf[idx]) >= threshold
        )

    def _is_head_upright(self, kpts_xy, kpts_conf):
        """
        Đầu có NGẨNG (không cúi gục) hay không, dựa vào vị trí dọc của
        mũi so với vai.

        Khi đứng/ngồi bình thường: mũi ở RÕ RÀNG phía trên đường vai
        (nose_y < shoulder_y một khoảng đáng kể). Khi cúi gục đầu (ngồi
        xổm úp mặt như ảnh 1): mũi tụt xuống ngang hoặc thấp hơn vai
        dù mặt vẫn còn hướng camera (keypoint vẫn conf cao) → không đủ
        tin để khẳng định "đầu nhìn rõ để xét mũ".

        Cần mũi + ít nhất 1 vai đủ conf. Thiếu dữ liệu → trả True (không
        chặn — để các điều kiện khác như head_strong_count quyết định,
        tránh vô tình bỏ qua người đứng thẳng mà mũi bị thiếu).

        Ngưỡng: mũi phải cao hơn vai ít nhất head_above_shoulder_ratio
        lần chiều cao box (mặc định nhỏ, chỉ loại trường hợp gục hẳn).
        """
        if kpts_xy is None or kpts_conf is None:
            return True

        if (KPT_NOSE >= len(kpts_conf) or
                float(kpts_conf[KPT_NOSE]) < self.head_kpt_conf_threshold):
            return True  # không có mũi tin cậy → không chặn

        nose_y = float(kpts_xy[KPT_NOSE][1])

        shoulder_ys = []
        for idx in SHOULDER_KPTS:
            if (idx < len(kpts_conf) and
                    float(kpts_conf[idx]) >= self.kpt_conf_threshold):
                shoulder_ys.append(float(kpts_xy[idx][1]))

        if not shoulder_ys:
            return True  # không có vai tin cậy → không chặn

        shoulder_y = sum(shoulder_ys) / len(shoulder_ys)

        # Khoảng cách dọc vai→mũi, chuẩn hóa theo khoảng vai (để không
        # phụ thuộc khoảng cách camera). Dùng |shoulder span| làm đơn vị.
        shoulder_xs = []
        for idx in SHOULDER_KPTS:
            if (idx < len(kpts_conf) and
                    float(kpts_conf[idx]) >= self.kpt_conf_threshold):
                shoulder_xs.append(float(kpts_xy[idx][0]))

        if len(shoulder_xs) >= 2:
            scale = max(1.0, abs(shoulder_xs[0] - shoulder_xs[1]))
        else:
            scale = max(1.0, abs(nose_y - shoulder_y) + 1.0)

        # mũi phía trên vai → (shoulder_y - nose_y) dương.
        above_ratio = (shoulder_y - nose_y) / scale

        return above_ratio >= self.head_above_shoulder_ratio

    def _torso_angle_deg(self, kpts_xy, kpts_conf):
        """
        Góc nghiêng thân so với phương NGANG, tính từ trung điểm vai và
        trung điểm hông — mirror đúng công thức
        FallDetector.torso_angle_deg_from_horizontal():

            angle = atan2(|hip_y - shoulder_y|, |hip_x - shoulder_x|)

        Quy ước (giống fall_detector):
          - ~90°  : thân THẲNG ĐỨNG (vai thẳng trên hông)
          - nhỏ dần → nghiêng/cúi (vai và hông lệch nhau theo phương ngang)
          - ~0°   : thân NẰM NGANG

        Trả về None nếu không đủ keypoint vai/hông tin cậy để tính.
        Cần ÍT NHẤT 1 vai và 1 hông có conf đủ cao (theo kpt_conf_threshold
        cho vai, hip_kpt_conf_threshold cho hông — hông khó hơn nên ngưỡng
        cao hơn để tránh dùng hông nội suy).
        """
        if kpts_xy is None or kpts_conf is None:
            return None

        def _avg_point(indices, conf_th):
            pts = []
            for idx in indices:
                if (idx < len(kpts_conf) and idx < len(kpts_xy)
                        and float(kpts_conf[idx]) >= conf_th):
                    pts.append((float(kpts_xy[idx][0]), float(kpts_xy[idx][1])))
            if not pts:
                return None
            n = len(pts)
            return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)

        shoulder_mid = _avg_point(SHOULDER_KPTS, self.kpt_conf_threshold)
        hip_mid = _avg_point(HIP_KPTS, self.hip_kpt_conf_threshold)

        if shoulder_mid is None or hip_mid is None:
            return None

        dx = abs(hip_mid[0] - shoulder_mid[0])
        dy = abs(hip_mid[1] - shoulder_mid[1])

        return math.degrees(math.atan2(dy, dx + 1e-6))

    def _is_torso_vertical(self, kpts_xy, kpts_conf):
        """
        Thân có ĐỨNG THẲNG ĐỨNG không — đo bằng quan hệ DỌC giữa vai và
        hông, ROBUST với xoay ngang/xoay lưng về phía camera (side/back
        view). Đây là thay thế cho _torso_angle_deg (atan2) vốn bị lệch
        khi người xoay hướng.

        Khác biệt then chốt:
          - atan2(|Δy|,|Δx|): độ lệch NGANG vai-hông làm góc giảm, nên
            xoay ngang bị coi nhầm là cúi.
          - Ở đây đo TRỰC TIẾP: người đứng thì vai Ở TRÊN hông một khoảng
            DỌC đáng kể so với bề ngang thân, BẤT KỂ hướng xoay.

        Công thức:
          vertical_gap   = hip_y - shoulder_y   (dương khi vai trên hông)
          horizontal_gap = |hip_x - shoulder_x|
        Đứng thẳng: vertical_gap > 0 VÀ
                    vertical_gap >= horizontal_gap * torso_vertical_ratio_min
        Cúi/nằm: vertical_gap nhỏ hoặc âm → False.

        Cần trung điểm vai + hông tin cậy. Thiếu → False (an toàn, không
        xét áo khi không đủ căn cứ).
        """
        if kpts_xy is None or kpts_conf is None:
            return False

        def _avg_point(indices, conf_th):
            pts = []
            for idx in indices:
                if (idx < len(kpts_conf) and idx < len(kpts_xy)
                        and float(kpts_conf[idx]) >= conf_th):
                    pts.append((float(kpts_xy[idx][0]), float(kpts_xy[idx][1])))
            if not pts:
                return None
            n = len(pts)
            return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)

        shoulder_mid = _avg_point(SHOULDER_KPTS, self.kpt_conf_threshold)
        # Dùng ngưỡng THƯỜNG (không phải hip_kpt_conf_threshold cao) cho
        # hông ở đây — _is_torso_vertical chỉ cần vị trí hông ĐẠI KHÁI để
        # xác định thân có thẳng đứng không, KHÔNG cần hông "chắc chắn lộ
        # ra" (việc hông có thật sự lộ để xét áo đã do hip_visible ở
        # ngoài quyết định). Nếu dùng ngưỡng cao, luồng B (hông khuất
        # nhẹ) sẽ luôn trả False làm không xét được áo dù thân thẳng rõ.
        hip_mid = _avg_point(HIP_KPTS, self.kpt_conf_threshold)

        if shoulder_mid is None or hip_mid is None:
            return False

        vertical_gap = hip_mid[1] - shoulder_mid[1]   # dương: vai trên hông
        horizontal_gap = abs(hip_mid[0] - shoulder_mid[0])

        if vertical_gap <= 0:
            return False   # vai không ở trên hông → cúi/nằm/bất thường

        return vertical_gap >= horizontal_gap * self.torso_vertical_ratio_min

    def _hands_covering_torso(self, kpts_xy, kpts_conf):
        """
        Phát hiện tư thế TAY ĐƯA RA TRƯỚC CHE THÂN (ôm/bê vật trước
        bụng/ngực) — tín hiệu HÌNH HỌC độc lập với confidence, để bổ
        sung cho việc hông hay bị pose NỘI SUY conf cao xuyên vật.

        Nguyên lý: khi ôm vật trước thân, cổ tay và/hoặc khuỷu tay bị
        kéo vào GIỮA thân theo chiều dọc — nằm trong khoảng từ vai đến
        hông (vùng áo). Bình thường (tay buông thẳng) cổ tay nằm THẤP
        hơn hông. Nếu có >=1 cổ tay hoặc khuỷu tay nằm trong dải dọc
        [vai, hông] VÀ gần trục giữa thân theo chiều ngang → nhiều khả
        năng đang che vùng áo → trả True (để bỏ xét áo).

        Cần đủ vai + hông để xác định dải thân. Thiếu → trả False
        (không kết luận che, để điều kiện khác quyết định).
        """
        if kpts_xy is None or kpts_conf is None:
            return False

        def _pt(idx, conf_th):
            if (idx < len(kpts_conf) and idx < len(kpts_xy)
                    and float(kpts_conf[idx]) >= conf_th):
                return (float(kpts_xy[idx][0]), float(kpts_xy[idx][1]))
            return None

        ls = _pt(KPT_LEFT_SHOULDER, self.kpt_conf_threshold)
        rs = _pt(KPT_RIGHT_SHOULDER, self.kpt_conf_threshold)
        lh = _pt(KPT_LEFT_HIP, self.kpt_conf_threshold)
        rh = _pt(KPT_RIGHT_HIP, self.kpt_conf_threshold)

        shoulders = [p for p in (ls, rs) if p is not None]
        hips = [p for p in (lh, rh) if p is not None]
        if not shoulders or not hips:
            return False

        shoulder_y = sum(p[1] for p in shoulders) / len(shoulders)
        hip_y = sum(p[1] for p in hips) / len(hips)

        top = min(shoulder_y, hip_y)
        bot = max(shoulder_y, hip_y)
        band = max(1.0, bot - top)
        top -= band * 0.10
        bot += band * 0.10

        cx_pts = shoulders + hips
        center_x = sum(p[0] for p in cx_pts) / len(cx_pts)
        if len(shoulders) >= 2:
            body_w = abs(shoulders[0][0] - shoulders[1][0])
        else:
            body_w = abs(shoulder_y - hip_y)
        half_w = max(1.0, body_w) * self.hands_cover_x_ratio

        limb_indices = (
            KPT_LEFT_WRIST, KPT_RIGHT_WRIST,
            KPT_LEFT_ELBOW, KPT_RIGHT_ELBOW,
        )
        for idx in limb_indices:
            p = _pt(idx, self.kpt_conf_threshold)
            if p is None:
                continue
            in_band = top <= p[1] <= bot
            near_center = abs(p[0] - center_x) <= half_w
            if in_band and near_center:
                return True

        return False

    # ==========================================================
    # Head-only PPE check (thân bị che, chỉ lộ đầu)
    # ==========================================================
    @staticmethod
    def _center_inside_local(small_box, big_box):
        """
        Bản local, độc lập với PPEDetector._center_inside — tránh sửa
        ppe_detector.py (file dùng chung với person_tracker_node.py).
        """
        sx1, sy1, sx2, sy2 = map(int, small_box)
        bx1, by1, bx2, by2 = map(int, big_box)
        cx = (sx1 + sx2) // 2
        cy = (sy1 + sy2) // 2
        return bx1 <= cx <= bx2 and by1 <= cy <= by2

    @staticmethod
    def _overlap_ratio_local(item_box, person_box):
        """
        Tỉ lệ diện tích item_box GIAO với person_box trên tổng diện tích
        item_box. Trả về 0.0..1.0.

        Dùng thay cho _center_inside khi tìm vest/helmet: khi người
        NGHIÊNG hoặc CẦM VẬT trước ngực, box của vest item (từ PPE model)
        có thể lệch khiến TÂM ĐIỂM rơi ra ngoài person_box dù áo vẫn
        đang được mặc và phần lớn vest vẫn nằm trong vùng người. Xét
        overlap thay vì tâm điểm giúp không bỏ sót các trường hợp này
        (nguyên nhân báo "thiếu áo" oan khi nghiêng/cầm vật).
        """
        ix1, iy1, ix2, iy2 = map(float, item_box)
        px1, py1, px2, py2 = map(float, person_box)

        inter_x1 = max(ix1, px1)
        inter_y1 = max(iy1, py1)
        inter_x2 = min(ix2, px2)
        inter_y2 = min(iy2, py2)

        inter_w = max(0.0, inter_x2 - inter_x1)
        inter_h = max(0.0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        item_area = max(1.0, (ix2 - ix1) * (iy2 - iy1))
        return inter_area / item_area

    def _expand_box_for_ppe_match(self, box, frame_w, frame_h):
        """
        Nới rộng nhẹ person_box trước khi tìm helmet/vest (theo
        ppe_match_margin_ratio). Box từ pose model thường "khít" theo
        khung xương hơn box từ model detection thường, khiến mũ (nhô
        cao hơn đỉnh đầu/keypoint mũi) hoặc áo (rộng hơn vai 1 chút) có
        tâm điểm rơi RA NGOÀI box dù người đó đang mặc đầy đủ.

        Chỉ dùng để tìm PPE item — box GỐC (không nới) vẫn dùng cho mọi
        việc khác (debug render, cache, head_clipped check) để không
        ảnh hưởng các tính toán hình học khác.
        """
        x1, y1, x2, y2 = box
        bw = max(1.0, x2 - x1)
        bh = max(1.0, y2 - y1)

        pad_x = bw * self.ppe_match_margin_ratio
        pad_y = bh * self.ppe_match_margin_ratio

        nx1 = max(0.0, x1 - pad_x)
        ny1 = max(0.0, y1 - pad_y)
        nx2 = min(float(frame_w - 1), x2 + pad_x)
        ny2 = min(float(frame_h - 1), y2 + pad_y)

        return (nx1, ny1, nx2, ny2)

    @staticmethod
    def _ppe_class_to_type(raw_name):
        """
        Map tên class thô của model PPE -> loại item nội bộ.

        Bản mở rộng của PPEDetector._class_to_type() có THÊM 'gloves'.
        Đặt tại đây (không sửa ppe_detector.py — file dùng chung). Nhận
        diện linh hoạt nhiều cách đặt tên (glove/gloves/hand-glove...),
        đồng thời phân biệt biến thể "no-..." (no_helmet/no_vest/
        no_gloves) nếu model có train.
        """
        name = str(raw_name).lower().replace("_", "-").replace(" ", "-")

        if "helmet" in name or "hardhat" in name or "hard-hat" in name:
            kw_pos = min(
                name.find("helmet") if "helmet" in name else len(name),
                name.find("hardhat") if "hardhat" in name else len(name),
                name.find("hard-hat") if "hard-hat" in name else len(name),
            )
            no_pos = name.find("no")
            if no_pos != -1 and no_pos < kw_pos:
                return "no_helmet"
            return "helmet"

        if "vest" in name:
            kw_pos = name.find("vest")
            no_pos = name.find("no")
            if no_pos != -1 and no_pos < kw_pos:
                return "no_vest"
            return "vest"

        if "glove" in name:
            kw_pos = name.find("glove")
            no_pos = name.find("no")
            if no_pos != -1 and no_pos < kw_pos:
                return "no_gloves"
            return "gloves"

        return None

    def _detect_ppe_items(self, frame):
        """
        Chạy model PPE trên ảnh, trả về list item {box, class_name, conf}.

        Tương đương PPEDetector.detect() nhưng dùng _ppe_class_to_type()
        ở trên (có thêm gloves). Dùng CHUNG model instance đã load trong
        self.ppe_detector.model — KHÔNG load model mới, KHÔNG thêm RAM,
        thay thế (không thêm) lần inference detect() cũ.
        """
        results = self.ppe_detector.model.predict(
            frame,
            imgsz=self.ppe_detector.imgsz,
            conf=self.ppe_detector.conf,
            iou=self.ppe_detector.iou,
            device=self.ppe_detector.infer_device,
            verbose=False
        )

        ppe_items = []
        if results is None or len(results) == 0:
            return ppe_items

        boxes = results[0].boxes
        names = results[0].names
        if boxes is None:
            return ppe_items

        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cls_id = int(box.cls[0])
            score = float(box.conf[0])

            if isinstance(names, dict):
                raw_name = names.get(cls_id, str(cls_id))
            else:
                raw_name = names[cls_id]

            item_type = self._ppe_class_to_type(raw_name)
            if item_type is None:
                continue

            ppe_items.append({
                "box": (x1, y1, x2, y2),
                "class_name": item_type,
                "raw_name": raw_name,
                "conf": score,
            })

        return ppe_items

    def _scan_box_for_items(self, person_box, ppe_items, positive_class, negative_class):
        """
        Quét TOÀN BỘ person_box tìm item thuộc (positive_class, negative_class)
        — KHÔNG giới hạn theo vị trí con (top X%, giữa Y%...).

        Lý do bỏ fixed-ratio sub-region: các vùng tỉ lệ cố định (head ở
        trên, áo ở giữa) giả định người đứng thẳng. Khi người NGỒI, CÚI
        NGƯỜI, hoặc với tay, vị trí thật của đầu/áo trong box bị lệch khỏi
        giả định đó rất nhiều → fixed-ratio dễ báo sai (vd cúi người làm
        áo thật sự nằm ở vùng trên nhưng torso_region tính ra lại nằm ở
        giữa/dưới → không match được áo dù đang mặc).

        Quét toàn bộ box đáng tin cậy hơn vì chỉ phụ thuộc class detect
        được (helmet/no_helmet riêng biệt với vest/no_vest do model PPE
        tự phân loại), không phụ thuộc giả định tư thế đứng thẳng.

        Trả về (positive_score, negative_score), mỗi giá trị là conf cao
        nhất tìm được (0.0 nếu không thấy item nào loại đó).
        """
        pos_score = 0.0
        neg_score = 0.0

        for item in ppe_items:
            item_type = item['class_name']
            if item_type not in (positive_class, negative_class):
                continue
            # Dùng overlap thay vì tâm-điểm-bên-trong: item lệch do
            # nghiêng/cầm vật vẫn match nếu giao đủ lớn với person box.
            if self._overlap_ratio_local(item['box'], person_box) < self.ppe_match_min_overlap:
                continue

            score = float(item['conf'])
            if item_type == positive_class:
                pos_score = max(pos_score, score)
            else:
                neg_score = max(neg_score, score)

        return pos_score, neg_score

    def _check_ppe_with_visibility(
        self, ppe_box, orig_box, ppe_items, frame_h,
        head_clearly_visible, torso_clearly_visible,
        hands_clearly_visible
    ):
        """
        Check PPE theo nguyên tắc: CHỈ báo THIẾU khi CHẮC CHẮN nhìn rõ
        vùng cơ thể tương ứng mà không tìm thấy PPE. Không chắc -> không
        báo (theo yeu cau "khong chac thi khong canh bao").

        Tham số:
          ppe_box  : box đã nới rộng, dùng để TÌM helmet/vest/gloves item.
          orig_box : box gốc, dùng cho head_clipped check (hình học).
          head_clearly_visible  : pose xác nhận đầu nhìn rõ -> được phép
                                   xét THIẾU MŨ.
          torso_clearly_visible : pose xác nhận thân (vai+hông) nhìn rõ
                                   -> được phép xét THIẾU ÁO.
          hands_clearly_visible : pose xác nhận bàn tay (cổ tay) nhìn rõ
                                   -> được phép xét THIẾU GĂNG TAY.

        Logic chung cho cả 3 loại PPE:
          - Tìm thấy item đủ conf -> coi như ĐANG MẶC (luôn đúng dù vùng
            cơ thể rõ hay không: thấy item nghĩa là có).
          - Không thấy item:
              + vùng cơ thể tương ứng nhìn rõ -> THIẾU (chắc chắn).
              + vùng không rõ -> KHÔNG báo (không chắc).

        Model ppe_s.engine train 3 class: helmet, vest, gloves.
        """
        x1, y1, x2, y2 = map(int, orig_box)
        head_clipped = y1 < frame_h * self.head_clip_margin_ratio

        # ── Mũ ──────────────────────────────────────────────────────────
        if not self.enable_helmet_check:
            # Tắt check mũ → không bao giờ báo thiếu mũ
            missing_helmet = False
            helmet_score = 0.0
        else:
            helmet_score, _ = self._scan_box_for_items(
                ppe_box, ppe_items, 'helmet', 'no_helmet'
            )
            helmet_found = helmet_score >= self.ppe_detector.helmet_ok_conf

            if helmet_found:
                missing_helmet = False      # thấy mũ -> chắc chắn có mũ
            elif head_clearly_visible and not head_clipped:
                missing_helmet = True       # nhìn rõ đầu, không mũ -> thiếu
            else:
                missing_helmet = False      # không chắc -> không báo

        # ── Áo ──────────────────────────────────────────────────────────
        if not self.enable_vest_check:
            # Tắt check áo → không bao giờ báo thiếu áo
            missing_vest = False
            vest_score = 0.0
        else:
            vest_score, _ = self._scan_box_for_items(
                ppe_box, ppe_items, 'vest', 'no_vest'
            )
            vest_found = vest_score >= self.ppe_detector.vest_ok_conf

            if vest_found:
                missing_vest = False        # thấy áo -> chắc chắn có áo
            elif torso_clearly_visible:
                missing_vest = True         # nhìn rõ thân, không áo -> thiếu
            else:
                missing_vest = False        # không chắc -> không báo

        # ── Găng tay ────────────────────────────────────────────────────
        if not self.enable_gloves_check:
            # Tắt check găng → không bao giờ báo thiếu găng
            missing_gloves = False
            gloves_score = 0.0
        else:
            gloves_score, _ = self._scan_box_for_items(
                ppe_box, ppe_items, 'gloves', 'no_gloves'
            )
            gloves_found = gloves_score >= self.gloves_ok_conf

            if gloves_found:
                missing_gloves = False      # thấy găng -> chắc chắn có găng
            elif hands_clearly_visible:
                missing_gloves = True       # nhìn rõ tay, không găng -> thiếu
            else:
                missing_gloves = False      # không chắc -> không báo

        return {
            'helmet_ok': not missing_helmet,
            'vest_ok': not missing_vest,
            'gloves_ok': not missing_gloves,
            'missing_helmet': missing_helmet,
            'missing_vest': missing_vest,
            'missing_gloves': missing_gloves,
            'violation': missing_helmet or missing_vest or missing_gloves,
            'helmet_score': helmet_score,
            'vest_score': vest_score,
            'gloves_score': gloves_score,
            'head_visible': head_clearly_visible,
            'torso_visible': torso_clearly_visible,
            'hands_visible': hands_clearly_visible,
        }

    def _determine_alert_type(self, person_status):
        """
        Xác định alert_type dựa trên tổng hợp vi phạm của mọi người.

        Nếu thiếu NHIỀU loại (>=2) hoặc thiếu găng → dùng MISSING_PPE
        chung (ESP32 hiển thị cảnh báo PPE tổng hợp, vì màn hình hiện
        chỉ phân biệt helmet/vest qua các mã cũ; gloves gộp vào PPE
        chung để không phải đổi firmware ESP32). Thiếu đúng 1 loại
        helmet hoặc vest → giữ mã riêng để tương thích logic cũ.
        """
        any_no_helmet = any(s.get('missing_helmet', False) for s in person_status)
        any_no_vest   = any(s.get('missing_vest',   False) for s in person_status)
        any_no_gloves = any(s.get('missing_gloves', False) for s in person_status)

        missing_kinds = sum([any_no_helmet, any_no_vest, any_no_gloves])

        # Thiếu nhiều loại, hoặc có thiếu găng → cảnh báo PPE tổng hợp
        if missing_kinds >= 2 or any_no_gloves:
            return 'MISSING_PPE'
        if any_no_helmet:
            return 'MISSING_HELMET'
        if any_no_vest:
            return 'MISSING_VEST'
        return 'MISSING_PPE'

    def _publish_normal(self, stamp):
        """Publish NORMAL để reset latch trong esp32_alert_bridge."""
        msg = AiAlert()
        msg.stamp      = stamp
        msg.alert_type = 'NORMAL'
        msg.confidence = 0.0
        msg.message    = 'PPE OK'
        msg.active     = False
        msg.robot_pose = PoseStamped()
        msg.robot_pose.header.stamp    = stamp
        msg.robot_pose.header.frame_id = 'map'
        msg.image_path = ''
        self.alert_pub.publish(msg)

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

            # Chỉ tô MÀU box theo trạng thái, KHÔNG vẽ nhãn text trên
            # đầu box người (theo yêu cầu bỏ nhãn "THIEU N+A").
            #   xám  = chưa xét xong
            #   đỏ   = có vi phạm (thiếu bảo hộ)
            #   xanh = đủ bảo hộ / không có vi phạm
            if status is None:
                color = (128, 128, 128)
            elif status.get('violation', False):
                color = (0, 0, 255)
            else:
                color = (0, 255, 0)

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

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