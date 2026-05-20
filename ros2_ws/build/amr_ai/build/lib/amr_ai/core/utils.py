# =============================
# utils.py
# Hàm xử lý box, ảnh, depth dùng chung
# =============================

import cv2
import math
import numpy as np
from amr_ai.core import config as cfg


def clamp_box(x1, y1, x2, y2, w, h):
    x1 = max(0, min(int(x1), w - 1))
    y1 = max(0, min(int(y1), h - 1))
    x2 = max(0, min(int(x2), w - 1))
    y2 = max(0, min(int(y2), h - 1))
    return x1, y1, x2, y2


def box_width_height(box):
    x1, y1, x2, y2 = map(int, box)
    return max(0, x2 - x1), max(0, y2 - y1)


def valid_box_size(box):
    bw, bh = box_width_height(box)
    return bw >= cfg.MIN_BOX_W and bh >= cfg.MIN_BOX_H


def valid_fall_box_size(box):
    bw, bh = box_width_height(box)
    area = bw * bh
    return bw >= cfg.FALL_BOX_MIN_W and bh >= cfg.FALL_BOX_MIN_H and area >= cfg.FALL_BOX_MIN_AREA


def crop_from_box(frame, box):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = clamp_box(box[0], box[1], box[2], box[3], w, h)
    if x2 <= x1 or y2 <= y1:
        return None, None
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None, None
    return crop, (x1, y1, x2, y2)


def box_center(box):
    x1, y1, x2, y2 = map(int, box)
    return (x1 + x2) // 2, (y1 + y2) // 2


def box_area(box):
    x1, y1, x2, y2 = map(int, box)
    return max(1, x2 - x1) * max(1, y2 - y1)


def center_distance_sq(box, cx, cy):
    bx, by = box_center(box)
    return (bx - cx) ** 2 + (by - cy) ** 2


def iou(boxA, boxB):
    if boxA is None or boxB is None:
        return 0.0
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    inter_w = max(0, xB - xA)
    inter_h = max(0, yB - yA)
    inter_area = inter_w * inter_h
    areaA = max(1, (boxA[2] - boxA[0])) * max(1, (boxA[3] - boxA[1]))
    areaB = max(1, (boxB[2] - boxB[0])) * max(1, (boxB[3] - boxB[1]))
    union = areaA + areaB - inter_area
    return 0.0 if union <= 0 else inter_area / union


def size_similarity(boxA, boxB):
    if boxA is None or boxB is None:
        return 0.0
    mn = min(box_area(boxA), box_area(boxB))
    mx = max(box_area(boxA), box_area(boxB))
    return 0.0 if mx <= 0 else mn / mx


def point_dist(p1, p2):
    if p1 is None or p2 is None:
        return None
    return float(math.hypot(p1[0] - p2[0], p1[1] - p2[1]))


def estimate_brightness(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray))


def apply_gamma(image, gamma=1.0):
    gamma = max(gamma, 1e-6)
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(256)]).astype("uint8")
    return cv2.LUT(image, table)


def gray_world_white_balance(img):
    img_f = img.astype(np.float32)
    b, g, r = cv2.split(img_f)
    mean_b, mean_g, mean_r = np.mean(b), np.mean(g), np.mean(r)
    mean_gray = (mean_b + mean_g + mean_r) / 3.0
    b *= mean_gray / (mean_b + 1e-6)
    g *= mean_gray / (mean_g + 1e-6)
    r *= mean_gray / (mean_r + 1e-6)
    return np.clip(cv2.merge([b, g, r]), 0, 255).astype(np.uint8)


def apply_clahe_bgr(image, clip_limit=2.0, tile_grid_size=(6, 6)):
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    l2 = clahe.apply(l)
    return cv2.cvtColor(cv2.merge((l2, a, b)), cv2.COLOR_LAB2BGR)


def simple_retinex_bgr(image):
    img = image.astype(np.float32) + 1.0
    out_channels = []
    for ch in cv2.split(img):
        blur = cv2.GaussianBlur(ch, (0, 0), 25)
        ret = np.log(ch) - np.log(blur + 1.0)
        ret = cv2.normalize(ret, None, 0, 255, cv2.NORM_MINMAX)
        out_channels.append(ret.astype(np.uint8))
    return cv2.merge(out_channels)


def unsharp_mask(image, sigma=1.0, strength=0.5):
    blur = cv2.GaussianBlur(image, (0, 0), sigma)
    sharp = cv2.addWeighted(image, 1.0 + strength, blur, -strength, 0)
    return np.clip(sharp, 0, 255).astype(np.uint8)


def normalize_person_crop(crop_bgr):
    if crop_bgr is None or crop_bgr.size == 0:
        return crop_bgr, 0.0

    brightness = estimate_brightness(crop_bgr)
    out = gray_world_white_balance(crop_bgr.copy())

    if brightness < 65:
        out = simple_retinex_bgr(out)
        out = apply_clahe_bgr(out, 2.0, (6, 6))
        out = apply_gamma(out, 0.92)
    elif brightness < 95:
        out = apply_clahe_bgr(out, 1.8, (6, 6))
        out = apply_gamma(out, 0.96)
    elif brightness < 185:
        out = apply_clahe_bgr(out, 1.5, (6, 6))
    elif brightness < 220:
        out = apply_gamma(out, 1.08)
    else:
        out = apply_gamma(out, 1.16)

    out = unsharp_mask(out, 1.0, 0.5)
    return out, brightness


def get_valid_depth_values(roi):
    if roi is None or roi.size == 0:
        return np.array([], dtype=np.uint16)
    return roi[(roi > cfg.MIN_DEPTH_MM) & (roi < cfg.MAX_DEPTH_MM)]


def estimate_depth_distance(depth_map, box):
    if depth_map is None or box is None:
        return None, None

    h, w = depth_map.shape[:2]
    x1, y1, x2, y2 = map(int, box)
    x1, y1, x2, y2 = clamp_box(x1, y1, x2, y2, w, h)

    if x2 <= x1 or y2 <= y1:
        return None, None

    bw = x2 - x1
    bh = y2 - y1

    rx1 = x1 + int(bw * cfg.DEPTH_ROI_X1_RATIO)
    rx2 = x1 + int(bw * cfg.DEPTH_ROI_X2_RATIO)
    ry1 = y1 + int(bh * cfg.DEPTH_ROI_Y1_RATIO)
    ry2 = y1 + int(bh * cfg.DEPTH_ROI_Y2_RATIO)

    rx1, ry1, rx2, ry2 = clamp_box(rx1, ry1, rx2, ry2, w, h)
    if rx2 <= rx1 or ry2 <= ry1:
        return None, None

    valid = get_valid_depth_values(depth_map[ry1:ry2, rx1:rx2])
    if valid.size < 20:
        return None, (rx1, ry1, rx2, ry2)

    return float(np.median(valid)), (rx1, ry1, rx2, ry2)


def sample_depth_at_point(depth_map, p, radius=4):
    if depth_map is None or p is None:
        return None
    h, w = depth_map.shape[:2]
    x, y = int(round(p[0])), int(round(p[1]))
    x1, x2 = max(0, x - radius), min(w, x + radius + 1)
    y1, y2 = max(0, y - radius), min(h, y + radius + 1)
    if x2 <= x1 or y2 <= y1:
        return None
    roi = depth_map[y1:y2, x1:x2]
    valid = roi[(roi > cfg.MIN_DEPTH_MM) & (roi < cfg.MAX_DEPTH_MM)]
    return None if valid.size < 5 else float(np.median(valid))
