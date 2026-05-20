# =============================
# reid.py
# ReID + chọn lại target sau khi mất track
# =============================

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models

from amr_ai.core import config as cfg
from amr_ai.core.utils import (
    crop_from_box, valid_box_size, box_area, center_distance_sq,
    iou, size_similarity, normalize_person_crop
)


class ReIDManager:
    def __init__(self, device):
        self.device = device
        weights = models.MobileNet_V3_Small_Weights.DEFAULT
        backbone = models.mobilenet_v3_small(weights=weights)
        self.feature_model = backbone.features.to(device)
        self.feature_model.eval()
        self.pool = nn.AdaptiveAvgPool2d((1, 1)).to(device)

        self.mean = torch.tensor([0.485, 0.456, 0.406], device=device).view(1, 3, 1, 1)
        self.std = torch.tensor([0.229, 0.224, 0.225], device=device).view(1, 3, 1, 1)

        self.reset()

    def reset(self):
        self.target_profile = None
        self.target_upper_profile = None
        self.target_shirt_profile = None

        self.owner_embeddings_bank = []
        self.owner_upper_embeddings_bank = []
        self.owner_shirt_bank = []

        self.current_track_id = None
        self.current_target_box = None
        self.current_target_sim = -1.0
        self.current_target_score = -1.0
        self.last_target_time = 0.0

        self.enroll_embeddings = []
        self.enroll_upper_embeddings = []
        self.enroll_shirts = []

        self.candidate_track_id = None
        self.candidate_count = 0
        self.last_brightness_value = 0.0
        self.smoothed_distance_mm = None

    def crop_reid_core_region(self, crop_bgr):
        if crop_bgr is None or crop_bgr.size == 0:
            return None
        h, w = crop_bgr.shape[:2]
        if h < 40 or w < 20:
            return crop_bgr
        return crop_bgr[int(h * 0.12):int(h * 0.88), int(w * 0.20):int(w * 0.80)]

    def crop_upper_body(self, crop_bgr):
        if crop_bgr is None or crop_bgr.size == 0:
            return None
        h, w = crop_bgr.shape[:2]
        if h < 40 or w < 20:
            return crop_bgr
        return crop_bgr[int(h * 0.10):int(h * 0.60), int(w * 0.18):int(w * 0.82)]

    def crop_shirt_region(self, crop_bgr):
        if crop_bgr is None or crop_bgr.size == 0:
            return None
        h, w = crop_bgr.shape[:2]
        if h < 30 or w < 20:
            return None
        shirt = crop_bgr[int(h * 0.22):int(h * 0.58), int(w * 0.22):int(w * 0.78)]
        return None if shirt.size == 0 else shirt

    def extract_embedding(self, crop_bgr):
        img = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (cfg.CROP_W, cfg.CROP_H))
        tensor = torch.from_numpy(img).float().permute(2, 0, 1).unsqueeze(0).to(self.device) / 255.0
        tensor = (tensor - self.mean) / self.std

        with torch.no_grad():
            feat = self.feature_model(tensor)
            feat = self.pool(feat)
            feat = feat.view(feat.size(0), -1)
            feat = torch.nn.functional.normalize(feat, dim=1)
        return feat.squeeze(0).cpu().numpy()

    def extract_shirt_hist(self, crop_bgr):
        shirt = self.crop_shirt_region(crop_bgr)
        if shirt is None:
            return None

        shirt = cv2.resize(shirt, (72, 72))
        shirt = cv2.GaussianBlur(shirt, (3, 3), 0)
        hsv = cv2.cvtColor(shirt, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (0, 20, 35), (180, 255, 255))
        if cv2.countNonZero(mask) < 0.12 * mask.size:
            mask = None

        hist_h = cv2.calcHist([hsv], [0], mask, [18], [0, 180])
        hist_s = cv2.calcHist([hsv], [1], mask, [16], [0, 256])
        hist_v = cv2.calcHist([hsv], [2], mask, [16], [0, 256])

        hist = np.concatenate([hist_h.flatten(), hist_s.flatten(), hist_v.flatten()]).astype(np.float32)
        norm = np.linalg.norm(hist)
        if norm > 1e-12:
            hist /= norm
        return hist

    @staticmethod
    def cosine_similarity(a, b):
        if a is None or b is None:
            return -1.0
        return float(np.dot(a, b))

    @staticmethod
    def hist_similarity(a, b):
        if a is None or b is None:
            return 0.0
        return float(np.dot(a, b))

    @staticmethod
    def average_embeddings(embeddings):
        if len(embeddings) == 0:
            return None
        avg = np.mean(np.stack(embeddings, axis=0), axis=0)
        norm = np.linalg.norm(avg)
        if norm > 1e-12:
            avg /= norm
        return avg

    @staticmethod
    def average_hists(hists):
        if len(hists) == 0:
            return None
        avg = np.mean(np.stack(hists, axis=0), axis=0)
        norm = np.linalg.norm(avg)
        if norm > 1e-12:
            avg /= norm
        return avg

    def keep_best_embeddings(self, embeddings, max_keep=cfg.MAX_OWNER_SAMPLES):
        if len(embeddings) <= max_keep:
            return embeddings[:]
        ref = self.average_embeddings(embeddings)
        scored = [(self.cosine_similarity(ref, emb), emb) for emb in embeddings]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:max_keep]]

    def keep_best_hists(self, hists, max_keep=cfg.MAX_OWNER_SAMPLES):
        if len(hists) <= max_keep:
            return hists[:]
        ref = self.average_hists(hists)
        scored = [(self.hist_similarity(ref, h), h) for h in hists]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:max_keep]]

    def multi_embedding_similarity(self, owner_bank, emb):
        if len(owner_bank) == 0 or emb is None:
            return -1.0
        sims = [self.cosine_similarity(ref, emb) for ref in owner_bank]
        sims.sort(reverse=True)
        return float(np.mean(sims[:min(3, len(sims))]))

    def multi_hist_similarity(self, owner_bank, hist):
        if len(owner_bank) == 0 or hist is None:
            return 0.0
        sims = [self.hist_similarity(ref, hist) for ref in owner_bank]
        sims.sort(reverse=True)
        return float(np.mean(sims[:min(3, len(sims))]))

    def motion_similarity(self, box, reference_box, center_x, center_y):
        if box is None:
            return 0.0
        if reference_box is None:
            dist2 = center_distance_sq(box, center_x, center_y)
            return max(0.0, 1.0 - min(1.0, dist2 / 180000.0))

        overlap = iou(box, reference_box)
        ref_cx = int((reference_box[0] + reference_box[2]) / 2)
        ref_cy = int((reference_box[1] + reference_box[3]) / 2)
        dist2 = center_distance_sq(box, ref_cx, ref_cy)
        dist_score = 1.0 - min(1.0, dist2 / 120000.0)
        size_score = size_similarity(box, reference_box)
        return max(0.0, min(1.0, 0.50 * overlap + 0.30 * dist_score + 0.20 * size_score))

    def compute_candidate_scores(self, crop_bgr, box, reference_box, center_x, center_y):
        core_crop = self.crop_reid_core_region(crop_bgr)
        upper_crop = self.crop_upper_body(crop_bgr)

        core_crop, brightness_value = normalize_person_crop(core_crop)
        upper_crop, _ = normalize_person_crop(upper_crop)

        self.last_brightness_value = brightness_value

        emb_core = self.extract_embedding(core_crop)
        emb_upper = self.extract_embedding(upper_crop)
        shirt_hist = self.extract_shirt_hist(upper_crop)

        emb_core_sim = max(
            self.multi_embedding_similarity(self.owner_embeddings_bank, emb_core),
            self.cosine_similarity(self.target_profile, emb_core)
        )
        emb_upper_sim = max(
            self.multi_embedding_similarity(self.owner_upper_embeddings_bank, emb_upper),
            self.cosine_similarity(self.target_upper_profile, emb_upper)
        )
        emb_sim = 0.65 * emb_core_sim + 0.35 * emb_upper_sim

        shirt_sim = max(
            self.multi_hist_similarity(self.owner_shirt_bank, shirt_hist),
            self.hist_similarity(self.target_shirt_profile, shirt_hist)
        )

        motion_sim = self.motion_similarity(box, reference_box, center_x, center_y)
        fused = cfg.EMB_WEIGHT * emb_sim + cfg.MOTION_WEIGHT * motion_sim + cfg.SHIRT_WEIGHT * shirt_sim
        return emb_sim, shirt_sim, motion_sim, fused

    def add_enroll_sample(self, frame, nearest_box):
        crop, _ = crop_from_box(frame, nearest_box)
        if crop is None or not valid_box_size(nearest_box):
            return

        core_crop = self.crop_reid_core_region(crop)
        upper_crop = self.crop_upper_body(crop)
        core_crop, _ = normalize_person_crop(core_crop)
        upper_crop, _ = normalize_person_crop(upper_crop)

        emb_core = self.extract_embedding(core_crop)
        emb_upper = self.extract_embedding(upper_crop)
        shirt_hist = self.extract_shirt_hist(upper_crop)

        if shirt_hist is not None:
            self.enroll_embeddings.append(emb_core)
            self.enroll_upper_embeddings.append(emb_upper)
            self.enroll_shirts.append(shirt_hist)

    def finish_enroll(self, track_id, box, now):
        self.owner_embeddings_bank = self.keep_best_embeddings(self.enroll_embeddings)
        self.owner_upper_embeddings_bank = self.keep_best_embeddings(self.enroll_upper_embeddings)
        self.owner_shirt_bank = self.keep_best_hists(self.enroll_shirts)

        self.target_profile = self.average_embeddings(self.owner_embeddings_bank)
        self.target_upper_profile = self.average_embeddings(self.owner_upper_embeddings_bank)
        self.target_shirt_profile = self.average_hists(self.owner_shirt_bank)

        self.current_track_id = track_id
        self.current_target_box = box
        self.current_target_sim = 1.0
        self.current_target_score = 1.0
        self.last_target_time = now

        self.enroll_embeddings = []
        self.enroll_upper_embeddings = []
        self.enroll_shirts = []
        self.candidate_track_id = None
        self.candidate_count = 0

    def rank_candidates_reacquire(self, detections, reference_box, center_x, center_y):
        ranked = []
        for det in detections:
            if not valid_box_size(det["box"]):
                continue
            box = det["box"]
            overlap = iou(box, reference_box)
            dist2 = center_distance_sq(box, center_x, center_y)
            area = box_area(box)
            score = overlap * 3.0 + area / 120000.0 - dist2 / 160000.0
            ranked.append((score, det))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in ranked]

    def select_target(self, frame, detections, center_x, center_y, now, frame_count):
        selected_target = None
        target_recently_lost = (now - self.last_target_time) <= cfg.TARGET_LOST_TOLERANCE
        current_mode = "TRACKING" if self.current_track_id is not None and target_recently_lost else "REACQUIRE"
        reid_interval = cfg.TRACKING_REID_INTERVAL if current_mode == "TRACKING" else cfg.REACQUIRE_REID_INTERVAL
        run_reid_this_frame = (frame_count % reid_interval == 0)

        if self.target_profile is None or len(detections) == 0:
            return None

        current_det = None
        for det in detections:
            if det["id"] == self.current_track_id:
                current_det = det
                break

        if current_det is not None and valid_box_size(current_det["box"]):
            if run_reid_this_frame:
                crop, _ = crop_from_box(frame, current_det["box"])
                if crop is not None:
                    try:
                        emb_sim, shirt_sim, motion_sim, fused = self.compute_candidate_scores(
                            crop, current_det["box"], self.current_target_box, center_x, center_y
                        )
                        current_det["emb_sim"] = emb_sim
                        current_det["shirt_sim"] = shirt_sim
                        current_det["motion_sim"] = motion_sim
                        current_det["score"] = fused + cfg.TRACK_ID_BONUS
                    except Exception:
                        current_det["emb_sim"] = -1.0
                        current_det["shirt_sim"] = 0.0
                        current_det["motion_sim"] = 0.0
                        current_det["score"] = -1.0
            else:
                current_det["emb_sim"] = self.current_target_sim
                current_det["shirt_sim"] = 0.0
                current_det["motion_sim"] = 0.0
                current_det["score"] = self.current_target_score

            if current_det["emb_sim"] >= cfg.KEEP_TARGET_THRESHOLD:
                selected_target = current_det
                self.current_target_box = current_det["box"]
                self.current_target_sim = current_det["emb_sim"]
                self.current_target_score = current_det["score"]
                self.last_target_time = now
                self.candidate_track_id = None
                self.candidate_count = 0

        if selected_target is None and run_reid_this_frame:
            ranked = self.rank_candidates_reacquire(detections, self.current_target_box, center_x, center_y)
            ranked = ranked[:cfg.MAX_REID_CANDIDATES_REACQUIRE]

            best_det = None
            best_score = -1.0
            for det in ranked:
                crop, _ = crop_from_box(frame, det["box"])
                if crop is None:
                    continue
                try:
                    emb_sim, shirt_sim, motion_sim, fused = self.compute_candidate_scores(
                        crop, det["box"], self.current_target_box, center_x, center_y
                    )
                except Exception:
                    continue

                det["emb_sim"] = emb_sim
                det["shirt_sim"] = shirt_sim
                det["motion_sim"] = motion_sim
                det["score"] = fused

                if det["score"] > best_score:
                    best_score = det["score"]
                    best_det = det

            if best_det is not None:
                emb_ok = best_det["emb_sim"] >= cfg.SIM_THRESHOLD_REACQUIRE
                motion_ok = best_det["motion_sim"] >= 0.20
                if emb_ok and motion_ok:
                    if self.candidate_track_id == best_det["id"]:
                        self.candidate_count += 1
                    else:
                        self.candidate_track_id = best_det["id"]
                        self.candidate_count = 1

                    if self.candidate_count >= cfg.REACQUIRE_CONFIRM_FRAMES:
                        self.current_track_id = best_det["id"]
                        self.current_target_box = best_det["box"]
                        self.current_target_sim = best_det["emb_sim"]
                        self.current_target_score = best_det["score"] + cfg.TRACK_ID_BONUS
                        self.last_target_time = now
                        selected_target = best_det
                        self.candidate_track_id = None
                        self.candidate_count = 0
                else:
                    self.candidate_track_id = None
                    self.candidate_count = 0

        return selected_target

    def smooth_depth_distance(self, new_value):
        if new_value is None:
            return self.smoothed_distance_mm
        if self.smoothed_distance_mm is None:
            self.smoothed_distance_mm = new_value
        else:
            self.smoothed_distance_mm = cfg.DEPTH_ALPHA * new_value + (1.0 - cfg.DEPTH_ALPHA) * self.smoothed_distance_mm
        return self.smoothed_distance_mm
