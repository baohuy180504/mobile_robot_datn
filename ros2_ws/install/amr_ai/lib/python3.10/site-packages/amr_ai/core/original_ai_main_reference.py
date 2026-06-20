# =============================
# main.py
# Chương trình chính: Camera + YOLO tracking + ReID + depth + fall detection
# =============================

import cv2
import time
import torch
import numpy as np
from ultralytics import YOLO

import config as cfg
from camera_openni import OpenNICamera
from reid import ReIDManager
from fall_detector import FallDetector
from utils import (
    valid_box_size, crop_from_box, center_distance_sq,
    estimate_depth_distance
)


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


def draw_results(annotated, detections, selected_target, selected_distance_mm, fps_value):
    h, w = annotated.shape[:2]

    for det in detections:
        x1, y1, x2, y2 = map(int, det["box"])
        color = (0, 255, 255)
        text_top = None

        if selected_target is not None and det["id"] == selected_target["id"]:
            color = (0, 255, 0)

        if det["falling"]:
            color = (0, 0, 255)
            text_top = "FALL DETECTED"

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        if text_top is not None:
            cv2.putText(
                annotated,
                text_top,
                (x1, max(25, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                color,
                2
            )

    if selected_target is not None and selected_distance_mm is not None:
        x1, y1, x2, y2 = map(int, selected_target["box"])
        label = f"{selected_distance_mm / 10.0:.1f} cm"

        text_y = max(25, y1 - 10)
        if any(det["id"] == selected_target["id"] and det["falling"] for det in detections):
            text_y = min(h - 10, y2 + 25)

        cv2.putText(
            annotated,
            label,
            (x1, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

    total_fall = sum(1 for det in detections if det["falling"])
    if total_fall > 0:
        cv2.putText(
            annotated,
            "CANH BAO: CO NGUOI TE NGA",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 255),
            3
        )
        cv2.putText(
            annotated,
            f"So nguoi nghi te: {total_fall}",
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2
        )

    if cfg.SHOW_FPS:
        cv2.putText(
            annotated,
            f"FPS: {fps_value:.1f}",
            (20, h - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )

    return annotated


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    infer_device = 0 if torch.cuda.is_available() else "cpu"
    use_half = torch.cuda.is_available()

    print("Device:", device)

    detect_model = YOLO(cfg.MODEL_PATH)
    reid = ReIDManager(device)
    fall_detector = FallDetector(cfg.POSE_MODEL_PATH, infer_device, use_half)

    camera = OpenNICamera()
    camera.start()

    window_name = "ReID + Astra Depth + Fall Detection"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.imshow(window_name, np.zeros((cfg.CAM_H, cfg.CAM_W, 3), dtype=np.uint8))
    cv2.waitKey(1)

    prepare_mode = False
    prepare_start_time = 0.0
    enroll_mode = False

    frame_count = 0
    fps_value = 0.0
    fps_last_t = time.time()

    try:
        while True:
            frame, depth = camera.read()
            if frame is None or depth is None:
                continue

            annotated = frame.copy()
            h, w = frame.shape[:2]
            center_x = w // 2
            center_y = h // 2
            now = time.time()
            frame_count += 1

            dt = now - fps_last_t
            if dt > 0:
                fps_value = 0.9 * fps_value + 0.1 * (1.0 / dt)
            fps_last_t = now

            if prepare_mode:
                elapsed = now - prepare_start_time
                if elapsed >= cfg.PREPARE_COUNTDOWN:
                    prepare_mode = False
                    enroll_mode = True
                    reid.enroll_embeddings = []
                    reid.enroll_upper_embeddings = []
                    reid.enroll_shirts = []
                    print("Bắt đầu enroll...")

            detect_results = detect_model.track(
                frame,
                persist=True,
                classes=[0],
                conf=0.4,
                tracker=cfg.TRACKER_CFG,
                verbose=False
            )

            boxes = detect_results[0].boxes
            detections = []
            nearest_track = None
            nearest_box = None

            if boxes is not None and boxes.id is not None:
                xyxy = boxes.xyxy.cpu().numpy()
                ids = boxes.id.int().cpu().tolist()
                confs = boxes.conf.cpu().numpy()

                nearest_track, nearest_box = get_nearest_track(xyxy, ids, center_x, center_y)

                if enroll_mode and nearest_box is not None:
                    try:
                        reid.add_enroll_sample(frame, nearest_box)
                    except Exception:
                        pass

                    if len(reid.enroll_embeddings) >= cfg.ENROLL_FRAMES:
                        reid.finish_enroll(nearest_track, nearest_box, now)
                        enroll_mode = False
                        print(f"Enroll xong, OWNER {cfg.OWNER_ID} -> track {reid.current_track_id}")

                for box, tid, conf in zip(xyxy, ids, confs):
                    detections.append({
                        "id": tid,
                        "box": box,
                        "conf": float(conf),
                        "emb_sim": None,
                        "shirt_sim": None,
                        "motion_sim": None,
                        "score": None,
                        "falling": False,
                        "fall_mode": None
                    })

            selected_target = reid.select_target(frame, detections, center_x, center_y, now, frame_count)

            selected_distance_mm = None
            if selected_target is not None:
                raw_distance_mm, _ = estimate_depth_distance(depth, selected_target["box"])
                selected_distance_mm = reid.smooth_depth_distance(raw_distance_mm)

            detections = fall_detector.update(
                frame, depth, detections, center_x, center_y, h, frame_count, now
            )

            annotated = draw_results(annotated, detections, selected_target, selected_distance_mm, fps_value)
            cv2.imshow(window_name, annotated)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("e"):
                reid.reset()
                fall_detector.reset()
                prepare_mode = True
                enroll_mode = False
                prepare_start_time = time.time()
                print("Bắt đầu đếm ngược 5 giây để chuẩn bị enroll")
            elif key == ord("r"):
                reid.reset()
                fall_detector.reset()
                prepare_mode = False
                enroll_mode = False
                print("Đã reset target profile")

    finally:
        camera.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
