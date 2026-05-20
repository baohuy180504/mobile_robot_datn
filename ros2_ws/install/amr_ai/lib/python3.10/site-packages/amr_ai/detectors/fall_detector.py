# =============================
# fall_detector.py
# Tách riêng nhánh phát hiện té ngã bằng YOLO pose
# Bản fix ngã dọc theo hướng camera cho Jetson Orin
# =============================

import time
import math
import numpy as np
from ultralytics import YOLO

from amr_ai.core import config as cfg
from amr_ai.core.utils import (
    valid_fall_box_size, box_area, center_distance_sq, box_width_height,
    point_dist, sample_depth_at_point, crop_from_box
)


class FallDetector:
    def __init__(self, pose_model_path, infer_device, use_half):
        self.pose_model = YOLO(pose_model_path)
        self.infer_device = infer_device
        self.use_half = use_half
        self.fall_states = {}
        self.box_motion_states = {}
        self.last_fall_alarm_print_time = 0.0

    @staticmethod
    def cfg_value(name, default):
        return getattr(cfg, name, default)

    def reset(self):
        self.fall_states = {}
        self.box_motion_states = {}

    def get_keypoint(self, xy, conf, idx, conf_th=cfg.POSE_KPT_CONF):
        if xy is None or idx < 0 or idx >= len(xy):
            return None
        if conf is not None:
            if idx >= len(conf) or float(conf[idx]) < conf_th:
                return None
        return (float(xy[idx][0]), float(xy[idx][1]))

    @staticmethod
    def midpoint(p1, p2):
        if p1 is None or p2 is None:
            return None
        return ((p1[0] + p2[0]) * 0.5, (p1[1] + p2[1]) * 0.5)

    @staticmethod
    def point_y_ratio(p, frame_h):
        if p is None:
            return None
        return p[1] / float(frame_h)

    @staticmethod
    def torso_angle_deg_from_horizontal(shoulder_mid, hip_mid):
        if shoulder_mid is None or hip_mid is None:
            return None
        dx = abs(hip_mid[0] - shoulder_mid[0])
        dy = abs(hip_mid[1] - shoulder_mid[1])
        return math.degrees(math.atan2(dy, dx + 1e-6))

    @staticmethod
    def expand_box(box, frame_w, frame_h, scale_x=0.18, scale_y=0.12):
        x1, y1, x2, y2 = map(int, box)
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        pad_x = int(bw * scale_x)
        pad_y = int(bh * scale_y)
        nx1 = max(0, x1 - pad_x)
        ny1 = max(0, y1 - pad_y)
        nx2 = min(frame_w - 1, x2 + pad_x)
        ny2 = min(frame_h - 1, y2 + pad_y)
        return np.array([nx1, ny1, nx2, ny2], dtype=np.float32)

    def get_box_motion_features(self, track_id, box, frame_h, now):
        x1, y1, x2, y2 = map(int, box)
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        cy = (y1 + y2) * 0.5
        bottom = y2
        center_y_ratio = cy / float(frame_h)
        bottom_ratio = bottom / float(frame_h)
        aspect_ratio = bw / float(bh)

        if track_id not in self.box_motion_states:
            self.box_motion_states[track_id] = {
                "prev_cy": cy,
                "prev_h": bh,
                "last_seen": now
            }

        st = self.box_motion_states[track_id]
        drop_px = cy - st["prev_cy"]
        height_ratio = bh / float(max(1, st["prev_h"]))
        st["prev_cy"] = cy
        st["prev_h"] = bh
        st["last_seen"] = now

        return {
            "center_y_ratio": center_y_ratio,
            "bottom_ratio": bottom_ratio,
            "aspect_ratio": aspect_ratio,
            "drop_px": drop_px,
            "height_ratio": height_ratio
        }

    def is_pose_needed_fast(self, track_id, box, frame_h, now, force_scan=False):
        if not valid_fall_box_size(box):
            return False

        feats = self.get_box_motion_features(track_id, box, frame_h, now)

        side_like = (
            feats["aspect_ratio"] >= 1.05 and
            feats["bottom_ratio"] >= 0.72
        )

        forward_like = (
            feats["drop_px"] >= 8 and
            feats["center_y_ratio"] >= 0.48 and
            feats["height_ratio"] <= 0.88
        )

        already_alert = False
        baseline_not_ready = True
        if track_id in self.fall_states:
            st = self.fall_states[track_id]
            already_alert = st["fallen"] or (now < st["alert_until"])
            baseline_not_ready = st.get("stand_count", 0) < self.cfg_value("FORWARD_MIN_STAND_FRAMES", 6)

        return side_like or forward_like or already_alert or force_scan or baseline_not_ready

    def choose_pose_targets(self, detections, center_x, center_y, frame_h, now, frame_count):
        candidates = []
        pose_scan_every = self.cfg_value("FORWARD_POSE_SCAN_EVERY", 2)
        scan_period = max(1, cfg.POSE_RUN_INTERVAL * pose_scan_every)
        force_scan = (frame_count % scan_period) == 0

        for det in detections:
            tid = det["id"]
            box = det["box"]
            if not self.is_pose_needed_fast(tid, box, frame_h, now, force_scan=force_scan):
                continue

            area = box_area(box)
            dist2 = center_distance_sq(box, center_x, center_y)

            suspect_bonus = 0.0
            if tid in self.fall_states:
                st = self.fall_states[tid]
                if st["fallen"] or now < st["alert_until"] or st["fall_count"] > 0:
                    suspect_bonus = 500000.0
                if st.get("stand_count", 0) < self.cfg_value("FORWARD_MIN_STAND_FRAMES", 6):
                    suspect_bonus += 200000.0

            score = suspect_bonus + area - 0.12 * dist2
            candidates.append((score, det))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in candidates[:cfg.MAX_POSE_PEOPLE]]

    def run_pose_on_crop(self, crop_bgr, det_box):
        try:
            results = self.pose_model.predict(
                crop_bgr,
                conf=cfg.POSE_CONF,
                imgsz=cfg.POSE_IMGSZ,
                half=self.use_half,
                device=self.infer_device,
                verbose=False
            )
        except Exception:
            return None

        if results is None or len(results) == 0:
            return None

        result = results[0]
        if result.keypoints is None or result.boxes is None or result.keypoints.xy is None:
            return None

        boxes = result.boxes.xyxy.cpu().numpy()
        if len(boxes) == 0:
            return None

        if result.boxes.conf is not None:
            confs = result.boxes.conf.cpu().numpy()
            best_idx = int(np.argmax(confs))
        else:
            areas = [(b[2] - b[0]) * (b[3] - b[1]) for b in boxes]
            best_idx = int(np.argmax(areas))

        kpts_xy = result.keypoints.xy.cpu().numpy()[best_idx]
        if result.keypoints.conf is not None:
            kpts_conf = result.keypoints.conf.cpu().numpy()[best_idx]
        else:
            kpts_conf = np.ones((kpts_xy.shape[0],), dtype=np.float32)

        x1, y1, _, _ = map(int, det_box)
        kpts_xy_global = kpts_xy.copy()
        kpts_xy_global[:, 0] += x1
        kpts_xy_global[:, 1] += y1

        return {"kpts_xy": kpts_xy_global, "kpts_conf": kpts_conf}

    def compute_pose_features_from_kpts(self, kpts_xy, kpts_conf, det_box, frame_h, depth_map=None):
        nose = self.get_keypoint(kpts_xy, kpts_conf, 0)
        left_shoulder = self.get_keypoint(kpts_xy, kpts_conf, 5)
        right_shoulder = self.get_keypoint(kpts_xy, kpts_conf, 6)
        left_hip = self.get_keypoint(kpts_xy, kpts_conf, 11)
        right_hip = self.get_keypoint(kpts_xy, kpts_conf, 12)
        left_knee = self.get_keypoint(kpts_xy, kpts_conf, 13)
        right_knee = self.get_keypoint(kpts_xy, kpts_conf, 14)
        left_ankle = self.get_keypoint(kpts_xy, kpts_conf, 15)
        right_ankle = self.get_keypoint(kpts_xy, kpts_conf, 16)

        shoulder_mid = self.midpoint(left_shoulder, right_shoulder)
        hip_mid = self.midpoint(left_hip, right_hip)
        knee_mid = self.midpoint(left_knee, right_knee)
        ankle_mid = self.midpoint(left_ankle, right_ankle)

        if shoulder_mid is None and nose is not None and hip_mid is not None:
            shoulder_mid = ((nose[0] + hip_mid[0]) * 0.5, (nose[1] + hip_mid[1]) * 0.5)

        torso_angle = self.torso_angle_deg_from_horizontal(shoulder_mid, hip_mid)
        bw, bh = box_width_height(det_box)
        box_aspect = bw / float(max(1, bh))
        box_center_y = (float(det_box[1]) + float(det_box[3])) * 0.5
        center_y_ratio = box_center_y / float(frame_h)
        bottom_ratio = float(det_box[3]) / float(frame_h)

        hip_ratio = self.point_y_ratio(hip_mid, frame_h)
        shoulder_ratio = self.point_y_ratio(shoulder_mid, frame_h)

        hip_above_knee = None
        if hip_mid is not None and knee_mid is not None:
            hip_above_knee = hip_mid[1] < (knee_mid[1] - cfg.KNEE_MARGIN_PX)

        body_axis_len = None
        if shoulder_mid is not None and ankle_mid is not None:
            body_axis_len = point_dist(shoulder_mid, ankle_mid)
        elif hip_mid is not None and ankle_mid is not None:
            body_axis_len = point_dist(hip_mid, ankle_mid)

        compact_ratio = None
        if body_axis_len is not None and bh > 0:
            compact_ratio = body_axis_len / float(bh)

        shoulder_z = sample_depth_at_point(depth_map, shoulder_mid)
        hip_z = sample_depth_at_point(depth_map, hip_mid)
        ankle_z = sample_depth_at_point(depth_map, ankle_mid)

        torso_depth_tilt = None
        if shoulder_z is not None and ankle_z is not None:
            torso_depth_tilt = abs(shoulder_z - ankle_z)
        elif hip_z is not None and ankle_z is not None:
            torso_depth_tilt = abs(hip_z - ankle_z)

        return {
            "shoulder_mid": shoulder_mid,
            "hip_mid": hip_mid,
            "torso_angle": torso_angle,
            "box_h": bh,
            "box_aspect": box_aspect,
            "center_y_ratio": center_y_ratio,
            "bottom_ratio": bottom_ratio,
            "hip_ratio": hip_ratio,
            "shoulder_ratio": shoulder_ratio,
            "hip_above_knee": hip_above_knee,
            "compact_ratio": compact_ratio,
            "torso_depth_tilt": torso_depth_tilt,
        }

    def ensure_fall_state(self, track_id, det_box, now):
        if track_id not in self.fall_states:
            self.fall_states[track_id] = {
                "prev_hip_y": None,
                "prev_shoulder_y": None,
                "prev_box_h": None,
                "prev_center_y": None,
                "stand_box_h": None,
                "stand_hip_y": None,
                "stand_shoulder_y": None,
                "stand_center_y": None,
                "stand_count": 0,
                "fall_count": 0,
                "clear_count": 0,
                "recover_count": 0,
                "fallen": False,
                "alert_until": 0.0,
                "last_seen": now,
                "last_box": det_box.copy(),
                "last_fall_mode": None
            }

    def mark_visible_tracks(self, detections, now):
        for det in detections:
            tid = det["id"]
            self.ensure_fall_state(tid, det["box"], now)
            self.fall_states[tid]["last_seen"] = now
            self.fall_states[tid]["last_box"] = det["box"].copy()

    def update_standing_baseline(self, state, feats):
        torso_angle = feats["torso_angle"]
        hip_ratio = feats["hip_ratio"]
        shoulder_ratio = feats["shoulder_ratio"]
        box_aspect = feats["box_aspect"]
        box_h = feats["box_h"]
        hip_mid = feats["hip_mid"]
        shoulder_mid = feats["shoulder_mid"]
        center_y_ratio = feats["center_y_ratio"]

        if torso_angle is None or hip_ratio is None or shoulder_ratio is None:
            return
        if hip_mid is None or shoulder_mid is None:
            return

        upright_like = (
            torso_angle >= self.cfg_value("STAND_TORSO_MIN_DEG", 58.0)
            and box_aspect <= self.cfg_value("STAND_BOX_ASPECT_MAX", 0.95)
            and hip_ratio <= self.cfg_value("STAND_HIP_RATIO_MAX", 0.64)
            and shoulder_ratio <= self.cfg_value("STAND_SHOULDER_RATIO_MAX", 0.48)
        )

        if not upright_like:
            return
        if state["fallen"] or state["fall_count"] > 0:
            return

        alpha = self.cfg_value("FORWARD_BASELINE_ALPHA", 0.08)

        if state["stand_box_h"] is None:
            state["stand_box_h"] = float(box_h)
            state["stand_hip_y"] = float(hip_mid[1])
            state["stand_shoulder_y"] = float(shoulder_mid[1])
            state["stand_center_y"] = float(center_y_ratio)
            state["stand_count"] = 1
            return

        if box_h >= state["stand_box_h"] * 0.90:
            state["stand_box_h"] = (1.0 - alpha) * state["stand_box_h"] + alpha * float(box_h)
            state["stand_hip_y"] = (1.0 - alpha) * state["stand_hip_y"] + alpha * float(hip_mid[1])
            state["stand_shoulder_y"] = (1.0 - alpha) * state["stand_shoulder_y"] + alpha * float(shoulder_mid[1])
            state["stand_center_y"] = (1.0 - alpha) * state["stand_center_y"] + alpha * float(center_y_ratio)
            state["stand_count"] = min(60, state["stand_count"] + 1)

    def update_single_fall_state(self, track_id, det_box, feats, now):
        state = self.fall_states[track_id]
        hip_mid = feats["hip_mid"]
        shoulder_mid = feats["shoulder_mid"]
        torso_angle = feats["torso_angle"]
        hip_ratio = feats["hip_ratio"]
        shoulder_ratio = feats["shoulder_ratio"]
        box_aspect = feats["box_aspect"]
        hip_above_knee = feats["hip_above_knee"]
        compact_ratio = feats["compact_ratio"]
        torso_depth_tilt = feats["torso_depth_tilt"]
        box_h = feats["box_h"]
        center_y_ratio = feats["center_y_ratio"]

        hip_drop_px = 0.0
        shoulder_drop_px = 0.0
        center_drop_ratio = 0.0

        if hip_mid is not None and state["prev_hip_y"] is not None:
            hip_drop_px = float(hip_mid[1] - state["prev_hip_y"])
        if shoulder_mid is not None and state["prev_shoulder_y"] is not None:
            shoulder_drop_px = float(shoulder_mid[1] - state["prev_shoulder_y"])
        if state["prev_center_y"] is not None:
            center_drop_ratio = float(center_y_ratio - state["prev_center_y"])

        rapid_drop = (
            hip_drop_px >= cfg.FALL_DROP_PX
            or shoulder_drop_px >= cfg.FALL_SHOULDER_DROP_PX
            or center_drop_ratio >= self.cfg_value("FORWARD_FAST_CENTER_DROP_RATIO", 0.035)
        )

        height_shrink_ratio = 1.0
        if state["prev_box_h"] is not None and state["prev_box_h"] > 0:
            height_shrink_ratio = box_h / float(state["prev_box_h"])

        baseline_ready = state.get("stand_count", 0) >= self.cfg_value("FORWARD_MIN_STAND_FRAMES", 6)
        base_height_ratio = 1.0
        base_center_drop_ratio = 0.0
        base_hip_drop_ratio = 0.0
        base_shoulder_drop_ratio = 0.0

        if baseline_ready and state["stand_box_h"] is not None:
            base_height_ratio = box_h / float(max(1.0, state["stand_box_h"]))
            if state["stand_center_y"] is not None:
                base_center_drop_ratio = center_y_ratio - state["stand_center_y"]
            if hip_mid is not None and state["stand_hip_y"] is not None:
                base_hip_drop_ratio = (hip_mid[1] - state["stand_hip_y"]) / float(max(1.0, state["stand_box_h"]))
            if shoulder_mid is not None and state["stand_shoulder_y"] is not None:
                base_shoulder_drop_ratio = (shoulder_mid[1] - state["stand_shoulder_y"]) / float(max(1.0, state["stand_box_h"]))

        classic_side_fall = (
            valid_fall_box_size(det_box)
            and torso_angle is not None
            and hip_ratio is not None
            and shoulder_ratio is not None
            and torso_angle <= cfg.FALL_TORSO_MAX_DEG
            and hip_ratio >= cfg.FALL_LOW_HIP_RATIO
            and shoulder_ratio >= cfg.FALL_LOW_SHOULDER_RATIO
            and box_aspect >= cfg.FALL_BOX_ASPECT_MIN
        )

        forward_back_fall = (
            valid_fall_box_size(det_box)
            and rapid_drop
            and hip_ratio is not None
            and shoulder_ratio is not None
            and hip_ratio >= cfg.FORWARD_FALL_HIP_RATIO
            and shoulder_ratio >= cfg.FORWARD_FALL_SHOULDER_RATIO
            and compact_ratio is not None
            and compact_ratio <= cfg.FALL_COMPACT_RATIO
            and height_shrink_ratio <= cfg.FALL_HEIGHT_SHRINK_RATIO
            and torso_depth_tilt is not None
            and torso_depth_tilt >= cfg.FALL_DEPTH_TILT_MM
        )

        forward_back_fall_no_depth = (
            valid_fall_box_size(det_box)
            and rapid_drop
            and hip_ratio is not None
            and shoulder_ratio is not None
            and hip_ratio >= 0.56
            and shoulder_ratio >= 0.40
            and compact_ratio is not None
            and compact_ratio <= self.cfg_value("FORWARD_NO_DEPTH_COMPACT_RATIO", 0.62)
            and height_shrink_ratio <= self.cfg_value("FORWARD_NO_DEPTH_HEIGHT_RATIO", 0.76)
            and torso_depth_tilt is None
        )

        vertical_forward_fall = (
            valid_fall_box_size(det_box)
            and baseline_ready
            and hip_ratio is not None
            and shoulder_ratio is not None
            and base_height_ratio <= self.cfg_value("FORWARD_BOX_HEIGHT_RATIO", 0.86)
            and (
                base_center_drop_ratio >= self.cfg_value("FORWARD_CENTER_DROP_RATIO", 0.075)
                or base_hip_drop_ratio >= self.cfg_value("FORWARD_HIP_DROP_RATIO", 0.070)
                or base_shoulder_drop_ratio >= self.cfg_value("FORWARD_SHOULDER_DROP_RATIO", 0.075)
                or rapid_drop
            )
            and (
                compact_ratio is not None and compact_ratio <= self.cfg_value("FORWARD_COMPACT_RATIO", 0.72)
                or torso_depth_tilt is not None and torso_depth_tilt >= self.cfg_value("FORWARD_DEPTH_TILT_MM_SOFT", 120.0)
                or hip_ratio >= 0.60 and shoulder_ratio >= 0.42
            )
        )

        depth_only_forward_fall = (
            valid_fall_box_size(det_box)
            and baseline_ready
            and torso_depth_tilt is not None
            and torso_depth_tilt >= self.cfg_value("FORWARD_DEPTH_TILT_MM_SOFT", 120.0)
            and base_height_ratio <= self.cfg_value("FORWARD_DEPTH_HEIGHT_RATIO", 0.92)
            and (
                base_center_drop_ratio >= self.cfg_value("FORWARD_CENTER_DROP_RATIO_SOFT", 0.055)
                or rapid_drop
            )
        )

        sit_like = (
            torso_angle is not None
            and hip_ratio is not None
            and torso_angle >= cfg.SIT_TORSO_MIN_DEG
            and hip_ratio >= cfg.SIT_LOW_HIP_RATIO
            and hip_above_knee is True
            and not rapid_drop
            and base_height_ratio >= self.cfg_value("SIT_MIN_HEIGHT_RATIO", 0.58)
            and (torso_depth_tilt is None or torso_depth_tilt < 140.0)
        )

        bend_like = (
            torso_angle is not None
            and hip_ratio is not None
            and cfg.BEND_TORSO_MIN_DEG <= torso_angle <= cfg.BEND_TORSO_MAX_DEG
            and hip_ratio <= cfg.BEND_HIP_MAX_RATIO
            and not rapid_drop
        )

        kneel_like = (
            torso_angle is not None
            and hip_ratio is not None
            and torso_angle >= 58.0
            and hip_ratio >= 0.52
            and box_aspect < 1.15
            and not rapid_drop
            and base_height_ratio >= self.cfg_value("KNEEL_MIN_HEIGHT_RATIO", 0.55)
        )

        fall_candidate = (
            classic_side_fall
            or forward_back_fall
            or forward_back_fall_no_depth
            or vertical_forward_fall
            or depth_only_forward_fall
        ) and not sit_like and not bend_like and not kneel_like

        if classic_side_fall:
            fall_mode = "SIDE_FALL"
        elif forward_back_fall or forward_back_fall_no_depth or vertical_forward_fall or depth_only_forward_fall:
            fall_mode = "FORWARD_BACK_FALL"
        else:
            fall_mode = None

        if fall_candidate:
            state["clear_count"] = 0
            add_count = 2 if rapid_drop else 1
            if vertical_forward_fall or depth_only_forward_fall:
                add_count = max(add_count, 2)
            state["fall_count"] = min(cfg.FALL_CONFIRM_FRAMES + 3, state["fall_count"] + add_count)
            if fall_mode is not None:
                state["last_fall_mode"] = fall_mode
        else:
            state["clear_count"] += 1
            state["fall_count"] = max(0, state["fall_count"] - 1)

        if state["fall_count"] >= cfg.FALL_CONFIRM_FRAMES:
            if not state["fallen"] and now - self.last_fall_alarm_print_time > 1.0:
                print(f"[ALERT] Track {track_id} FALL DETECTED")
                self.last_fall_alarm_print_time = now

            state["fallen"] = True
            state["alert_until"] = max(state["alert_until"], now + cfg.FALL_ALERT_HOLD_SEC)
            state["recover_count"] = 0

        recovered_like = (
            torso_angle is not None
            and hip_ratio is not None
            and torso_angle >= 60.0
            and hip_ratio < 0.58
            and box_aspect < 0.95
            and base_height_ratio >= self.cfg_value("RECOVER_MIN_HEIGHT_RATIO", 0.80)
        )

        if state["fallen"]:
            if recovered_like and now >= state["alert_until"]:
                state["recover_count"] += 1
            else:
                state["recover_count"] = 0

            if state["recover_count"] >= cfg.RECOVER_CONFIRM_FRAMES:
                state["fallen"] = False
                state["fall_count"] = 0

        self.update_standing_baseline(state, feats)

        if hip_mid is not None:
            state["prev_hip_y"] = hip_mid[1]
        if shoulder_mid is not None:
            state["prev_shoulder_y"] = shoulder_mid[1]
        state["prev_box_h"] = box_h
        state["prev_center_y"] = center_y_ratio

    def cleanup(self, now):
        for tid in list(self.fall_states.keys()):
            state = self.fall_states[tid]
            if (now - state["last_seen"]) > cfg.STATE_TRACK_TIMEOUT:
                if now >= state["alert_until"]:
                    del self.fall_states[tid]

        for tid in list(self.box_motion_states.keys()):
            if now - self.box_motion_states[tid]["last_seen"] > cfg.STATE_TRACK_TIMEOUT:
                del self.box_motion_states[tid]

    def get_active_fall_map(self, now):
        active = {}
        for tid, state in self.fall_states.items():
            alert_active = state["fallen"] or (now < state["alert_until"])
            if alert_active:
                active[tid] = {
                    "box": state["last_box"],
                    "fall_mode": state["last_fall_mode"]
                }
        return active

    def update(self, frame, depth, detections, center_x, center_y, frame_h, frame_count, now):
        self.mark_visible_tracks(detections, now)

        for det in detections:
            det["falling"] = False
            det["fall_mode"] = None

        if frame_count % cfg.POSE_RUN_INTERVAL == 0 and len(detections) > 0:
            frame_w = frame.shape[1]
            pose_targets = self.choose_pose_targets(detections, center_x, center_y, frame_h, now, frame_count)

            for det in pose_targets:
                expanded_box = self.expand_box(det["box"], frame_w, frame_h)
                crop, clipped_box = crop_from_box(frame, expanded_box)
                if crop is None:
                    continue

                pose_info = self.run_pose_on_crop(crop, clipped_box)
                if pose_info is None:
                    continue

                feats = self.compute_pose_features_from_kpts(
                    pose_info["kpts_xy"],
                    pose_info["kpts_conf"],
                    det["box"],
                    frame_h,
                    depth
                )
                self.update_single_fall_state(det["id"], det["box"], feats, now)

        self.cleanup(now)
        active_fall_map = self.get_active_fall_map(now)

        for det in detections:
            if det["id"] in active_fall_map:
                det["falling"] = True
                det["fall_mode"] = active_fall_map[det["id"]]["fall_mode"]

        return detections
