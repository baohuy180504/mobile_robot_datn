#!/usr/bin/env python3
"""
bench_trt_yolo.py — CHẠY TRÊN JETSON. So sánh Ultralytics (cũ) và TrtYOLO (mới, TensorRT trực
tiếp) trên CÙNG một ảnh: box/keypoint có khớp nhau không, và nhanh hơn bao nhiêu.

Bắt buộc chạy bước này và thấy "khớp" trước khi để ai_detector_node.py dùng TrtYOLO thật,
vì trt_yolo.py suy đoán định dạng đầu ra engine (end2end, đã NMS, tọa độ theo ảnh letterbox)
dựa trên metadata, chưa đối chiếu với ảnh người thật.

Dùng:
    python3 bench_trt_yolo.py --image /duong/dan/anh_co_nguoi.jpg
    python3 bench_trt_yolo.py --image anh.jpg --model person   # chỉ benchmark model person
    python3 bench_trt_yolo.py --image anh.jpg --model pose --crop 100,50,300,400
"""
import argparse
import os
import sys
import time

import cv2
import numpy as np


def find_models_dir():
    p = os.path.expanduser('~/mobile_robot/ros2_ws/install/amr_ai/share/amr_ai/models')
    return p if os.path.isdir(p) else '.'


def draw_boxes(img, boxes, confs, color, label_prefix):
    out = img.copy()
    for box, conf in zip(boxes, confs):
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        cv2.putText(out, f'{label_prefix} {conf:.2f}', (x1, max(15, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    return out


def draw_kpts(img, kpts, color):
    out = img.copy()
    for kp in kpts:
        for x, y, v in kp:
            if v > 0.3:
                cv2.circle(out, (int(x), int(y)), 3, color, -1)
    return out


def iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    ua = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1) + max(0.0, bx2 - bx1) * max(0.0, by2 - by1) - inter
    return inter / ua if ua > 0 else 0.0


def match_report(boxes_a, confs_a, boxes_b, confs_b, tag):
    print(f'\n[{tag}] Ultralytics: {len(boxes_a)} box | TrtYOLO: {len(boxes_b)} box')
    if len(boxes_a) != len(boxes_b):
        print('  CẢNH BÁO: số lượng box khác nhau — kiểm tra ngưỡng conf, hoặc định dạng đầu ra sai.')
    used = set()
    for i, (ba, ca) in enumerate(zip(boxes_a, confs_a)):
        best_j, best_iou = -1, 0.0
        for j, bb in enumerate(boxes_b):
            if j in used:
                continue
            v = iou(ba, bb)
            if v > best_iou:
                best_iou, best_j = v, j
        if best_j < 0:
            print(f'  box #{i} (Ultralytics conf={ca:.2f}) KHÔNG có box nào bên TrtYOLO khớp gần')
            continue
        used.add(best_j)
        cb = confs_b[best_j]
        flag = 'OK' if best_iou > 0.9 else ('GẦN ĐÚNG' if best_iou > 0.5 else 'LỆCH NHIỀU -- kiểm tra decode!')
        print(f'  box #{i}: IoU={best_iou:.3f} conf {ca:.2f} vs {cb:.2f}  [{flag}]')
    return len(boxes_a) == len(boxes_b) and all(
        iou(a, b) > 0.9 for a, b in zip(sorted(boxes_a, key=lambda x: x[0]), sorted(boxes_b, key=lambda x: x[0]))
    ) if len(boxes_a) == len(boxes_b) and len(boxes_a) > 0 else len(boxes_a) == len(boxes_b) == 0


def bench(name, fn, n=60):
    for _ in range(10):
        fn()
    t0 = time.perf_counter()
    for _ in range(n):
        fn()
    ms = (time.perf_counter() - t0) / n * 1000.0
    print(f'  {name}: {ms:.2f} ms/lần  (~{1000.0/ms:.0f} lần/giây)')
    return ms


def run_person(img, models_dir, do_bench):
    path = os.path.join(models_dir, 'yolo26n.engine')
    print(f'\n=== PERSON: {path} ===')
    from ultralytics import YOLO as UltraYOLO
    from amr_ai.core.trt_yolo import TrtYOLO

    um = UltraYOLO(path)
    tm = TrtYOLO(path)

    ur = um.predict(img, classes=[0], conf=0.4, verbose=False)[0]
    tr = tm.predict(img, classes=[0], conf=0.4, verbose=False)[0]
    ub = ur.boxes.xyxy.cpu().numpy().tolist()
    uc = ur.boxes.conf.cpu().numpy().tolist()
    tb = tr.boxes.xyxy.cpu().numpy().tolist()
    tc = tr.boxes.conf.cpu().numpy().tolist()
    good = match_report(ub, uc, tb, tc, 'PERSON')

    out = img.copy()
    out = draw_boxes(out, ub, uc, (0, 255, 255), 'ultra')
    out = draw_boxes(out, tb, tc, (0, 0, 255), 'trt')
    cv2.imwrite('/tmp/bench_person.jpg', out)
    print('  Ảnh so sánh (vàng=Ultralytics, đỏ=TensorRT): /tmp/bench_person.jpg')

    if do_bench:
        print('  Thời gian (đã làm nóng 10 lần, đo trung bình 60 lần):')
        bench('Ultralytics .predict()', lambda: um.predict(img, classes=[0], conf=0.4, verbose=False))
        bench('TrtYOLO     .predict()', lambda: tm.predict(img, classes=[0], conf=0.4, verbose=False))
    return good


def run_pose(img, models_dir, crop_arg, do_bench):
    path = os.path.join(models_dir, 'yolo26n-pose.engine')
    print(f'\n=== POSE: {path} ===')
    from ultralytics import YOLO as UltraYOLO
    from amr_ai.core.trt_yolo import TrtYOLO

    if crop_arg:
        x1, y1, x2, y2 = map(int, crop_arg.split(','))
        crop = img[y1:y2, x1:x2]
    else:
        crop = img
        print('  (không truyền --crop: dùng cả ảnh làm "người" giả để so khớp, không phản ánh độ chính xác thật)')

    um = UltraYOLO(path)
    tm = TrtYOLO(path)

    ur = um.predict(crop, imgsz=192, verbose=False)[0]
    tr = tm.predict(crop, imgsz=192, verbose=False)[0]
    ub = ur.boxes.xyxy.cpu().numpy().tolist()
    uc = ur.boxes.conf.cpu().numpy().tolist()
    tb = tr.boxes.xyxy.cpu().numpy().tolist()
    tc = tr.boxes.conf.cpu().numpy().tolist()
    good = match_report(ub, uc, tb, tc, 'POSE (box)')

    uk = ur.keypoints.data.cpu().numpy() if len(ub) else np.zeros((0, 17, 3))
    tk = tr.keypoints.data.cpu().numpy() if len(tb) else np.zeros((0, 17, 3))
    if len(uk) and len(tk):
        d = np.linalg.norm(uk[0][:, :2] - tk[0][:, :2], axis=1)
        print(f'  Lệch keypoint (Ultralytics vs TrtYOLO), pixel: trung bình={d.mean():.1f}, lớn nhất={d.max():.1f}')
        if d.mean() > 5.0:
            print('  CẢNH BÁO: lệch trung bình > 5 px, kiểm tra lại decode_pose (thứ tự trục, pad, tỉ lệ).')

    out = draw_kpts(draw_boxes(crop, ub, uc, (0, 255, 255), 'ultra'), uk, (0, 255, 255))
    out = draw_kpts(draw_boxes(out, tb, tc, (0, 0, 255), 'trt'), tk, (0, 0, 255))
    cv2.imwrite('/tmp/bench_pose.jpg', out)
    print('  Ảnh so sánh (vàng=Ultralytics, đỏ=TensorRT): /tmp/bench_pose.jpg')

    if do_bench:
        print('  Thời gian (đã làm nóng 10 lần, đo trung bình 60 lần):')
        bench('Ultralytics .predict()', lambda: um.predict(crop, imgsz=192, verbose=False))
        bench('TrtYOLO     .predict()', lambda: tm.predict(crop, imgsz=192, verbose=False))
    return good


def main():
    ap = argparse.ArgumentParser(description='So sánh Ultralytics vs TrtYOLO trên cùng ảnh')
    ap.add_argument('--image', required=True, help='ảnh có người, chụp từ camera thật càng tốt')
    ap.add_argument('--models-dir', default=None)
    ap.add_argument('--model', choices=['person', 'pose', 'both'], default='both')
    ap.add_argument('--crop', default=None, help='x1,y1,x2,y2 vùng người cho model pose (mặc định: cả ảnh)')
    ap.add_argument('--no-bench', action='store_true', help='chỉ so khớp, bỏ qua đo thời gian')
    args = ap.parse_args()

    img = cv2.imread(args.image)
    if img is None:
        print(f'Không đọc được ảnh: {args.image}')
        sys.exit(2)

    models_dir = args.models_dir or find_models_dir()
    print(f'Thư mục model: {models_dir}')
    do_bench = not args.no_bench

    ok = True
    if args.model in ('person', 'both'):
        ok = run_person(img, models_dir, do_bench) and ok
    if args.model in ('pose', 'both'):
        ok = run_pose(img, models_dir, args.crop, do_bench) and ok

    print('\n' + ('KẾT QUẢ: box khớp tốt (IoU > 0.9) — có thể yên tâm chuyển sang TrtYOLO.'
                  if ok else
                  'KẾT QUẢ: CÓ SAI LỆCH — đừng dùng TrtYOLO cho tới khi xem lại decode_detect/decode_pose. '
                  'Gửi ảnh /tmp/bench_*.jpg cho người hỗ trợ.'))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
