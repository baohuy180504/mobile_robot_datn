from ultralytics import YOLO
from amr_ai.core import config as cfg


def get_cfg(name, default):
    return getattr(cfg, name, default)


class PPEDetector:
    def __init__(
        self,
        model_path=None,
        infer_device=None,
        imgsz=None,
        conf=None,
        iou=None,
        helmet_ok_conf=None,
        vest_ok_conf=None,
    ):
        self.model_path = model_path or get_cfg("PPE_MODEL_PATH", "models/ppe_s.engine")
        self.infer_device = infer_device if infer_device is not None else get_cfg("PPE_INFER_DEVICE", 0)

        self.imgsz = imgsz if imgsz is not None else get_cfg("PPE_IMGSZ", 512)
        self.conf = conf if conf is not None else get_cfg("PPE_CONF", 0.12)
        self.iou = iou if iou is not None else get_cfg("PPE_IOU", 0.50)

        self.helmet_ok_conf = helmet_ok_conf if helmet_ok_conf is not None else get_cfg("PPE_HELMET_OK_CONF", 0.18)
        self.vest_ok_conf = vest_ok_conf if vest_ok_conf is not None else get_cfg("PPE_VEST_OK_CONF", 0.45)

        self.model = YOLO(self.model_path, task="detect")

        print("[PPE] model path:", self.model_path)
        print("[PPE] imgsz:", self.imgsz)
        print("[PPE] conf:", self.conf)
        print("[PPE] names:", self.model.names)

    def _normalize_name(self, raw_name):
        return str(raw_name).lower().replace("_", "-").replace(" ", "-")

    def _class_to_type(self, raw_name):
        name = self._normalize_name(raw_name)

        if "no-helmet" in name or "nohelmet" in name:
            return "no_helmet"

        if "helmet" in name or "hardhat" in name or "hard-hat" in name:
            return "helmet"

        if "no-vest" in name or "novest" in name:
            return "no_vest"

        if "vest" in name:
            return "vest"

        return None

    def _center_inside(self, small_box, big_box):
        sx1, sy1, sx2, sy2 = map(int, small_box)
        bx1, by1, bx2, by2 = map(int, big_box)

        cx = (sx1 + sx2) // 2
        cy = (sy1 + sy2) // 2

        return bx1 <= cx <= bx2 and by1 <= cy <= by2

    def _inter_area_ratio(self, small_box, big_box):
        sx1, sy1, sx2, sy2 = map(int, small_box)
        bx1, by1, bx2, by2 = map(int, big_box)

        ix1 = max(sx1, bx1)
        iy1 = max(sy1, by1)
        ix2 = min(sx2, bx2)
        iy2 = min(sy2, by2)

        iw = max(0, ix2 - ix1)
        ih = max(0, iy2 - iy1)

        inter = iw * ih
        small_area = max(1, (sx2 - sx1) * (sy2 - sy1))

        return inter / float(small_area)

    def detect(self, frame):
        """
        Chạy model PPE trên ảnh đầu vào.
        Trả về danh sách item: Helmet, Vest, No-Helmet, No-Vest nếu model có.
        """
        results = self.model.predict(
            frame,
            imgsz=self.imgsz,
            conf=self.conf,
            iou=self.iou,
            device=self.infer_device,
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

            item_type = self._class_to_type(raw_name)

            if item_type is None:
                continue

            ppe_items.append({
                "box": (x1, y1, x2, y2),
                "class_name": item_type,
                "raw_name": raw_name,
                "conf": score
            })

        return ppe_items

    def detect_target_only(self, frame, person_box):
        """
        Chỉ crop vùng người vận hành rồi check PPE trong vùng đó.
        Không check người xung quanh.
        """
        pad_ratio = get_cfg("PPE_PAD_RATIO", 0.08)

        frame_h, frame_w = frame.shape[:2]
        px1, py1, px2, py2 = map(int, person_box)

        person_w = max(1, px2 - px1)
        person_h = max(1, py2 - py1)

        pad_x = int(person_w * pad_ratio)
        pad_y = int(person_h * pad_ratio)

        cx1 = max(0, px1 - pad_x)
        cy1 = max(0, py1 - pad_y)
        cx2 = min(frame_w - 1, px2 + pad_x)
        cy2 = min(frame_h - 1, py2 + pad_y)

        if cx2 <= cx1 or cy2 <= cy1:
            return []

        crop = frame[cy1:cy2, cx1:cx2]
        crop_items = self.detect(crop)

        mapped_items = []

        for item in crop_items:
            x1, y1, x2, y2 = item["box"]

            item["box"] = (
                x1 + cx1,
                y1 + cy1,
                x2 + cx1,
                y2 + cy1
            )

            mapped_items.append(item)

        return mapped_items

    def check_person_ppe(self, person_box, ppe_items):
        px1, py1, px2, py2 = map(int, person_box)

        person_w = max(1, px2 - px1)
        person_h = max(1, py2 - py1)
        person_area = person_w * person_h

        head_x_margin = get_cfg("PPE_HEAD_X_MARGIN_RATIO", 0.10)
        head_y2_ratio = get_cfg("PPE_HEAD_Y2_RATIO", 0.42)

        torso_x_margin = get_cfg("PPE_TORSO_X_MARGIN_RATIO", 0.10)
        torso_y1_ratio = get_cfg("PPE_TORSO_Y1_RATIO", 0.22)
        torso_y2_ratio = get_cfg("PPE_TORSO_Y2_RATIO", 0.90)

        head_region = (
            px1 + int(person_w * head_x_margin),
            py1,
            px2 - int(person_w * head_x_margin),
            py1 + int(person_h * head_y2_ratio)
        )

        torso_region = (
            px1 + int(person_w * torso_x_margin),
            py1 + int(person_h * torso_y1_ratio),
            px2 - int(person_w * torso_x_margin),
            py1 + int(person_h * torso_y2_ratio)
        )

        helmet_score = 0.0
        no_helmet_score = 0.0
        vest_score = 0.0
        no_vest_score = 0.0

        vest_inter_ratio = get_cfg("PPE_VEST_INTER_RATIO", 0.45)
        no_vest_inter_ratio = get_cfg("PPE_NO_VEST_INTER_RATIO", 0.35)

        vest_min_area_ratio = get_cfg("PPE_VEST_MIN_AREA_RATIO", 0.035)
        vest_min_h_ratio = get_cfg("PPE_VEST_MIN_H_RATIO", 0.16)
        vest_min_w_ratio = get_cfg("PPE_VEST_MIN_W_RATIO", 0.20)

        for item in ppe_items:
            item_box = item["box"]
            item_type = item["class_name"]
            score = float(item["conf"])

            ix1, iy1, ix2, iy2 = item_box
            item_w = max(1, ix2 - ix1)
            item_h = max(1, iy2 - iy1)
            item_area = item_w * item_h

            if item_type == "helmet":
                if self._center_inside(item_box, head_region):
                    helmet_score = max(helmet_score, score)

            elif item_type == "no_helmet":
                if self._center_inside(item_box, head_region):
                    no_helmet_score = max(no_helmet_score, score)

            elif item_type == "vest":
                ratio = self._inter_area_ratio(item_box, torso_region)

                vest_shape_ok = (
                    item_area >= person_area * vest_min_area_ratio and
                    item_h >= person_h * vest_min_h_ratio and
                    item_w >= person_w * vest_min_w_ratio
                )

                if ratio >= vest_inter_ratio and vest_shape_ok:
                    vest_score = max(vest_score, score)

            elif item_type == "no_vest":
                ratio = self._inter_area_ratio(item_box, torso_region)

                if ratio >= no_vest_inter_ratio:
                    no_vest_score = max(no_vest_score, score)

        vest_margin_score = get_cfg("PPE_VEST_MARGIN_SCORE", 0.08)

        helmet_ok = (
            helmet_score >= self.helmet_ok_conf and
            helmet_score >= no_helmet_score
        )

        vest_ok = (
            vest_score >= self.vest_ok_conf and
            vest_score >= no_vest_score + vest_margin_score
        )

        missing_helmet = not helmet_ok
        missing_vest = not vest_ok

        return {
            "helmet_ok": helmet_ok,
            "vest_ok": vest_ok,
            "missing_helmet": missing_helmet,
            "missing_vest": missing_vest,
            "violation": missing_helmet or missing_vest,
            "helmet_score": helmet_score,
            "vest_score": vest_score,
            "no_helmet_score": no_helmet_score,
            "no_vest_score": no_vest_score
        }

    def check_target(self, frame, person_box):
        ppe_items = self.detect_target_only(frame, person_box)
        ppe_status = self.check_person_ppe(person_box, ppe_items)

        return ppe_status, ppe_items

    def get_person_label(self, ppe_status):
        if ppe_status is None:
            return "PPE CHECKING"

        if not ppe_status["violation"]:
            return "PPE OK"

        if ppe_status["missing_helmet"] and ppe_status["missing_vest"]:
            return "MISSING HELMET + VEST"

        if ppe_status["missing_helmet"]:
            return "MISSING HELMET"

        if ppe_status["missing_vest"]:
            return "MISSING VEST"

        return "PPE CHECKING"


class TargetPPEMonitor:
    """
    Bộ quản lý trạng thái PPE theo thời gian.
    GUI chỉ cần gọi update(frame, selected_target).

    selected_target yêu cầu dạng:
    {
        "id": target_id,
        "box": (x1, y1, x2, y2)
    }
    """

    def __init__(
        self,
        detector=None,
        enabled=None,
        run_interval=None,
        confirm_frames=None,
        clear_frames=None,
        edge_margin=None,
        min_target_h_ratio=None,
    ):
        self.enabled = enabled if enabled is not None else get_cfg("ENABLE_PPE", True)

        if self.enabled:
            self.detector = detector if detector is not None else PPEDetector()
        else:
            self.detector = None

        self.run_interval = run_interval if run_interval is not None else get_cfg("PPE_RUN_INTERVAL", 25)
        self.confirm_frames = confirm_frames if confirm_frames is not None else get_cfg("PPE_CONFIRM_FRAMES", 2)
        self.clear_frames = clear_frames if clear_frames is not None else get_cfg("PPE_CLEAR_FRAMES", 4)

        self.edge_margin = edge_margin if edge_margin is not None else get_cfg("PPE_EDGE_MARGIN", 12)
        self.min_target_h_ratio = (
            min_target_h_ratio if min_target_h_ratio is not None else get_cfg("PPE_MIN_TARGET_H_RATIO", 0.18)
        )

        self.reset()

    def reset(self):
        self.frame_id = 0
        self.last_target_id = None
        self.last_status = None
        self.last_items = []
        self.violation_count = 0
        self.clear_count = 0
        self.alarm_active = False
        self.alarm_label = ""

    def clear_alarm_when_target_invalid(self):
        self.last_status = None
        self.last_items = []
        self.violation_count = 0
        self.clear_count = 0
        self.alarm_active = False
        self.alarm_label = ""

    def is_target_box_valid(self, frame, person_box):
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = map(int, person_box)

        box_w = x2 - x1
        box_h = y2 - y1

        if box_w <= 0 or box_h <= 0:
            return False

        if box_h < h * self.min_target_h_ratio:
            return False

        if x1 <= self.edge_margin:
            return False

        if y1 <= self.edge_margin:
            return False

        if x2 >= w - self.edge_margin:
            return False

        if y2 >= h - self.edge_margin:
            return False

        return True

    def is_confirmed_ok(self):
        """
        True nếu PPE đã được xác nhận ổn định là OK (đủ helmet+vest) trong
        clear_frames lần check liên tiếp gần nhất. Dùng để quyết định có
        cho phép BẮT ĐẦU follow hay không. Nếu PPE bị tắt (enabled=False)
        thì coi như luôn pass để không đổi hành vi cũ.
        """
        if not self.enabled:
            return True

        if self.last_status is None:
            return False

        if self.last_status["violation"]:
            return False

        return self.clear_count >= self.clear_frames

    def _make_result(self, text):
        return {
            "enabled": self.enabled,
            "text": text,
            "status": self.last_status,
            "items": self.last_items,
            "alarm": self.alarm_active,
            "alarm_label": self.alarm_label
        }

    def _attach_to_target(self, selected_target):
        if selected_target is None:
            return

        selected_target["ppe_status"] = self.last_status
        selected_target["ppe_items"] = self.last_items
        selected_target["ppe_alarm"] = self.alarm_active
        selected_target["ppe_alarm_label"] = self.alarm_label

    def update(self, frame, selected_target):
        if not self.enabled or self.detector is None:
            return self._make_result("Disabled")

        if selected_target is None:
            self.clear_alarm_when_target_invalid()
            return self._make_result("No target")

        target_id = selected_target.get("id")
        person_box = selected_target.get("box")

        if person_box is None:
            self.clear_alarm_when_target_invalid()
            self._attach_to_target(selected_target)
            return self._make_result("No target")

        if self.last_target_id != target_id:
            self.reset()
            self.last_target_id = target_id

        if not self.is_target_box_valid(frame, person_box):
            self.clear_alarm_when_target_invalid()
            self._attach_to_target(selected_target)
            return self._make_result("Target partial")

        self.frame_id += 1

        if self.frame_id % self.run_interval != 0:
            self._attach_to_target(selected_target)

            if self.alarm_active:
                return self._make_result(self.alarm_label)

            if self.last_status is None:
                return self._make_result("PPE checking")

            if self.last_status["violation"]:
                label = self.detector.get_person_label(self.last_status)
                return self._make_result(
                    f"{label} {self.violation_count}/{self.confirm_frames}"
                )

            return self._make_result("PPE OK")

        try:
            ppe_status, ppe_items = self.detector.check_target(
                frame,
                person_box
            )

            self.last_status = ppe_status
            self.last_items = ppe_items

            raw_label = self.detector.get_person_label(ppe_status)

            if ppe_status["violation"]:
                self.violation_count += 1
                self.clear_count = 0

                if self.violation_count >= self.confirm_frames:
                    self.alarm_active = True
                    self.alarm_label = raw_label

            else:
                self.clear_count += 1
                self.violation_count = 0

                if self.clear_count >= self.clear_frames:
                    self.alarm_active = False
                    self.alarm_label = ""

            self._attach_to_target(selected_target)

            if self.alarm_active:
                return self._make_result(self.alarm_label)

            if ppe_status["violation"]:
                return self._make_result(
                    f"{raw_label} {self.violation_count}/{self.confirm_frames}"
                )

            return self._make_result("PPE OK")

        except Exception as exc:
            print("[PPE ERROR]", exc)
            self._attach_to_target(selected_target)
            return self._make_result("PPE error")