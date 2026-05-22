import cv2
from ultralytics import YOLO


class FireSmokeDetector:
    def __init__(
        self,
        model_path,
        infer_device=0,
        imgsz=640,
        fire_conf=0.40,
        smoke_conf=0.60
    ):
        self.model = YOLO(model_path)
        self.infer_device = infer_device
        self.imgsz = imgsz
        self.fire_conf = fire_conf
        self.smoke_conf = smoke_conf

    def is_valid_smoke_region(self, frame, box, conf):
        x1, y1, x2, y2 = box
        frame_h, frame_w = frame.shape[:2]

        x1 = max(0, min(x1, frame_w - 1))
        y1 = max(0, min(y1, frame_h - 1))
        x2 = max(0, min(x2, frame_w - 1))
        y2 = max(0, min(y2, frame_h - 1))

        if x2 <= x1 or y2 <= y1:
            return False

        box_w = x2 - x1
        box_h = y2 - y1
        area = box_w * box_h
        frame_area = frame_w * frame_h

        if area < frame_area * 0.004:
            return False

        if conf < self.smoke_conf:
            return False

        roi = frame[y1:y2, x1:x2]

        if roi.size == 0:
            return False

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        s_mean = hsv[:, :, 1].mean()
        v_mean = hsv[:, :, 2].mean()

        if s_mean > 120:
            return False

        if v_mean < 50:
            return False

        return True

    def detect(self, frame):
        base_conf = min(self.fire_conf, self.smoke_conf, 0.10)

        results = self.model.predict(
            frame,
            imgsz=self.imgsz,
            conf=base_conf,
            iou=0.45,
            device=self.infer_device,
            verbose=False
        )

        detections = []
        fire_detected = False
        smoke_detected = False

        if results is None or len(results) == 0:
            return detections, fire_detected, smoke_detected

        boxes = results[0].boxes
        names = results[0].names

        if boxes is None:
            return detections, fire_detected, smoke_detected

        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            cls_name = names[cls_id].lower()

            is_fire = "fire" in cls_name or "flame" in cls_name
            is_smoke = "smoke" in cls_name

            if is_fire and conf >= self.fire_conf:
                fire_detected = True
                detections.append({
                    "box": (x1, y1, x2, y2),
                    "class_name": "fire",
                    "conf": conf
                })

            elif is_smoke:
                smoke_box = (x1, y1, x2, y2)

                if not self.is_valid_smoke_region(frame, smoke_box, conf):
                    continue

                smoke_detected = True
                detections.append({
                    "box": smoke_box,
                    "class_name": "smoke",
                    "conf": conf
                })

        return detections, fire_detected, smoke_detected

    def draw(self, frame, detections, fire_detected, smoke_detected):
        annotated = frame.copy()

        for det in detections:
            x1, y1, x2, y2 = det["box"]
            class_name = det["class_name"]
            conf = det["conf"]

            if class_name == "fire":
                color = (0, 0, 255)
                label = f"FIRE {conf:.2f}"
            else:
                color = (160, 160, 160)
                label = f"SMOKE {conf:.2f}"

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                annotated,
                label,
                (x1, max(25, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )

        if fire_detected and smoke_detected:
            alert_text = "CANH BAO: CO LUA VA KHOI"
        elif fire_detected:
            alert_text = "CANH BAO: CO LUA"
        elif smoke_detected:
            alert_text = "CANH BAO: CO KHOI"
        else:
            alert_text = None

        if alert_text is not None:
            cv2.putText(
                annotated,
                alert_text,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 0, 255),
                3
            )

        return annotated
